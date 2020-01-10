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

class LMSecurity:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()

        self.firewall_frame = self.frame_xml.get_widget("outer_frame")
        self.firewall_vbox = self.frame_xml.get_widget("firewall_vbox")
        self.firewall_label_box = self.frame_xml.get_widget("firewall_label_box")
        self.securityOptionMenu = self.frame_xml.get_widget("securityOptionMenu")
        self.selinuxOptionMenu = self.frame_xml.get_widget("selinuxOptionMenu")
        self.firewallDefaultRadio = self.frame_xml.get_widget("firewallDefaultRadio")
        self.trusted_devices_label = self.frame_xml.get_widget("trusted_devices_label")
        self.allow_incoming_label = self.frame_xml.get_widget("allow_incoming_label")
        self.fnnirewall_ports_label = self.frame_xml.get_widget("firewall_ports_label")
        self.firewall_ports_entry = self.frame_xml.get_widget("firewall_ports_entry")
        self.customTable = self.frame_xml.get_widget("customTable")
        self.customFrame = self.frame_xml.get_widget("customFrame")

        self.securityOptionMenu.connect("changed", self.disable_firewall)

        #create table with custom checklists
        self.label1 = gtk.Label (_("Trusted devices:"))
        self.label1.set_alignment (0.0, 0.0)
        self.customTable.attach (self.label1, 0, 1, 2, 3, gtk.FILL, gtk.FILL, 5, 5)

        self.trustedStore = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)

        self.trustedView = gtk.TreeView()
        self.trustedView.set_headers_visible(False)
        self.trustedView.set_model(self.trustedStore)
        checkbox = gtk.CellRendererToggle()
        checkbox.connect("toggled", self.item_toggled, self.trustedStore)
        col = gtk.TreeViewColumn('', checkbox, active=0)
        col.set_fixed_width(20)
        col.set_clickable(True)
        self.trustedView.append_column(col)

        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.trustedView.append_column(col)

        for device in self.cfg.ksobj._get("network","network"):
            iter = self.trustedStore.append()
            self.trustedStore.set_value(iter,0,False)
            self.trustedStore.set_value(iter,1,device.device)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.trustedView)
        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        viewport.add(sw)
        self.customTable.attach (viewport, 1, 2, 2, 3, gtk.EXPAND|gtk.FILL, gtk.FILL, 5, 5)

        self.label2 = gtk.Label (_("Trusted services:"))
        self.label2.set_alignment (0.0, 0.0)

        self.incomingStore = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        self.incomingView = gtk.TreeView()
        self.incomingView.set_headers_visible(False)
        self.incomingView.set_model(self.incomingStore)
        checkbox = gtk.CellRendererToggle()
        checkbox.connect("toggled", self.item_toggled, self.incomingStore)
        col = gtk.TreeViewColumn('', checkbox, active=0)
        col.set_fixed_width(20)
        col.set_clickable(True)
        self.incomingView.append_column(col)

        col = gtk.TreeViewColumn("", gtk.CellRendererText(), text=1)
        self.incomingView.append_column(col)

        self.list = {"SSH":"ssh", "Telnet":"telnet", "WWW (HTTP)":"http",
                     "Mail (SMTP)":"smtp", "FTP":"ftp"}

        for item in self.list.keys():
            iter = self.incomingStore.append()
            self.incomingStore.set_value(iter, 0, False)
            self.incomingStore.set_value(iter, 1, item)

        viewport = gtk.Viewport()
        viewport.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        viewport.add(self.incomingView)

        self.customTable.attach (self.label2, 0, 1, 3, 4, gtk.FILL, gtk.FILL, 5, 5)
        self.customTable.attach (viewport, 1, 2, 3, 4, gtk.EXPAND|gtk.FILL, gtk.FILL, 5, 5)

        self.label3 = gtk.Label (_("Other ports: (1029:tcp)"))
        self.label3.set_alignment (0.0, 0.0)
        self.portsEntry = gtk.Entry ()
        self.customTable.attach (self.label3, 0, 1, 4, 5, gtk.FILL, gtk.FILL, 5, 5)
        self.customTable.attach (self.portsEntry, 1, 2, 4, 5, gtk.EXPAND|gtk.FILL, gtk.FILL, 5, 5)

        self.firewall_vbox.show_all()

    def item_toggled(self, data, row, store):
        iter = store.get_iter((int(row),))
        val = store.get_value(iter, 0)
        store.set_value(iter, 0 , not val)

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "security")

    def button_back_clicked(self, button):
        self.gui.back()

    def check_options(self):
        return True

    def store_options(self):
        pass

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            self.gui.next()

    def disable_firewall(self, widget):
        state = self.securityOptionMenu.get_history()

        if state == 0:
            self.customTable.set_sensitive (True)
        else:
            self.customTable.set_sensitive (False)
