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

import sys
import pykickstart
import pykickstart.constants
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk
import logging
import time

import yum
from yum.constants import *
from yum.packages import comparePoEVR
import yum.Errors

import revisor

from revisor.errors import *
from revisor.constants import *

# Translation
from revisor.translate import _, N_

# Master GTK Interface update routine
def _runGtkMain(*args):
    while gtk.events_pending():
        gtk.main_iteration()

class ReadyScreen:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.number_packages = self.frame_xml.get_widget("number_packages")
        self.package_payload = self.frame_xml.get_widget("payload_size")
        self.package_installpayload = self.frame_xml.get_widget("installpayload_size")

        gui.add_buttons()

        self.connect_button_signals()

        self.pkgFilter = None
        self.sortedStore = None

        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(PIXMAPS_FILES + "header_packages.png")

        self.button_vbox = self.frame_xml.get_widget("button_vbox")

        self.gui.base_buttons_xml.get_widget("button_forward").set_sensitive(False)
        self.gui.base_buttons_xml.get_widget("button_back").set_sensitive(False)

        # Hey, we did not come past any depsolving... How do we know the statistics?
        if not self.cfg.kickstart_manifest and not self.cfg.kickstart_options_customize:
            # We should have selected packages by hand, and depsolved on "next"
            self.populate_stats()
        elif self.cfg.kickstart_manifest and self.cfg.kickstart_manifest_customize:
            # We should have selected packages by hand, and depsolved on "next"
            self.populate_stats()
        elif not self.cfg.kickstart_manifest:
            # Again, packages selected manually and thus depsolved
            self.populate_stats()
        elif self.cfg.kickstart_manifest:
            # We haven't selected anything manually, but we do have a list of stuff we wanna add
            if not self.base.setup_yum():
                # It's already doing a notice... We're gonna wanna return to configuration
                self.cfg.i_did_all_this = False
                self.cfg.yumobj = yum.YumBase()
                self.cfg.repos = {}
                self.gui.displayRevisorConfiguration()
            else:
                self.cfg.i_did_all_this = True

            msg_id = self.gui.statusbar.push(0,"Adding in packages from Kickstart Data, please wait")
            _runGtkMain()


            groupList = self.cfg.ksobj._get("packages","groupList")
            packageList = self.cfg.ksobj._get("packages","packageList")
            excludedList = self.cfg.ksobj._get("packages","excludedList")
            self.base.pkglist_from_ksdata(groupList=groupList, packageList=packageList, excludedList=excludedList, ignore_list=self.cfg.yumobj.tsInfo.pkgdict.keys())
            self.gui.statusbar.remove(0,msg_id)
            self.base.check_dependencies()
            self.populate_stats()

        elif self.cfg.kickstart_options_customize:
            # We should have selected packages by hand, and customized the media further... need to depsolve
            self.base.check_dependencies()
            self.populate_stats()

        self.gui.base_buttons_xml.get_widget("button_forward").set_sensitive(True)
        self.gui.base_buttons_xml.get_widget("button_back").set_sensitive(True)

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def check_options(self):
        """Check the options specified"""
        # No options enabled yet
        return True

    def button_back_clicked(self, button):
        self.gui.back()

    def button_forward_clicked(self, button):
        if not self.check_options():
#            print "Failed Checking Options..."
            pass
        else:
            # Destroy the packageList and groupList then fill them up again
            #self.cfg.ksobj._set("packages","packageList",[])
            #self.cfg.ksobj._set("packages","groupList",[])
            #self.cfg.yumobj.tsInfo.makelists()
            #packageList = []
            #txmbrs = self.cfg.yumobj.tsInfo.installed + self.cfg.yumobj.tsInfo.depinstalled
            #for txmbr in txmbrs:
                #packageList.append(txmbr.name)
            #self.cfg.ksobj._set("packages","packageList",[])
            self.gui.next()

    def populate_stats(self):
        """ Populate the stats displayed on the ready screen, based on our yum transaction. """
        self.base.populate_stats()

        self.base.report_sizes()

        self.number_packages.set_text("%s packages" % (self.cfg.payload_packages))
        self.package_payload.set_text("%s %s" % revisor.misc.size_me(self.cfg.payload_installmedia))
        self.package_installpayload.set_text("%s %s" % revisor.misc.size_me(self.cfg.payload_livemedia))
