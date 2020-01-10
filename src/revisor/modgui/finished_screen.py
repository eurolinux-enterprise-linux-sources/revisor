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

# Translation
from revisor.translate import _, N_

class FinishedScreen:
    def __init__(self, gui):
        self.gui = gui
        self.cfg = self.gui.cfg
        self.frame_xml = gui.frame_xml

        self.add_buttons()

        self.connect_button_signals()
        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(None)

        self.compose_results_locations = self.frame_xml.get_widget("compose_results_locations")

        if self.cfg.destination_directory == "":
           self.compose_results_locations.set_text(_("Check current directory."))
        else:
           self.compose_results_locations.set_text(self.cfg.destination_directory)

    def connect_button_signals(self):
        sigs = { "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_information_clicked": self.button_information_clicked }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def add_buttons(self):
        self.gui.base_buttons_xml = gtk.glade.XML(GLADE_FILES + "finished_buttons.glade", domain=domain)
        self.button_hbox = self.gui.base_buttons_xml.get_widget("button_hbox")

        self.button_vbox = self.gui.frame_xml.get_widget("button_vbox")
        self.button_vbox.add(self.button_hbox)
        self.base_statusbar_xml = gtk.glade.XML(GLADE_FILES + "base_statusbar.glade", domain=domain)
        self.statusbar = self.base_statusbar_xml.get_widget("statusbar")
        self.button_vbox.pack_end(self.statusbar,expand=False,fill=False)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "finished")

