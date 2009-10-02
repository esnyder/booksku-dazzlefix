#!/usr/bin/env python

import os, sys, re
import urllib2, urllib, cookielib
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, Tag, NavigableString

from optparse import OptionParser

class booksku_error(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class booksku_session:
    """
    Authenticate with BookSku in constructor, then use those credentials to 
    scrape the condition notes by SKU.
    """
    def __init__(self, username, password):
        self.jar = cookielib.CookieJar()
        self.handler = urllib2.HTTPSHandler()
        self.cjh = urllib2.HTTPCookieProcessor(self.jar)
        self.opener = urllib2.build_opener(self.handler, self.cjh)
        loginvalues = {'username': username,
                       'userpass': password,
                       'userlogin': 'Log In',
                       'autologin': '1'}
        data = urllib.urlencode(loginvalues)
        page = self.opener.open("https://bs.booksku.com/bs/login.php", data)
        # Fix: handle errors more gracefully here.  Occassionally we fail to
        # resolve bs.booksku.com for some reason; re-running the script will
        # then succeed.
        self.loginsoup = BeautifulSoup(page)
        if len(self.loginsoup.findAll('input', attrs={'id': 'username'})):
            raise booksku_error("Login failed, wrong password?")
        page.close()

    def condition(self, sku):
        url = "https://bs.booksku.com/bs/catalog_files/index_search.php?action=edit&sku=%s&ownder_id=282" % sku
        page = self.opener.open(url)
        soup = BeautifulSoup(page)
        alldetails = soup.findAll(attrs={'name': 'detail_string'})
        if len(alldetails) != 1:
            raise booksku_exception("Expected 1 'detail_string' field for sku '%s', found %d" % (sku, len(alldetails)))
        return alldetails[0].attrMap['value']

class dazzle_error(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class dazzle_doc:
    """
    Parse DAZzle document and provide a method to add lines of text as 
    <RubberStamp[stampbase]> ... <RubberStamp[stampbase+n]> elements.
    """
    def __init__(self, fname, stampbase):
        self.doc = BeautifulStoneSoup(open(fname, "r").read())
        self.base = stampbase
        self.last = 20

    def skus(self):
        for p in self.doc.findAll("package"):
            skus = p.findAll("rubberstamp2")
            if (len(skus) != 1):
                raise dazzle_error("expected exactly 1 'rubberstamp2' field in package, found %d" % len(skus))
            sku = skus[0]
            yield sku.contents[0]

    def pkg(self, sku):
        for p in self.doc.findAll("package"):
            skuelem = p.findAll("rubberstamp2")[0]
            if skuelem.contents[0] == sku:
                return p

    def set_condition_notes(self, sku, condition_lines):
        p = self.pkg(sku)

        if p is None:
            raise dazzle_error("package with sku '%s' not found" % sku)

        # make sure we don't have these fields set yet
        for i in xrange(self.base, self.base+len(condition_lines)):
            stamp = p.findAll("rubberstamp%d" % i)
            if len(stamp):
                raise dazzle_error("package with sku '%s' already has field 'rubberstamp%d'" % (sku, i))

        i = self.base
        for cl in condition_lines:
            n = Tag(self.doc, "rubberstamp%d" % i)
            n.append(NavigableString(cl))
            p.append(n)
            i += 1
        while(i < self.last):
            n = Tag(self.doc, "rubberstamp%d" % i)
            n.append(NavigableString("."))
            p.append(n)
            i += 1
        return p

    def save(self, fname):
        f = open(fname, "w")
        f.write(self.doc.renderContents())
        f.close()

def break_lines(text, linelength):
    l = ""
    lines = []
    for w in text.split():
        if len(l) + len(w) + 1 > linelength:
            lines.append(l)
            l = w
        else:
            l += " %s" % w
    lines.append(l)
    return lines

def fix_docs(opts, args):
    print "Opening session with booksku..."
    try:
        s = booksku_session(opts.username, opts.password)
    except booksku_error, e:
        print e
        return

    for fname in args:
        print "Processing '%s'..." % fname
        d = dazzle_doc(fname, opts.basestamp)
        
        for sku in d.skus():
            print "    processing SKU %s with line length %d..." % (sku, opts.linelength),
            try:
                c = s.condition(sku)
                lines = break_lines(c, opts.linelength)
                pkg = d.set_condition_notes(sku, lines)
            except (booksku_error, dazzle_error), e:
                print "FAILED to set condition notes: %s!" % e
            else:
                print "set %d lines" % len(lines)

        sname = fname.replace(".xml", ".fixed.xml")
        print "    ...saving '%s'" % sname
        d.save(sname)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-u", "--username", dest="username",
                      help="BookSku account name", metavar="USER", default="roguebooks")
    parser.add_option("-p", "--password", dest="password", 
                      help="BookSku account password", metavar="PASSWORD")
    parser.add_option("-l", "--linelength", type="int", help="Maximum length (in characters) of condition notes lines", default=100)
    parser.add_option("-b", "--basestamp", type="int", help="Use 'RubberStamp<basestamp>' as the first field of condition notes", default=10)

    (opts, args) = parser.parse_args()
    try:
        fix_docs(opts, args)
    except KeyboardInterrupt:
        print
        print "Canceling."
        sys.exit(-1)
