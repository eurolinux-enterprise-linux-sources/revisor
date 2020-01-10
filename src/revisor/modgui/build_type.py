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

class BuildType:
    def __init__(self, gui):
        self.gui = gui
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()
        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(PIXMAPS_FILES + "header_main.png")

        self.restore_options()

    def connect_button_signals(self):
        sigs = { "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_information_clicked": self.button_information_clicked }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "build-type")

    def button_back_clicked(self, button):
        pass

    def store_options(self):
        pass

    def restore_options(self):
        pass

    def button_forward_clicked(self, button):
        self.store_options()
        self.gui.displayRevisorConfiguration()
