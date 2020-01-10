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
import os
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk

import pykickstart
import yum.repos

import revisor

# Import constants
from revisor.constants import *

# Translation
from revisor.translate import _, N_

class LoadKickstart:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg

        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()

        self.cfg.ksobj._reset()

        # Get me some widgets that I can refer to

        self.kickstart_file = self.frame_xml.get_widget("kickstart_file")
        self.kickstart_repos = self.frame_xml.get_widget("checkbutton_kickstart_repos")
        self.kickstart_manifest = self.frame_xml.get_widget("checkbutton_kickstart_manifest")
        self.kickstart_manifest_customize = self.frame_xml.get_widget("checkbutton_kickstart_manifest_customize")
        self.kickstart_options_customize = self.frame_xml.get_widget("checkbutton_kickstart_options_customize")
        self.kickstart_include = self.frame_xml.get_widget("checkbutton_kickstart_include")
        self.kickstart_default = self.frame_xml.get_widget("checkbutton_kickstart_default")

        self.restore_options()
        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(PIXMAPS_FILES + "header_kickstart.png")

        # Set advanced kickstart config for only live media, for now
        if not self.cfg.media_live_optical and not self.cfg.media_live_thumb:
            self.kickstart_options_customize.set_active(False)
            self.kickstart_options_customize.set_sensitive(False)

        if not self.cfg.media_installation:
            self.kickstart_include.set_sensitive(False)
            self.kickstart_default.set_sensitive(False)

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_open_kickstart_file_clicked": self.open_kickstart_file_dialog,
                 "on_checkbutton_kickstart_manifest_clicked": self.use_kickstart_manifest_clicked,
                 "on_checkbutton_kickstart_manifest_customize_clicked": self.customize_kickstart_manifest_clicked,
                 "on_checkbutton_kickstart_options_customize_clicked": self.kickstart_options_customize_clicked,
                 "on_checkbutton_kickstart_include_clicked": self.kickstart_include_clicked,
                 "on_checkbutton_kickstart_default_clicked": self.kickstart_default_clicked }

        self.gui.frame_xml.signal_autoconnect(sigs)

    def use_kickstart_manifest_clicked(self,button):
        """Actions to take when the use of the kickstart manifest has been altered"""
        self.kickstart_manifest_customize.set_sensitive(self.kickstart_manifest.get_active())

    def customize_kickstart_manifest_clicked(self,button):
        self.cfg.kickstart_manifest_customize = self.kickstart_manifest_customize.get_active()

    def kickstart_options_customize_clicked(self,button):
        self.cfg.kickstart_options_customize = self.kickstart_options_customize.get_active()

    def kickstart_include_clicked(self,button):
        self.cfg.kickstart_include = self.kickstart_include.get_active()

    def kickstart_default_clicked(self,button):
        self.cfg.kickstart_default = self.kickstart_default.get_active()

    def open_kickstart_file_dialog(self, button):
        self.dialog_filechooser_xml = gtk.glade.XML(GLADE_FILES + "dialog_filechooser.glade", domain=domain)
        self.dialog_filechooser = self.dialog_filechooser_xml.get_widget("dialog_filechooser")
        self.dialog_filechooser.set_modal(True)
        self.dialog_filechooser.set_transient_for(self.gui.main_window)
        button_open = self.dialog_filechooser_xml.get_widget("button_open")
        button_cancel = self.dialog_filechooser_xml.get_widget("button_cancel")

        if os.access("/etc/revisor/", os.F_OK):
            self.dialog_filechooser.set_current_folder("/etc/revisor/")

        sigs = { "on_button_filechooser_open_clicked": self.button_filechooser_open_clicked,
                 "on_button_filechooser_cancel_clicked": self.button_filechooser_cancel_clicked }
        self.dialog_filechooser_xml.signal_autoconnect(sigs)

        self.dialog_filechooser.show()

    def button_filechooser_open_clicked(self, button):
        if self.dialog_filechooser.get_filename():
            self.kickstart_file.set_text(self.dialog_filechooser.get_filename())
            self.dialog_filechooser.hide()
            self.dialog_filechooser.destroy()

    def check_options(self):
        if self.kickstart_file.get_text() == "":
            self.cfg.use_kickstart_file = False
            self.cfg.kickstart_file = ""
            self.cfg.kickstart_manifest = False
            self.cfg.kickstart_manifest_customize = False
            return True
        elif not os.access(self.kickstart_file.get_text(), os.R_OK):
            self.cfg.use_kickstart_file = False
            self.log.error(_("Kickstart file %s not accessible.") % self.kickstart_file.get_text())
            return False
        elif self.cfg.test_ks(self.kickstart_file.get_text()):
            self.cfg.kickstart_file = self.kickstart_file.get_text()
            self.cfg.use_kickstart_file = True
            return True
        else:
            self.log.error(_("Kickstart file not good."))
            return False

        return True

    def restore_options(self):
        self.kickstart_file.set_text(self.cfg.kickstart_file)
        self.kickstart_repos.set_active(self.cfg.kickstart_repos)
        self.kickstart_manifest.set_active(self.cfg.kickstart_manifest)
        self.kickstart_manifest_customize.set_sensitive(self.kickstart_manifest.get_active())
        self.kickstart_manifest_customize.set_active(self.cfg.kickstart_manifest_customize)
        self.kickstart_options_customize.set_active(self.cfg.kickstart_options_customize)
        self.kickstart_include.set_active(self.cfg.kickstart_include)
        self.kickstart_default.set_active(self.cfg.kickstart_default)

    def store_options(self):
        if self.cfg.use_kickstart_file:
            self.cfg.kickstart_file = self.kickstart_file.get_text()
            if os.path.isfile(self.cfg.kickstart_file):
                self.cfg.load_kickstart(self.cfg.kickstart_file)
            self.cfg.kickstart_manifest = self.kickstart_manifest.get_active()

            if self.cfg.kickstart_repos:
                self.cfg._repos_kickstart = self.cfg.ksobj._get("repo","repoList") or []

            if self.cfg.kickstart_manifest:
                self.cfg.kickstart_manifest_customize = self.kickstart_manifest_customize.get_active()
            else:
                self.cfg.kickstart_manifest_customize = False
                self.cfg.ksobj._set("packages","groupList",[])
                self.cfg.ksobj._set("packages","excludedList",[])
                self.cfg.ksobj._set("packages","packageList",[])
            self.cfg.kickstart_options_customize = self.kickstart_options_customize.get_active()
        else:
            self.cfg.kickstart_file = ""

    def button_filechooser_cancel_clicked(self, button):
        self.dialog_filechooser.hide()
        self.dialog_filechooser.destroy()

    def button_back_clicked(self, button):
        self.store_options()
        self.gui.back()
        self.gui.displayRevisorConfiguration()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            self.gui.next()
