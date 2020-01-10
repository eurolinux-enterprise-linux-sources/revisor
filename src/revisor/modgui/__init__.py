# -*- coding: utf-8 -*-
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

# Import python classes
import sys
import urllib2
import time
import os
import urlgrabber, urlgrabber.progress
from ConfigParser import SafeConfigParser
import string
import subprocess
import math
import shutil

# Import GTK classes
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk

import pykickstart.constants

# Import revisor classes
import build_media
import build_type
import finished_screen
import load_kickstart
import lm_auth
import lm_basic
import lm_bootloader
import lm_display
import lm_network
import lm_security
import lm_usercustomize
import package_selection
import configuration
import select_media
import welcome_screen
import ready_screen

# Import revisor constants and errors
from revisor.constants import *
from revisor.errors import *

# Import yum.Errors for reporting errors
import yum.Errors

## Try and disable gtk threading
#try:
#    from gtk import _disable_gdk_threading
#    _disable_gdk_threading()
#except ImportError:
#    pass

## Import pirut's progress and details dialogs
#from pirut import Progress
#from pirut import DetailsDialog
## Alias those dialogs
#RevisorProgress = Progress.PirutProgress
#RevisorProgressCallback = Progress.PirutProgressCallback
#RevisorDetailsDialog = DetailsDialog.PirutDetailsDialog

# Translation
from revisor.translate import _, N_

gtk.glade.bindtextdomain(domain)

# Try and disable gtk threading
try:
    from gtk import _disable_gdk_threading
    _disable_gdk_threading()
except ImportError:
    pass

def add_options(parser):
    pass

# Master GTK Interface update routine
def _runGtkMain(*args):
    while gtk.events_pending():
        gtk.main_iteration()

class RevisorGui:
    """Master GUI Class for Revisor. This baby has legs, arms and a fully functional brain"""
    def __init__(self):
        """Initialize the RevisorGUI class instance and create a ConfigStore object"""
        pass

    def add_options(self, parser):
        """This function isn't here"""
        pass

    def set_defaults(self, defaults):
        """This function isn't here"""
        pass

    def check_options(self, cfg, cli_options):
        """This function isn't here"""
        pass

    def run(self, base=None):
        # We need base, really we do
        if base == None:
            self.log.error(_("GUI Mode didn't get RevisorBase instance, which is fatal."), recoverable=False)
        else:
            self.base = base

        self.log = self.base.log
        self.cfg = self.base.cfg

        self.build_main_window()
        self.displayWelcomeScreen()
        self.main_window.show()
        _runGtkMain()
        gtk.main()

    def build_main_window(self):
        try:
            base_screen_xml = gtk.glade.XML(GLADE_FILES + "base_screen.glade", domain=domain)
        except RuntimeError, e:
            if not os.access(GLADE_FILES + "base_screen.glade", os.R_OK):
                self.log.error("RuntimeError: %s.\n\nCould not find %s%s.\n\nIf you are running from source, you might need to recreate using 'autoreconf' and './configure'" % (e,GLADE_FILES,"base_screen.glade"))
                sys.exit(1)

        self.base_screen_xml = base_screen_xml
        self.main_window = base_screen_xml.get_widget("main_window")
        self.main_vbox = base_screen_xml.get_widget("main_vbox")
        self.menu_quit = base_screen_xml.get_widget("menu_quit")
        self.menu_about = base_screen_xml.get_widget("menu_about")
        self.menu_homepage = base_screen_xml.get_widget("menu_homepage")
        self.button_fedoraunity_link = base_screen_xml.get_widget("button_fedoraunity_link")
        self.button_revisor_link = base_screen_xml.get_widget("button_revisor_link")
        self.dialog_about = base_screen_xml.get_widget("dialog_about")

        self.main_window.connect("destroy", self.destroy)
        self.menu_quit.connect("activate", self.button_cancel_clicked)
        self.menu_about.connect("activate", self.on_menu_about_activate)
        self.menu_homepage.connect("activate", self.on_menu_homepage_activate)

    def connect_button_signals(self, frame):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.button_cancel_clicked,
                 "on_button_information_clicked": self.button_information_clicked }
        self.base_buttons_xml.signal_autoconnect(sigs)

    def add_buttons(self):
        base_buttons_xml = gtk.glade.XML(GLADE_FILES + "base_buttons.glade", domain=domain)
        self.base_buttons_xml = base_buttons_xml
        self.button_hbox = base_buttons_xml.get_widget("button_hbox")

        self.button_vbox = self.frame_xml.get_widget("button_vbox")
        self.button_vbox.add(self.button_hbox)
        base_statusbar_xml = gtk.glade.XML(GLADE_FILES + "base_statusbar.glade", domain=domain)
        self.base_statusbar_xml = base_statusbar_xml
        self.statusbar = base_statusbar_xml.get_widget("statusbar")
        self.button_vbox.pack_end(self.statusbar,expand=False,fill=False)

    def on_menu_about_activate(self, menu):
        self.dialog_about.set_default_size(100, 100)
        self.dialog_about.set_position(gtk.WIN_POS_CENTER)
        self.button_fedoraunity_link.connect("clicked", self.on_button_fedoraunity_link_clicked)
        self.button_revisor_link.connect("clicked", self.on_button_revisor_link_clicked)
        self.dialog_about.show()

    def on_menu_homepage_activate(self, menu):
        self.open_url(REVISOR_HOMEPAGE)

    def open_url(self, url):
        user = os.getenv('SUDO_USER')
        pid = os.fork()
        if not pid:
            self.log.info(_("Opening up /usr/bin/sudo -u %s /usr/bin/xdg-open %s") % (user,url))
            os.execv("/usr/bin/sudo", ["/usr/bin/sudo", "-u", "%s" % user, "/usr/bin/xdg-open", "%s" % (url)])

    def on_button_revisor_link_clicked(self, *args):
        self.open_url(REVISOR_HOMEPAGE)

    def on_button_fedoraunity_link_clicked(self, *args):
        self.open_url(FEDORAUNITY_HOMEPAGE)

    def button_back_clicked(self, button):
        pass

    def button_forward_clicked(self, button):
        pass

    def button_information_clicked(self, button, keyword):
        self.base.show_help(keyword)

    def button_cancel_clicked(self, button):
        # Destroy ConfigStore
        self.cfg = ""
        gtk.main_quit()
        sys.exit(1)

    def destroy(self, args):
        # Destroy ConfigStore
        self.cfg = ""
        gtk.main_quit()

    def load_frame(self, frame):
        try:
            self.outer_frame.hide()
            self.outer_frame.destroy()
        except:
            pass

        self.frame_xml = gtk.glade.XML(os.path.join(GLADE_FILES, frame), domain=domain)
        self.outer_frame = self.frame_xml.get_widget("outer_frame")
        self.main_vbox.add(self.outer_frame)


    def displayWelcomeScreen(self):
        self.load_frame("welcome_screen.glade")
        self.WelcomeScreen = welcome_screen.WelcomeScreen(self)

    def displaySelectMediaAdvanced(self):
        self.load_frame("select_media_advanced.glade")
        self.SelectMediaTypes = select_media.SelectMediaAdvanced(self)

    def displaySelectMedia(self):
        self.load_frame("select_media.glade")
        self.SelectMedia = select_media.SelectMedia(self)

    def displaySelectMediaInstallation(self):
        self.load_frame("select_media_installation.glade")
        self.SelectMedia = select_media.SelectMediaInstallation(self)

    def displaySelectMediaLive(self):
        self.load_frame("select_media_live.glade")
        self.SelectMedia = select_media.SelectMediaLive(self)

    def displaySelectMediaVirtualization(self):
        self.load_frame("select_media_virtualization.glade")
        self.SelectMedia = select_media.SelectMediaVirtualization(self)

    def displaySelectMediaUtility(self):
        self.load_frame("select_media_utility.glade")
        self.SelectMedia = select_media.SelectMediaUtility(self)

    def displaySelectMediaRebrand(self):
        self.load_frame("select_media_rebrand.glade")
        self.SelectMedia = select_media.SelectMediaRebrand(self)

    def displayBuildType(self):
        self.load_frame("build_type.glade")
        self.BuildType = build_type.BuildType(self)

    def displayRevisorConfiguration(self):
        self.load_frame("revisor_configuration.glade")
        self.RevisorConf = configuration.RevisorConfiguration(self)

    def displayPackageSelection(self):
        self.load_frame("package_selection.glade")
        self.PackageSelection = package_selection.PackageSelection(self)

    def displayLoadKickstart(self):
        self.load_frame("load_kickstart.glade")
        self.loadKickstart = load_kickstart.LoadKickstart(self)

    def displayLMBasic(self):
        self.load_frame("lm_basic.glade")
        self.LMConfBasic = lm_basic.LMBasic(self)

    def displayLMBootloader(self):
        self.load_frame("lm_bootloader.glade")
        self.LMConfBootloader = lm_bootloader.LMBootloader(self)

    def displayLMNetwork(self):
        self.load_frame("lm_network.glade")
        self.LMConfNetwork = lm_network.LMNetwork(self)

    def displayLMAuth(self):
        self.load_frame("lm_auth.glade")
        self.LMAuth = lm_auth.LMAuth(self)

    def displayLMSecurity(self):
        self.load_frame("lm_security.glade")
        self.LMSecurity = lm_security.LMSecurity(self)

    def displayLMDisplay(self):
        self.load_frame("lm_display.glade")
        self.LMDisplay = lm_display.LMDisplay(self)

    def displayLMUserCustomize(self):
        self.load_frame("lm_usercustomize.glade")
        self.LMUserCustomize = lm_usercustomize.LMUserCustomize(self)

    def displayReadyScreen(self):
        self.load_frame("ready_screen.glade")
        self.ReadyScreen = ready_screen.ReadyScreen(self)

    def displayBuildMedia(self):
        self.load_frame("build_media.glade")
        self.BuildMedia = build_media.BuildMedia(self)
        self.BuildMedia.start()

    def displayFinished(self):
        self.load_frame("finished_screen.glade")
        self.FinishedScreen = finished_screen.FinishedScreen(self)

    def downloadErrorDialog(mainwin, secondary, details=None):
        d = RevisorDetailsDialog(mainwin, gtk.MESSAGE_ERROR,
                               [('gtk-ok', gtk.RESPONSE_OK)],
                               _("Error downloading packages"),
                               secondary)
        if details:
            d.set_details("%s" %(details,))
        d.run()
        d.destroy()
        raise RevisorDownloadError

    def depDetails(self, mainwin):
        self.cfg.yumobj.tsInfo.makelists()
        if (len(self.cfg.yumobj.tsInfo.depinstalled) > 0 or
            len(self.cfg.yumobj.tsInfo.depupdated) > 0 or
            len(self.cfg.yumobj.tsInfo.depremoved) > 0):
            d = RevisorDetailsDialog(mainwin, gtk.MESSAGE_INFO,
                                 [('gtk-cancel', gtk.RESPONSE_CANCEL),
                                  (_("Continue"), gtk.RESPONSE_OK, 'gtk-ok')],
                                 _("Dependencies added"),
                                 _("Updating these packages requires "
                                   "additional package changes for proper "
                                   "operation."))

            b = gtk.TextBuffer()
            tag = b.create_tag('bold')
            tag.set_property('weight', pango.WEIGHT_BOLD)
            tag = b.create_tag('indented')
            tag.set_property('left-margin', 10)
            types=[(self.cfg.yumobj.tsInfo.depinstalled,_("Adding for dependencies:\n")),
                   (self.cfg.yumobj.tsInfo.depremoved, _("Removing for dependencies:\n")),
                   (self.cfg.yumobj.tsInfo.depupdated, _("Updating for dependencies:\n"))]
            for (lst, strng) in types:
                if len(lst) > 0:
                    i = b.get_end_iter()
                    b.insert_with_tags_by_name(i, strng, "bold")
                    for txmbr in lst:
                        i = b.get_end_iter()
                        (n,a,e,v,r) = txmbr.pkgtup
                        b.insert_with_tags_by_name(i, "%s-%s-%s\n" % (n,v,r),
                                                   "indented")
            d.set_details(buffer=b)
            timeout = 20
            if len(self.cfg.yumobj.tsInfo.depremoved) > 0:
                d.expand_details()
                timeout = None
            rc = d.run(timeout=timeout)
            d.destroy()

    default = {
        "WelcomeScreen": {
            "disp": displayWelcomeScreen,
            "next": "SelectMedia"
        },
        "SelectMedia": {
            "disp": displaySelectMedia,
            "next": "RevisorConfiguration"
        },
        "RevisorConfiguration": {
            "disp": displayRevisorConfiguration,
            "next": "LoadKickstart"
        },
        "LoadKickstart": {
            "disp": displayLoadKickstart,
            "next": "PackageSelection",
            "cond": "var = 'LMBasic' if self.cfg.kickstart_options_customize else 'ReadyScreen';         next = var if (self.cfg.use_kickstart_file and self.cfg.kickstart_manifest and not self.cfg.kickstart_manifest_customize) else False"
        },
        "PackageSelection": {
            "disp": displayPackageSelection,
            "next": "ReadyScreen",
            "cond": "next = 'LMBasic' if self.cfg.kickstart_options_customize and self.cfg.use_kickstart_file else False"
        },
        "ReadyScreen": {
            "disp": displayReadyScreen,
            "next": "BuildMedia",
            "cond": "next = 'LMBasic' if not self.cfg.use_kickstart_file and (self.cfg.media_live or self.base.plugins.return_true_boolean_from_plugins('media_virtualization') or self.cfg.media_utility) else False"
        },

        "LMBasic": {
            "disp": displayLMBasic,
            "next": "LMBootloader"
        },
        "LMBootloader": {
            "disp": displayLMBootloader,
            "next": "LMNetwork"
        },
        "LMNetwork": {
            "disp": displayLMNetwork,
            "next": "LMAuth"
        },
        "LMAuth": {
            "disp": displayLMAuth,
            "next": "LMSecurity"
        },
        "LMSecurity": {
            "disp": displayLMSecurity,
            "next": "LMDisplay"
        },
        "LMDisplay": {
            "disp": displayLMDisplay,
            "next": "LMUserCustomize"
        },
        "LMUserCustomize": {
            "disp": displayLMUserCustomize,
            "next": "BuildMedia"
        },

        "BuildMedia": {
            "next": False,           #using False to indicate the end...
            "disp": displayBuildMedia
        }
    }

    current = "WelcomeScreen"
    backlog = []

    def next(self):
        if self.current:
            self.backlog.append(self.current)

            next = False
            if self.default[self.current].has_key('cond'):
                exec(self.default[self.current]['cond'])
            if next:
                self.current = next
            else:
                self.current = self.default[self.current]['next']
            self.default[self.current]['disp'](self)

    def back(self):
        self.current = self.backlog[-1]
        self.default[self.current]['disp'](self)
        self.backlog = self.backlog[:-1]

# FIXME!
#            if rc != gtk.RESPONSE_OK:
#                self._undoDepInstalls()
#                raise PirutError
