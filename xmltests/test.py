#!/usr/bin/env python

import os
import xml.dom.minidom

codes = range(1, 128)

def make_datafiles():
    tmpl = open("tmpl.xml", "r").read()
    for i in codes:
        data = tmpl.replace("SOMEEMAIL", "first%clast" % chr(i))
        open("%d.xml" % i, "w").write(data)

def clean_datafiles():
    for i in codes:
        os.remove("%d.xml" % i)

def find_failed():
    failed = []
    for i in codes:
        try:
            d = xml.dom.minidom.parse("%d.xml" % i)
        except:
            failed.append(i)
    return failed

make_datafiles()
print find_failed()
clean_datafiles()
