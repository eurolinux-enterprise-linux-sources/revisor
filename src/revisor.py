#!/usr/bin/python2
#
# Copyright 2007-2009 Fedora Unity Project (http://fedoraunity.org)
#
# Jonathan Steffan <jon a fedoraunity.org>
# Jeroen van Meeuwen <kanarip a fedoraunity.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 only
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import logging
import os
import sys

# This is development
sys.path.append(".")
sys.path.append(sys.path[0])

try:
    from revisor.translate import _
except:
    pass

if os.access("/usr/lib/anaconda-runtime/", os.R_OK):
    sys.path.append("/usr/lib/anaconda-runtime/")
else:
    print >> sys.stderr, _("Cannot find anaconda-runtime in /usr/lib/anaconda-runtime")
    sys.exit(1)

# Before we start running crazy, check if we can import revisor.logger, for instance

try:
    import revisor.logger
except ImportError, e:
    print >> sys.stderr, "%s. If you are running from source you need to autoreconf -v && ./configure before running %s" % (e, sys.argv[0])
    sys.exit(1)

import revisor

if __name__ == "__main__":
    revisor = revisor.Revisor()
    revisor.run()
