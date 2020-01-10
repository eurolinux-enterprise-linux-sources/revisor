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

import string
import getopt

class LMAuth:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()

        self.use_shadow_check = self.frame_xml.get_widget("use_shadow")
        self.use_md5_check = self.frame_xml.get_widget("use_md5")
        self.use_nis_check = self.frame_xml.get_widget("use_nis")
        self.use_ldap_check = self.frame_xml.get_widget("use_ldap")
        self.use_kerberos_check = self.frame_xml.get_widget("use_kerberos")
        self.use_hesiod_check = self.frame_xml.get_widget("use_hesiod")
        self.use_samba_check = self.frame_xml.get_widget("use_samba")
        self.use_nscd_check = self.frame_xml.get_widget("use_nscd")

        self.restore_options()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = {
                "on_use_shadow_toggled": self.use_shadow_toggled,
                "on_use_md5_toggled": self.use_md5_toggled,
                "on_use_nis_toggled": self.use_nis_toggled,
                "on_use_ldap_toggled": self.use_ldap_toggled,
                "on_use_kerberos_toggled": self.use_kerberos_toggled,
                "on_use_hesiod_toggled": self.use_hesiod_toggled,
                "on_use_samba_toggled": self.use_samba_toggled,
                "on_use_nscd_toggled": self.use_nscd_toggled,
                "on_use_nis_broadcast_toggled": self.use_nis_broadcast_toggled
               }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def use_shadow_toggled(self):
        self.cfg.lm_use_shadow = self.use_shadow_check.get_active()

    def use_md5_toggled(self):
        self.cfg.lm_use_md5 = self.use_md5_check.get_active()

    def use_nis_toggled(self, gobject):
        # Enable/Disable the options in the NIS tab
        use_nis = self.use_nis_check.get_active()
        self.frame_xml.get_widget("nis_domain").set_sensitive(use_nis)
        self.frame_xml.get_widget("nis_domain_label").set_sensitive(use_nis)
        self.frame_xml.get_widget("nis_server").set_sensitive(use_nis)
        self.frame_xml.get_widget("nis_server_label").set_sensitive(use_nis)
        self.frame_xml.get_widget("nis_broadcast").set_sensitive(use_nis)

    def use_nis_broadcast_toggled(self,gobject):
        if self.frame_xml.get_widget("nis_broadcast").get_active():
            self.frame_xml.get_widget("nis_server").set_sensitive(False)
            self.frame_xml.get_widget("nis_server_label").set_sensitive(False)
        else:
            self.frame_xml.get_widget("nis_server").set_sensitive(True)
            self.frame_xml.get_widget("nis_server_label").set_sensitive(True)

    def use_ldap_toggled(self, gobject):
        use_ldap = self.use_ldap_check.get_active()
        self.frame_xml.get_widget("ldap_server").set_sensitive(use_ldap)
        self.frame_xml.get_widget("ldap_server_label").set_sensitive(use_ldap)
        self.frame_xml.get_widget("ldap_dn").set_sensitive(use_ldap)
        self.frame_xml.get_widget("ldap_dn_label").set_sensitive(use_ldap)

    def use_kerberos_toggled(self, gobject):
        use_kerberos = self.use_kerberos_check.get_active()
        self.frame_xml.get_widget("kerberos_realm").set_sensitive(use_kerberos)
        self.frame_xml.get_widget("kerberos_realm_label").set_sensitive(use_kerberos)
        self.frame_xml.get_widget("kerberos_kdc").set_sensitive(use_kerberos)
        self.frame_xml.get_widget("kerberos_kdc_label").set_sensitive(use_kerberos)
        self.frame_xml.get_widget("kerberos_master").set_sensitive(use_kerberos)
        self.frame_xml.get_widget("kerberos_master_label").set_sensitive(use_kerberos)

    def use_hesiod_toggled(self, gobject):
        use_hesiod = self.use_hesiod_check.get_active()
        self.frame_xml.get_widget("hesiod_lhs").set_sensitive(use_hesiod)
        self.frame_xml.get_widget("hesiod_lhs_label").set_sensitive(use_hesiod)
        self.frame_xml.get_widget("hesiod_rhs").set_sensitive(use_hesiod)
        self.frame_xml.get_widget("hesiod_rhs_label").set_sensitive(use_hesiod)

    def use_samba_toggled(self, gobject):
        use_samba = self.use_samba_check.get_active()
        self.frame_xml.get_widget("samba_servers").set_sensitive(use_samba)
        self.frame_xml.get_widget("samba_servers_label").set_sensitive(use_samba)
        self.frame_xml.get_widget("samba_workgroup").set_sensitive(use_samba)
        self.frame_xml.get_widget("samba_workgroup_label").set_sensitive(use_samba)

    def use_nscd_toggled(self, gobject):
        use_nscd = self.use_nscd_check.get_active()

    def check_options(self):
        return True

    def restore_options(self):
        # Restore from defaults
        # Override from loaded kickstart data
        # Override from current configstore/kickstart data
        if self.cfg.ksobj._get("authconfig","authconfig") != "":
            authstr = self.cfg.ksobj._get("authconfig","authconfig")
            opts, args = getopt.getopt(authstr, "d:h",["enablemd5", "enablenis",
                                       "nisdomain=", "nisserver=", "useshadow", "enableshadow",
                                       "enableldap", "enableldapauth", "ldapserver=", "ldapbasedn=",
                                       "enableldaptls",
                                       "enablekrb5", "krb5realm=", "krb5kdc=", "krb5adminserver=",
                                       "enablehesiod", "hesiodlhs=", "hesiodrhs=", "enablesmbauth",
                                       "smbservers=", "smbworkgroup=", "enablecache"])

            for opt, value in opts:
                if opt == "--enablemd5cache":
                    self.use_md5_check.set_active(True)

                if opt == "--enableshadow" or opt == "--useshadow":
                    self.use_shadow_check.set_active(True)

                if opt == "--enablenis":
                    self.use_nis_check.set_active(True)
                    self.frame_xml.get_widget("nis_broadcast").set_active(True)

                if opt == "--nisdomain":
                    self.use_nis_check.set_active(True)
                    self.frame_xml.get_widget("nis_domain").set_text(value)
                    self.frame_xml.get_widget("nis_broadcast").set_active(True)

                if opt == "--nisserver":
                    self.use_nis_check.set_active(True)
                    self.frame_xml.get_widget("nis_broadcast").set_active(False)
                    self.frame_xml.get_widget("nis_server").set_text(value)

                if opt == "--enableldap":
                    self.use_ldap_check.set_active(True)

                if opt == "--ldapserver":
                    self.frame_xml.get_widget("ldap_server").set_text(value)
                    self.use_ldap_check.set_active(True)

                if opt == "--ldapbasedn":
                    self.frame_xml.get_widget("ldap_dn").set_text(value)
                    self.use_ldap_check.set_active(True)

                if opt == "--enablekrb5":
                    self.use_kerberos_check.set_active(True)

                if opt == "--krb5realm":
                    self.frame_xml.get_widget("kerberos_realm").set_text(value)
                    self.use_kerberos_check.set_active(True)

                if opt == "--krb5kdc":
                    self.frame_xml.get_widget("kerberos_kdc").set_text(value)
                    self.use_kerberos_check.set_active(True)

                if opt == "--krb5adminserver":
                    self.frame_xml.get_widget("kerberos_master").set_text(value)
                    self.use_kerberos_check.set_active(True)

                if opt == "--enablehesiod":
                    self.use_hesiod_check.set_active(True)

                if opt == "--hesiodlhs":
                    self.frame_xml.get_widget("hesiod_lhs").set_text(value)
                    self.use_hesiod_check.set_active(True)

                if opt == "--hesiodrhs":
                    self.frame_xml.get_widget("hesiod_rhs").set_text(value)
                    self.use_hesiod_check.set_active(True)

                if opt == "--enablesmbauth":
                    self.use_samba_check.set_active(True)

                if opt == "--smbservers":
                    self.frame_xml.get_widget("samba_servers").set_text(value)
                    self.use_samba_check.set_active(True)

                if opt == "--smbworkgroup":
                    self.frame_xml.get_widget("same_workgroup").set_text(value)
                    self.use_samba_check.set_active(True)

                if opt == "--enablecache":
                    self.use_nscd_check.set_active(True)

    def store_options(self):
        self.store_nis_data()
        self.store_ldap_data()
        self.store_kerberos_data()
        self.store_hesiod_data()
        self.store_samba_data()
        self.store_nscd_data()
        self.cfg.set_authconfig()

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "authentication")

    def button_back_clicked(self, button):
        self.gui.back()

    def button_forward_clicked(self, button):
        self.store_options()
        self.gui.next()

    def store_nis_data(self):
        if not self.frame_xml.get_widget("use_nis").get_active():
            self.cfg.nis_auth = ""
        else:
            if self.frame_xml.get_widget("nis_broadcast").get_active() and self.frame_xml.get_widget("nis_broadcast").get_sensitive():
                if self.nisdomain == "":
                    self.cfg.nis_auth = ""
                else:
                    self.cfg.nis_auth = " --enablenis --nisdomain=" + self.frame_xml.get_widget("nis_domain").get_text()
            else:
                if self.frame_xml.get_widget("nis_domain").get_text() == "" or self.frame_xml.get_widget("nis_server").get_text() == "":
                    self.cfg.set_nis_auth = ""
                else:
                    self.cfg.set_nis_auth = " --enablenis --nisdomain=" + self.frame_xml.get_widget("nis_domain").get_text() + " --nisserver=" + self.frame_xml.get_widget("nis_server").get_text()

    def store_ldap_data(self):
        if not self.frame_xml.get_widget("use_ldap").get_active():
            self.cfg.ldap_auth = ""
        elif self.frame_xml.get_widget("ldap_server").get_text() == "" or self.frame_xml.get_widget("ldap_dn").get_text() == "":
            self.cfg.ldap_auth = ""
        else:
            return " --enableldap --enableldapauth --ldapserver=" + self.frame_xml.get_widget("ldap_server").get_text() + " --ldapbasedn=" + self.frame_xml.get_widget("ldap_dn").get_text()

    def store_kerberos_data(self):
        if not self.use_kerberos_check.get_active():
            self.cfg.kerberos_auth = ""
        elif self.frame_xml.get_widget("kerberos_realm").get_text() == "" or self.frame_xml.get_widget("kerberos_kdc").get_text() == "" or self.frame_xml.get_widget("kerberos_master").get_text() == "":
            self.cfg.kerberos_auth = ""
        else:
            self.cfg.kerberos_auth = " --enablekrb5 --krb5realm=" + self.frame_xml.get_widget("kerberos_realm").get_text() + " --krb5kdc=" + self.frame_xml.get_widget("kerberos_kdc").get_text() + " --krb5adminserver=" + self.frame_xml.get_widget("kerberos_master").get_text()

    def store_hesiod_data(self):
        if not self.use_hesiod_check.get_active():
            self.cfg.hesiod_auth = ""
        elif self.frame_xml.get_widget("hesiod_lhs").get_text() == "" or self.frame_xml.get_widget("hesiod_rhs").get_text() == "":
            self.cfg.hesiod_auth = ""
        else:
            self.cfg.hesiod_auth = " --hesiodlhs=" + self.frame_xml.get_widget("hesiod_lhs").get_text() + " --hesiodrhs=" + self.frame_xml.get_widget("hesiod_rhs").get_text()

    def store_samba_data(self):
        if not self.use_samba_check.get_active():
            self.cfg.samba_auth = ""
        elif self.frame_xml.get_widget("samba_server").get_text() == "" or self.frame_xml.get_widget("samba_workgroup").get_text() == "":
            self.cfg.samba_auth = ""
        else:
            self.cfg.samba_auth = " --enablesmbauth --smbservers=" + self.frame_xml.get_widget("samba_server").get_text() + " --smbworkgroup=" + self.frame_xml.get_widget("samba_workgroup").get_text()

    def store_nscd_data(self):
        pass

