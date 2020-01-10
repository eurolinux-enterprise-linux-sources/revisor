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

import string

# Import constants
from revisor.constants import *

# Translation
from revisor.translate import _, N_

class LMNetwork:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()

        self.network_frame = self.frame_xml.get_widget("outer_frame")
        self.network_device_tree = self.frame_xml.get_widget("network_device_tree")
        self.add_device_button = self.frame_xml.get_widget("add_device_button")
        self.edit_device_button = self.frame_xml.get_widget("edit_device_button")
        self.delete_device_button = self.frame_xml.get_widget("delete_device_button")
        self.network_device_dialog = self.frame_xml.get_widget("network_device_dialog")
        self.network_device_dialog.connect("delete-event", self.resetDialog)

        self.network_device_option_menu = self.frame_xml.get_widget("network_device_option_menu")
        self.network_type_option_menu = self.frame_xml.get_widget("network_type_option_menu")
        self.network_type_hbox = self.frame_xml.get_widget("network_type_hbox")

        self.ip_entry1 = self.frame_xml.get_widget("ip_entry1")
        self.ip_entry2 = self.frame_xml.get_widget("ip_entry2")
        self.ip_entry3 = self.frame_xml.get_widget("ip_entry3")
        self.ip_entry4 = self.frame_xml.get_widget("ip_entry4")
        self.netmask_entry1 = self.frame_xml.get_widget("netmask_entry1")
        self.netmask_entry2 = self.frame_xml.get_widget("netmask_entry2")
        self.netmask_entry3 = self.frame_xml.get_widget("netmask_entry3")
        self.netmask_entry4 = self.frame_xml.get_widget("netmask_entry4")
        self.gw_entry1 = self.frame_xml.get_widget("gw_entry1")
        self.gw_entry2 = self.frame_xml.get_widget("gw_entry2")
        self.gw_entry3 = self.frame_xml.get_widget("gw_entry3")
        self.gw_entry4 = self.frame_xml.get_widget("gw_entry4")
        self.nameserver_entry1 = self.frame_xml.get_widget("nameserver_entry1")
        self.nameserver_entry2 = self.frame_xml.get_widget("nameserver_entry2")
        self.nameserver_entry3 = self.frame_xml.get_widget("nameserver_entry3")
        self.nameserver_entry4 = self.frame_xml.get_widget("nameserver_entry4")
        self.network_table = self.frame_xml.get_widget("network_table")
        self.network_ok_button = self.frame_xml.get_widget("network_ok_button")
        self.network_cancel_button = self.frame_xml.get_widget("network_cancel_button")

        self.network_device_tree.get_selection().connect("changed", self.rowSelected)
        self.add_device_button.connect("clicked", self.showAddNetworkDialog)
        self.edit_device_button.connect("clicked", self.showEditNetworkDialog)
        self.delete_device_button.connect("clicked", self.deleteDevice)

        self.network_device_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
                                                  gobject.TYPE_STRING, gobject.TYPE_STRING,
                                                  gobject.TYPE_STRING, gobject.TYPE_STRING,)

        self.network_device_tree.set_model(self.network_device_store)

        self.network_device_tree.set_property("headers-visible", True)
        col = gtk.TreeViewColumn("Device", gtk.CellRendererText(), text=0)
        self.network_device_tree.append_column(col)

        col = gtk.TreeViewColumn("Network Type", gtk.CellRendererText(), text=1)
        self.network_device_tree.append_column(col)


        self.deviceMenu = gtk.Menu()
        self.deviceList = []

        for i in range(17):
            dev = "eth%d" %i
            item = gtk.MenuItem(dev)
            self.deviceList.append(dev)
            self.deviceMenu.append(item)

        self.network_device_option_menu.set_menu(self.deviceMenu)
        self.network_device_option_menu.show_all()

        self.typeMenu = gtk.Menu()
        item = gtk.MenuItem(_("DHCP"))
        self.typeMenu.append(item)
        item = gtk.MenuItem(_("Static IP"))
        self.typeMenu.append(item)
        item = gtk.MenuItem(_("BOOTP"))
        self.typeMenu.append(item)

        self.network_type_option_menu.set_menu(self.typeMenu)
        self.network_type_hbox.show_all()

        self.network_type_option_menu.connect("changed", self.typeChanged)
        self.network_cancel_button.connect("clicked", self.resetDialog)
        self.network_frame.show_all()

        if not "NetworkManager" in self.cfg.ksobj._get("packages","packageList") or "NetworkManager" in self.cfg.ksobj._get("packages","excludedList"):
            self.frame_xml.get_widget("checkbutton_use_networkmanager").set_active(False)
            self.frame_xml.get_widget("checkbutton_use_networkmanager").set_sensitive(False)

        self.restore_options()

    def showAddNetworkDialog(self, *args):
        self.handler = self.network_ok_button.connect("clicked", self.addDevice)

        #Let's find the last eth device in the list and increment by one to
        #fill in the option menu with the next device
        device = None
        iter = self.network_device_store.get_iter_first()
        while iter:
            device = self.network_device_store.get_value(iter, 0)
            iter = self.network_device_store.iter_next(iter)

        if device == None:
            num = 0
        else:
            num = int(device[3:])
            if num < 15:
                num = num + 1

        self.network_device_option_menu.set_history(num)
        self.network_device_dialog.show_all()

    def showEditNetworkDialog(self, *args):
        rc = self.network_device_tree.get_selection().get_selected()

        if rc:
            store, iter = rc

            device = self.network_device_store.get_value(iter, 0)
            num = self.deviceList.index(device)
            self.network_device_option_menu.set_history(num)

            type = self.network_device_store.get_value(iter, 1)
            if type == _("DHCP"):
                self.network_type_option_menu.set_history(0)
            elif type == _("Static IP"):
                self.network_type_option_menu.set_history(1)

                ip = self.network_device_store.get_value(iter, 2)
                ip1, ip2, ip3, ip4 = string.split(ip, ".")
                self.ip_entry1.set_text(ip1)
                self.ip_entry2.set_text(ip2)
                self.ip_entry3.set_text(ip3)
                self.ip_entry4.set_text(ip4)

                ip = self.network_device_store.get_value(iter, 3)
                ip1, ip2, ip3, ip4 = string.split(ip, ".")
                self.netmask_entry1.set_text(ip1)
                self.netmask_entry2.set_text(ip2)
                self.netmask_entry3.set_text(ip3)
                self.netmask_entry4.set_text(ip4)

                ip = self.network_device_store.get_value(iter, 4)
                ip1, ip2, ip3, ip4 = string.split(ip, ".")
                self.gw_entry1.set_text(ip1)
                self.gw_entry2.set_text(ip2)
                self.gw_entry3.set_text(ip3)
                self.gw_entry4.set_text(ip4)

                ip = self.network_device_store.get_value(iter, 5)
                ip1, ip2, ip3, ip4 = string.split(ip, ".")
                self.nameserver_entry1.set_text(ip1)
                self.nameserver_entry2.set_text(ip2)
                self.nameserver_entry3.set_text(ip3)
                self.nameserver_entry4.set_text(ip4)

        self.handler = self.network_ok_button.connect("clicked", self.editDevice, iter)
        self.network_device_dialog.show_all()

    def deviceIsFilledIn(self):
        return self.ip_entry1.get_text() != "" and self.ip_entry2.get_text() != "" and \
               self.ip_entry3.get_text() != "" and self.ip_entry4.get_text() != "" and \
               self.netmask_entry1.get_text() != "" and self.netmask_entry2.get_text() != "" and \
               self.netmask_entry3.get_text() != "" and self.netmask_entry4.get_text() != "" and \
               self.gw_entry1.get_text() != "" and self.gw_entry2.get_text() != "" and \
               self.gw_entry3.get_text() != "" and self.gw_entry4.get_text() != "" and \
               self.nameserver_entry1.get_text() != "" and self.nameserver_entry2.get_text() != "" and \
               self.nameserver_entry3.get_text() != "" and self.nameserver_entry4.get_text() != ""

    def addDevice(self, *args):
        devNum = self.network_device_option_menu.get_history()
        devName = self.deviceList[devNum]

        if self.doesDeviceExist(devName) is None:
            return

        if self.network_type_option_menu.get_history() == 0:
            iter = self.network_device_store.append()
            self.network_device_store.set_value(iter, 0, devName)
            self.network_device_store.set_value(iter, 1, _("DHCP"))
        elif self.network_type_option_menu.get_history() == 2:
            iter = self.network_device_store.append()
            self.network_device_store.set_value(iter, 0, devName)
            self.network_device_store.set_value(iter, 1, _("BOOTP"))
        else:
            if not self.deviceIsFilledIn():
                text = _("Please fill in the network information")
                dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, text)
                dlg.set_position(gtk.WIN_POS_CENTER)
                dlg.set_modal(True)
                rc = dlg.run()
                dlg.destroy()
                return None

            iter = self.network_device_store.append()
            self.network_device_store.set_value(iter, 0, devName)
            self.network_device_store.set_value(iter, 1, _("Static IP"))

            ipBuf = ("%s.%s.%s.%s" %
                     (self.ip_entry1.get_text(),
                      self.ip_entry2.get_text(),
                      self.ip_entry3.get_text(),
                      self.ip_entry4.get_text()))
            self.network_device_store.set_value(iter, 2, ipBuf)

            netmaskBuf = ("%s.%s.%s.%s" %
                          (self.netmask_entry1.get_text(),
                           self.netmask_entry2.get_text(),
                           self.netmask_entry3.get_text(),
                           self.netmask_entry4.get_text()))
            self.network_device_store.set_value(iter, 3, netmaskBuf)

            gatewayBuf = ("%s.%s.%s.%s" %
                          (self.gw_entry1.get_text(),
                           self.gw_entry2.get_text(),
                           self.gw_entry3.get_text(),
                           self.gw_entry4.get_text()))
            self.network_device_store.set_value(iter, 4, gatewayBuf)

            nameserverBuf = ("%s.%s.%s.%s" %
                             (self.nameserver_entry1.get_text(),
                              self.nameserver_entry2.get_text(),
                              self.nameserver_entry3.get_text(),
                              self.nameserver_entry4.get_text()))
            self.network_device_store.set_value(iter, 5, nameserverBuf)

#        iter = firewall.trustedStore.append()
#        firewall.trustedStore.set_value(iter, 0, False)
#        firewall.trustedStore.set_value(iter, 1, devName)

        self.resetDialog()

    def editDevice(self, button, iter):
        devNum = self.network_device_option_menu.get_history()
        devName = self.deviceList[devNum]

        if self.network_device_store.get_value(iter, 0) != devName:
            if self.doesDeviceExist(devName) is None:
                return

        self.network_device_store.set_value(iter, 0, devName)

        if self.network_type_option_menu.get_history() == 0:
            self.network_device_store.set_value(iter, 1, _("DHCP"))
        elif self.network_type_option_menu.get_history() == 2:
            self.network_device_store.set_value(iter, 1, _("BOOTP"))
        else:
            if not self.deviceIsFilledIn():
                text = _("Please fill in the network information")
                dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, text)
                dlg.set_position(gtk.WIN_POS_CENTER)
                dlg.set_modal(True)
                rc = dlg.run()
                dlg.destroy()
                return None

            self.network_device_store.set_value(iter, 1, _("Static IP"))

            ipBuf = ("%s.%s.%s.%s" %
                     (self.ip_entry1.get_text(),
                      self.ip_entry2.get_text(),
                      self.ip_entry3.get_text(),
                      self.ip_entry4.get_text()))
            self.network_device_store.set_value(iter, 2, ipBuf)

            netmaskBuf = ("%s.%s.%s.%s" %
                          (self.netmask_entry1.get_text(),
                           self.netmask_entry2.get_text(),
                           self.netmask_entry3.get_text(),
                           self.netmask_entry4.get_text()))
            self.network_device_store.set_value(iter, 3, netmaskBuf)

            gatewayBuf = ("%s.%s.%s.%s" %
                          (self.gw_entry1.get_text(),
                           self.gw_entry2.get_text(),
                           self.gw_entry3.get_text(),
                           self.gw_entry4.get_text()))
            self.network_device_store.set_value(iter, 4, gatewayBuf)

            nameserverBuf = ("%s.%s.%s.%s" %
                             (self.nameserver_entry1.get_text(),
                              self.nameserver_entry2.get_text(),
                              self.nameserver_entry3.get_text(),
                              self.nameserver_entry4.get_text()))
            self.network_device_store.set_value(iter, 5, nameserverBuf)

        self.resetDialog()

    def deleteDevice(self, *args):
        rc = self.network_device_tree.get_selection().get_selected()

        if rc:
            store, iter = rc
            self.network_device_store.remove(iter)

    def doesDeviceExist(self, devName):
        iter = self.network_device_store.get_iter_first()

        while iter:
            if devName == self.network_device_store.get_value(iter, 0):
                text = _("A network device with the name %s already exists.  Please choose another device name") % devName
                dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, text)
                dlg.set_position(gtk.WIN_POS_CENTER)
                dlg.set_modal(True)
                rc = dlg.run()
                dlg.destroy()
                return None
            iter = self.network_device_store.iter_next(iter)

        return 0

    def resetDialog(self, *args):
        self.network_device_option_menu.set_history(0)
        self.network_type_option_menu.set_history(0)
        self.ip_entry1.set_text("")
        self.ip_entry2.set_text("")
        self.ip_entry3.set_text("")
        self.ip_entry4.set_text("")

        self.netmask_entry1.set_text("")
        self.netmask_entry2.set_text("")
        self.netmask_entry3.set_text("")
        self.netmask_entry4.set_text("")

        self.gw_entry1.set_text("")
        self.gw_entry2.set_text("")
        self.gw_entry3.set_text("")
        self.gw_entry4.set_text("")

        self.nameserver_entry1.set_text("")
        self.nameserver_entry2.set_text("")
        self.nameserver_entry3.set_text("")
        self.nameserver_entry4.set_text("")

        self.network_ok_button.disconnect(self.handler)
        self.network_device_dialog.hide()
        return True

    def store_options(self):
        self.cfg.ksobj._set("network","network",[])
        iter = self.network_device_store.get_iter_first()

        while iter:

            nd = self.cfg.ksobj._NetworkData()

            if self.network_device_store.get_value(iter, 1) == _("DHCP"):
                nd.bootProto = "dhcp"
            elif self.network_device_store.get_value(iter, 1) == _("BOOTP"):
                nd.bootProto = "bootp"
            else:
                nd.bootProto = "static"
                nd.ip = self.network_device_store.get_value(iter, 2)
                nd.netmask = self.network_device_store.get_value(iter, 3)
                nd.gateway = self.network_device_store.get_value(iter, 4)
                nd.nameserver = self.network_device_store.get_value(iter, 5)

            nd.device = self.network_device_store.get_value(iter, 0)
            self.cfg.ksobj._network_add(nd)
            iter = self.network_device_store.iter_next(iter)

    def typeChanged(self, *args):
        if self.network_type_option_menu.get_history() == 1:
            self.network_table.set_sensitive(True)
        else:
            self.network_table.set_sensitive(False)

    def rowSelected(self, *args):
        store, iter = self.network_device_tree.get_selection().get_selected()
        if iter == None:
            self.edit_device_button.set_sensitive(False)
            self.delete_device_button.set_sensitive(False)
        else:
            self.edit_device_button.set_sensitive(True)
            self.delete_device_button.set_sensitive(True)

    def check_options(self):
        return True

    def restore_options(self):
        self.network_device_store.clear()

        for nic in self.cfg.ksobj._get("network","network"):
            iter = self.network_device_store.append()

            if nic.device != "":
                self.network_device_store.set_value(iter, 0, nic.device)
#                firewall_iter = firewall.trustedStore.append()
#                firewall.trustedStore.set_value(firewall_iter, 0, False)
#                firewall.trustedStore.set_value(firewall_iter, 1, nic.device)

            if nic.bootProto != "":
                if nic.bootProto == "dhcp":
                    self.network_device_store.set_value(iter, 1, _("DHCP"))
                elif nic.bootProto == "static":
                    self.network_device_store.set_value(iter, 1, _("Static IP"))
                elif nic.bootProto == "bootp":
                    self.network_device_store.set_value(iter, 1, _("BOOTP"))

            if nic.ip != "":
                self.network_device_store.set_value(iter, 2, nic.ip)

            if nic.netmask != "":
                self.network_device_store.set_value(iter, 3, nic.netmask)

            if nic.gateway != "":
                self.network_device_store.set_value(iter, 4, nic.gateway)

            if nic.nameserver != "":
                self.network_device_store.set_value(iter, 5, nic.nameserver)


    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_information_clicked": self.button_information_clicked }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "networking")

    def button_back_clicked(self, button):
        self.gui.back()

    def button_forward_clicked(self, button):
        if not self.check_options():
           pass
        else:
            self.store_options()
            self.gui.next()
