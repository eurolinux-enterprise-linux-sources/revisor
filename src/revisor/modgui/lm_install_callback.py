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

import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk
import rpm
from yum.constants import *

def _runGtkMain(*args):
    while gtk.events_pending():
        gtk.main_iteration()

class LMRPMInstallCallback:
    def __init__(self, pbar):
        self.pbar = pbar
        self.total_actions = 0
        self.total_installed = 0

        self.tsInfo = None # this needs to be set for anything else to work

    def callback(self, what, bytes, total, h, user):
        if what == rpm.RPMCALLBACK_TRANS_START:
            if bytes == 6:
                self.total_actions = total

        elif what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            if h is not None:
                self.total_installed += 1
                self.pbar.set_fraction(self.total_installed/self.total_actions)
                _runGtkMain()