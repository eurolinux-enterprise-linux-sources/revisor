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

class LMUserCustomize:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.connect_button_signals()

        # Get some widgets
        self.user_name = self.frame_xml.get_widget("user_name")
        self.user_comment = self.frame_xml.get_widget("user_comment")
        self.user_password = self.frame_xml.get_widget("user_password")
        self.confirm_user_password = self.frame_xml.get_widget("confirm_user_password")
        self.user_autologin = self.frame_xml.get_widget("user_autologin")
        self.user_wheel = self.frame_xml.get_widget("user_wheel")
        self.wheel_sudo_nopasswd = self.frame_xml.get_widget("wheel_sudo_nopasswd")
        self.dump_current_profile = self.frame_xml.get_widget("dump_current_profile")

        self.user_name_set = False
        self.user_password_set = False
        self.confirm_user_password_set = False
        self.check_passwords_ok = False

        self.restore_options()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_user_name_changed": self.user_name_changed,
                 "on_user_password_changed": self.user_password_changed,
                 "on_user_password_delete_text": self.user_password_delete_text,
                 "on_confirm_user_password_changed": self.confirm_user_password_changed }
        self.gui.frame_xml.signal_autoconnect(sigs)

    def user_name_changed(self, widget):
        self.user_name_set = True
        self.set_sensitivity_checkbuttons()

    def user_password_changed(self, widget):
        if not self.user_password.get_text() == "":
            self.user_password_set = True

    def confirm_user_password_changed(self, widget):
        if self.check_passwords():
            self.confirm_user_password_set = True

    def set_sensitivity_checkbuttons(self):
        if self.user_name_set and self.check_passwords_ok:
            self.user_autologin.set_sensitive(True)
            self.user_wheel.set_sensitive(True)
            self.wheel_sudo_nopasswd.set_sensitive(True)
            self.dump_current_profile.set_sensitive(True)
        else:
            # Disable them
            self.user_autologin.set_active(False)
            self.user_wheel.set_active(False)
            self.wheel_sudo_nopasswd.set_active(False)
            self.dump_current_profile.set_active(False)
            self.user_autologin.set_sensitive(False)
            self.user_wheel.set_sensitive(False)
            self.wheel_sudo_nopasswd.set_sensitive(False)
            self.dump_current_profile.set_sensitive(False)


    def check_passwords(self, alert=False):
        if not self.user_password.get_text() == "":
            if not self.user_password.get_text() == self.confirm_user_password.get_text():
                if alert:
                    self.log.alert(_("These passwords do not match"))
                    self.check_passwords_ok = False
                    self.set_sensitivity_checkbuttons()
                    return False
                else:
                    self.check_passwords_ok = False
                    self.set_sensitivity_checkbuttons()
                    return False
            else:
                self.check_passwords_ok = True
                self.set_sensitivity_checkbuttons()
                return True
        else:
            self.check_passwords_ok = False
            self.set_sensitivity_checkbuttons()
            return False

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "user-customize")

    def button_back_clicked(self, button):
        self.gui.back()

    def button_forward_clicked(self, button):
        if self.check_options():
            self.store_options()
            self.gui.next()

    def store_options(self):
        # We have already checked the passwords.. self.check_passwords_ok

        if not self.user_name.get_text() == "":
            self.cfg.lm_user_configuration = False

            self.cfg.lm_user_name = self.user_name.get_text()
            self.cfg.lm_user_comment = self.user_comment.get_text()

            # Actually, do some settings checking such as shadow and md5...
            # salt it like we do with the root password?
            self.cfg.lm_user_password = self.user_password.get_text()
        else:
            # Obviously the user has not configured a username...
            self.cfg.lm_user_configuration = False

    def restore_options(self):
        if self.cfg.lm_user_configuration:
            self.user_name.set_text(self.cfg.lm_user_name)
            self.user_comment.set_text(self.cfg.lm_user_comment)
            # Do something similar to what we have for the root password
            self.user_password.set_visibility(True)
            self.user_password.set_text(_("Using kickstart configuration, edit entry here"))
            self.confirm_user_password.set_sensitive(False)
            self.user_password_set = True
            self.confirm_user_password_set = True
            self.check_user_passwords_ok = True
            self.user_autologin.set_sensitive(True)
            self.user_wheel.set_sensitive(True)
            self.wheel_sudo_nopasswd.set_sensitive(True)
            self.dump_current_profile.set_sensitive(True)

            self.user_autologin.set_active(self.cfg.lm_user_auto_login)
            self.user_wheel.set_active(self.cfg.lm_user_wheel)
            self.wheel_sudo_nopasswd.set_active(self.cfg.lm_wheel_sudo_no_passwd)
            self.dump_current_profile.set_active(self.cfg.lm_dump_current_profile)
        pass

    def check_options(self):
        return True

    def user_password_delete_text(self, gentry, from_char, to_char):
        if to_char > from_char:
#            self.user_password.set_text("")
            self.user_password.set_visibility(False)
            self.confirm_user_password.set_sensitive(True)
            self.check_passwords()
