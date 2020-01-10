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
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk

# Import constants
from revisor.constants import *

sys.path.append("/usr/share/system-config-kickstart/")
import xconfig

# Translation
from revisor.translate import _, N_

class LMDisplay:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()
        self.xconfig_check = self.frame_xml.get_widget("config_x_button")
        self.xconfig_notebook = self.frame_xml.get_widget("xconfig_notebook")

        self.xconfig = xconfig.xconfig(self.frame_xml,self.cfg.ksobj._handler())

        # Update what we can configure
        self.cfg.check_package_selection()
        self.xconfig_check.set_sensitive(self.cfg.package_Xorg)

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_x_config_toggled": self.button_x_config_toggled }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "display-configuration")

    def button_back_clicked(self, button):
        self.gui.back()

    def button_forward_clicked(self, button):
        self.xconfig.formToKickstart()
        self.gui.next()

    def button_x_config_toggled(self, widget):
        self.xconfig_notebook.set_sensitive(self.xconfig_check.get_active())

    def check_options(self):
        # Is never called, don't know what does the checking...
        pass

    def restore_options(self):
        # Is never called, xconfig.applyKsData() does this
        pass

    def store_options(self):
        # Is never called, xconfig.formToKsData() does this
        pass
