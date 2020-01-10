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

import string
import os
import random
import crypt
import getopt

import system_config_keyboard.keyboard as keyboard
import system_config_keyboard.keyboard_models as keyboard_models

# Translation
from revisor.translate import _, N_

# import hardwareLists from system-config-kickstart
sys.path.append('/usr/share/system-config-kickstart')
from hardwareLists import langDict

class LMBasic:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml
        self.cleared_root_passwd = False

        gui.add_buttons()

        self.connect_button_signals()

        self.lang_combo = self.frame_xml.get_widget("lang_combo")
        self.keyboard_combo = self.frame_xml.get_widget("keyboard_combo")
        self.timezone_combo = self.frame_xml.get_widget("timezone_combo")
        self.utc_check_button = self.frame_xml.get_widget("utc_check_button")

        self.root_passwd_entry = self.frame_xml.get_widget("root_passwd_entry")
        self.root_passwd_confirm_entry = self.frame_xml.get_widget("root_passwd_confirm_entry")
        self.encrypt_root_pw_checkbutton = self.frame_xml.get_widget("encrypt_root_pw_checkbutton")
        self.lang_support_list = self.frame_xml.get_widget("lang_support_list")
        self.platform_combo = self.frame_xml.get_widget("platform_combo")

        self.platform_list =  ["x86, AMD64, or Intel EM64T", "Intel Itanium", "IBM iSeries",
                               "IBM pSeries", "IBM zSeries/s390"]
        self.platform_combo.set_popdown_strings(self.platform_list)
#        self.platform_combo.entry.connect("changed", self.platformChanged)

        self.langDict = langDict

        #populate language combo
        self.lang_list = self.langDict.keys()
        self.lang_list.sort()
#        print >> sys.stdout, str(self.lang_list)

        widget_cbox_parent = self.gui.frame_xml.get_widget("basic_config_table")

        self.lang_combo.hide()
        self.lang_combo.destroy()
        self.lang_combo = gtk.combo_box_new_text()

        for lang in self.lang_list:
            self.lang_combo.append_text(lang)

        if not self.lang_combo.get_active() >= 0:
            self.lang_combo.set_active(0)

        widget_cbox_parent.attach(self.lang_combo,1,2,0,1)
        self.lang_combo.show()

        self.keyboard_combo.hide()
        self.keyboard_combo.destroy()
        self.keyboard_combo = gtk.combo_box_new_text()

        #populate keyboard combo, add keyboards here
        self.keyboard_dict = keyboard_models.KeyboardModels().get_models()
        keys = self.keyboard_dict.keys()
        keys.sort()
        self.keyboard_list = []

        for item in keys:
            self.keyboard_combo.append_text(self.keyboard_dict[item][0])

        widget_cbox_parent.attach(self.keyboard_combo,1,2,1,2)
        self.keyboard_combo.show()

        #populate time zone combo
        if os.access("/usr/share/zoneinfo/zone.tab", os.R_OK):
            tz = open ("/usr/share/zoneinfo/zone.tab", "r")
            lines = tz.readlines()
            tz.close()

        self.timezone_list = []

        self.timezone_combo.hide()
        self.timezone_combo.destroy()
        self.timezone_combo = gtk.combo_box_new_text()

        try:
            for line in lines:
                if line[:1] == "#":
                    pass
                else:
                    tokens = string.split(line)
                    self.timezone_list.append(tokens[2])

            self.timezone_list.sort()
        except:
            self.timezone_list = []

        for timez in self.timezone_list:
            self.timezone_combo.append_text(timez)

        widget_cbox_parent.attach(self.timezone_combo,1,2,2,3)
        self.timezone_combo.show()

        self.restore_options()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_root_passwd_entry_delete_text": self.on_root_passwd_entry_delete_text,
                 "on_root_passwd_entry_changed": self.on_root_passwd_entry_changed,
                 "on_root_passwd_confirm_entry_changed": self.on_root_passwd_confirm_entry_changed }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "basic")

    def button_back_clicked(self, button):
        self.gui.back()

    def on_root_passwd_entry_changed(self, gentry):
        if not self.cleared_root_passwd and not self.root_passwd_entry.get_text() == _("Using kickstart configuration, edit entry here"):
            self.root_passwd_entry.set_text("")
            self.cleared_root_passwd = True
            return

        if not self.root_passwd_entry.get_text() == "" and not self.root_passwd_entry.get_text() == _("Using kickstart configuration, edit entry here"):
            self.root_passwd_entry.set_visibility(False)
            self.root_passwd_set = True
            self.root_passwd_confirm_entry.set_sensitive(True)

    def on_root_passwd_confirm_entry_changed(self, gentry):
        if not self.cleared_root_passwd and not self.root_passwd_entry.get_text() == _("Using kickstart configuration, edit entry here"):
            self.root_passwd_entry.set_text("")
            self.root_password_from_kickstart = False
            self.cleared_root_passwd = True

        if not self.root_passwd_entry.get_text() == "":
            self.root_passwd_set = True
            self.root_password_from_kickstart = False
            self.root_passwd_confirm_entry.set_sensitive(True)

    def on_root_passwd_confirm_entry_changed(self, widget):
        if self.check_passwords():
            self.root_password_from_kickstart = False
            self.root_passwd_confirm_set = True

    def on_root_passwd_entry_delete_text(self, gentry, from_char, to_char):
        if to_char and from_char and not self.cleared_root_passwd and to_char > from_char:
            self.root_passwd_entry.set_text("")
            self.root_password_from_kickstart = False
            self.root_passwd_entry.set_visibility(False)
            self.root_passwd_confirm_entry.set_sensitive(True)
            self.cleared_root_passwd = True

    def check_passwords(self, alert=False):
        if not self.root_passwd_entry.get_text() == "":
            if not self.root_passwd_entry.get_text() == self.root_passwd_confirm_entry.get_text():
                if alert:
                    self.log.error(_("These passwords do not match"))
                    self.check_passwords_ok = False
                    return False
                else:
                    self.check_passwords_ok = False
                    return False
            else:
                self.check_passwords_ok = True
                return True
        else:
            self.check_passwords_ok = False
            return False

    def restore_options(self):
        """Restore options from self.cfg.ksparser or fallback to defaults"""

        # Language stuff
        self.lang_combo.set_active(self.lang_list.index('English (USA)'))
        if self.cfg.use_kickstart_file:
            # Now we can restore options from the loaded kickstart file...!
            if not self.cfg.ksobj._get("lang","lang") == "":
                for lang in self.langDict.keys():
                    if self.langDict[lang] in self.cfg.ksobj._get("lang","lang"):
                        self.lang_combo.set_active(self.lang_list.index(lang))

            # Keyboard stuff
            kbd = keyboard.Keyboard()
            kbd.read()
            currentKeymap = kbd.get()

            keys = self.keyboard_dict.keys()
            keys.sort()

            key_ks = False
            key_current = False
            key_default = False
            i = 0
            for item in keys:
                if self.keyboard_dict[item][1] == self.cfg.ksobj._get("keyboard","keyboard"):
                    key_ks = i
                elif self.keyboard_dict[item][1] == currentKeymap:
                    key_current = i
                elif self.keyboard_dict[item][1] == "us":
                    key_default = i
                i += 1

            if self.cfg.use_kickstart_file:
                try:
                    self.keyboard_combo.set_active(key_ks)
                except:
                    self.keyboard_combo.set_default(key_default)
            else:
                try:
                    self.keyboard_combo.set_active(key_current)
                except:
                    self.keyboard_combo.set_active(key_default)

            # Timezone stuff
            # Set the timezone from the loaded ksdata
            # Set the timezone from the current system
            # Set the default timezone
            # Set no timezone at all
            try:
                select = self.timezone_list.index(self.cfg.ksobj._get("timezone","timezone"))
            except:
                try:
                    select = self.timezone_list.index("America/New_York")
                except:
                    select = 0

            self.timezone_combo.set_active(select)

            self.utc_check_button.set_active(self.cfg.ksobj._get("timezone","isUtc"))

            self.root_passwd_entry.set_visibility(True)
            self.root_passwd_entry.set_text(_("Using kickstart configuration, edit entry here"))
            self.root_passwd_confirm_entry.set_sensitive(False)
            self.root_password_from_kickstart = True
        else:
            self.root_password_from_kickstart = False

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            self.gui.next()

    def check_options(self):
        if not self.root_password_from_kickstart:
            if not self.check_passwords(alert=True):
                return False

            if self.root_passwd_entry.get_text() == "":
                self.log.error(_("Please select a root password."))
                return False

            if len(self.root_passwd_entry.get_text()) < 5:
                self.log.error(_("You should really select a more complex root password."))

        return True

    def store_options(self):
        self.cfg.ksobj._set("lang","lang",self.langDict[self.lang_combo.get_active_text()])

        keys = self.keyboard_dict.keys()
        keys.sort()
        for item in keys:
            if self.keyboard_dict[item][0] == self.keyboard_combo.get_active_text():
                self.cfg.ksobj._set("keyboard","keyboard",item)
                break

        self.cfg.ksobj._set("timezone","timezone",self.timezone_combo.get_active_text())
        if self.utc_check_button.get_active() == True:
            self.cfg.ksobj._set("timezone","isUtc",True)

        if not self.root_password_from_kickstart:
            pure = self.root_passwd_entry.get_text()

            if self.encrypt_root_pw_checkbutton.get_active() == True:
                salt = "$1$"
                saltLen = 8

                if not pure.startswith(salt):
                    for i in range(saltLen):
                        salt = salt + random.choice (string.letters + string.digits + './')

                    self.passwd = crypt.crypt (pure, salt)

                    temp = unicode (self.passwd, 'iso-8859-1')
                    self.cfg.ksobj._set("rootpw","isCrypted",True)
                    self.cfg.ksobj._set("rootpw","password",temp)
                else:
                    self.cfg.ksobj._set("rootpw","isCrypted",True)
                    self.cfg.ksobj._set("rootpw","password",pure)
            else:
                self.passwd = self.root_passwd_entry.get_text()
                self.cfg.ksobj._set("rootpw","isCrypted",False)
                self.cfg.ksobj._set("rootpw","password",pure)

        self.cfg.ksobj._set("platform",val=self.platform_combo.entry.get_text())

        return 0
