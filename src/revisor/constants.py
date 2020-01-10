#
# Copyright 2007-2010 Fedora Unity Project (http://fedoraunity.org)
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

import os
import sys

if os.access(os.path.join(sys.path[0], "revisor/modgui/glade/"), os.R_OK):
    GLADE_FILES = os.path.join(sys.path[0], "revisor/modgui/glade/")
else:
    GLADE_FILES = "/usr/share/revisor/ui/"

if os.access(os.path.join(sys.path[0], "revisor/modgui/glade/pixmaps"), os.R_OK):
    PIXMAPS_FILES = os.path.join(sys.path[0], "revisor/modgui/glade/pixmaps/")
else:
    PIXMAPS_FILES = "/usr/share/revisor/pixmaps/"

if os.access(os.path.join(sys.path[0], "conf/"), os.R_OK):
    BASE_CONF_DIR = os.path.join(sys.path[0], "conf/")
    BASE_CONFD_DIR = os.path.join(BASE_CONF_DIR, "conf.d/")
else:
    BASE_CONF_DIR = "/etc/revisor"
    BASE_CONFD_DIR = os.path.join(BASE_CONF_DIR, "conf.d/")

DOCS_BASEPATH = "http://revisor.fedoraunity.org/documentation/"

REVISOR_HOMEPAGE = "http://revisorproject.org/"
FEDORAUNITY_HOMEPAGE = "http://fedoraunity.org/"

domain = 'revisor'

SELINUX_DISABLED = 0
SELINUX_ENABLED = 1
SELINUX_PERMISSIVE = 2

PIPE = -1
STDOUT = -2

# Big no-nonsense dictionary with destination directories to check
# given one of the values is true.

DESTDIRS = {

        'iso': [
                "media_installation_cd",
                "media_installation_dvd",
                "media_installation_dvd_duallayer",
                "media_installation_bluray",
                "media_installation_bluray_duallayer",
                "media_installation_unified",
                "media_utility_rescue",
            ],
        'live': [
                "media_live_optical",
            ],
        'os': [
                "getsource",
                "media_installation_tree",
            ],
        'debug': [
                "getdebuginfo",
            ],
        'usb': [
                "media_installation_usb",
            ],
    }
