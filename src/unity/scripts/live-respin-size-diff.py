#!/usr/bin/python -tt

# From jkeating's live-scripts/livediffsize.py

import os, sys, string

THRESH = 0.01

def readfile(fn):
    pkgs = {}
    f = open(fn, "r")
    lines = f.readlines()
    f.close()
    for l in lines:
        (size, name) = l.split()
        pkgs[name] = size
    return pkgs

old = sys.argv[1]
new = sys.argv[2]

oldpkgs = readfile(old)
newpkgs = readfile(new)

for (pkg, size) in newpkgs.items():
    if not oldpkgs.has_key(pkg):
        print "new package %s: %s" %(pkg, size)
        continue

    oldsize = oldpkgs[pkg]
    if oldsize == "0":
        continue

    deltapct = (int(size) - int(oldsize)) / float(oldsize)
    if deltapct > THRESH:
        print "%s grew by %.2f%% (%s->%s)" %(pkg, deltapct*100, oldsize, size)

for (pkg, size) in oldpkgs.items():
    if not newpkgs.has_key(pkg):
        print "removed package %s: %s" %(pkg, size)

print "Old Live Re-Spin at %s has %d packages" %(old,len(oldpkgs),)
print "New Live Re-Spin at %s has %d packages" %(new,len(newpkgs),)

