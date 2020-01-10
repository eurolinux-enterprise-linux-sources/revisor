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

class SelectMedia:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg

        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(os.path.join(PIXMAPS_FILES, "select_media.png"))

        self.gui.add_buttons()

        self.restore_options()

        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        self.gui.back()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            self.gui.next()

    def check_options(self):
        mic = self.frame_xml.get_widget("media_installation_cd").get_active()
        mid = self.frame_xml.get_widget("media_installation_dvd").get_active()
        mlt = self.frame_xml.get_widget("media_live_thumb").get_active()
        mlo = self.frame_xml.get_widget("media_live_optical").get_active()

        if not mic and not mid and not mlt and not mlo:
            self.log.error(_("No media selected. Please select at least one media type to compose."))
            return False
        else:
            return True

    def store_options(self):
        self.cfg.media_installation_cd = self.frame_xml.get_widget("media_installation_cd").get_active()
        self.cfg.media_installation_dvd = self.frame_xml.get_widget("media_installation_dvd").get_active()
        self.cfg.media_live_thumb = self.frame_xml.get_widget("media_live_thumb").get_active()
        self.cfg.media_live_optical = self.frame_xml.get_widget("media_live_optical").get_active()

        if self.cfg.media_installation_cd or self.cfg.media_installation_dvd:
            self.cfg.media_installation = True
        else:
            self.cfg.media_installation = False

        if self.cfg.media_live_thumb or self.cfg.media_live_optical:
            self.cfg.media_live = True
        else:
            self.cfg.media_live = False

    def restore_options(self):
        self.frame_xml.get_widget("media_installation_cd").set_active(self.cfg.media_installation_cd)
        self.frame_xml.get_widget("media_installation_dvd").set_active(self.cfg.media_installation_dvd)
        self.frame_xml.get_widget("media_live_thumb").set_active(self.cfg.media_live_thumb)
        self.frame_xml.get_widget("media_live_optical").set_active(self.cfg.media_live_optical)

class SelectMediaAdvanced:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(PIXMAPS_FILES + "select_media.png")

        gui.add_buttons()

        self.restore_options()

        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        self.gui.outer_frame.hide()
        self.gui.outer_frame.destroy()
        self.gui.displayWelcomeScreen()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            if self.cfg.media_installation:
                self.gui.displaySelectMediaInstallation()
            elif self.cfg.media_live:
                self.gui.displaySelectMediaLive()
            elif self.cfg.media_virtualization:
                self.gui.displaySelectMediaVirtualization()
            elif self.cfg.media_utility:
                self.gui.displaySelectMediaUtility()

    def restore_options(self):
        self.frame_xml.get_widget("media_installation").set_active(self.cfg.media_installation)
        self.frame_xml.get_widget("media_live").set_active(self.cfg.media_live)
        self.frame_xml.get_widget("media_virtualization").set_active(self.cfg.media_virtualization)
        self.frame_xml.get_widget("media_utility").set_active(self.cfg.media_utility)
        if self.cfg.plugins.modrebrand:
            self.frame_xml.get_widget("rebrand").set_active(self.cfg.rebrand)
        else:
            self.frame_xml.get_widget("rebrand").set_active(False)
            self.frame_xml.get_widget("rebrand").set_sensitive(False)

        # Disable the options that have not yet been implemented in Revisor
        # self.frame_xml.get_widget("media_virtualization").set_sensitive(False)
        # self.frame_xml.get_widget("media_virtualization").set_active(False)

    def store_options(self):
        self.cfg.media_installation = self.frame_xml.get_widget("media_installation").get_active()
        self.cfg.media_live = self.frame_xml.get_widget("media_live").get_active()
        self.cfg.media_virtualization = self.frame_xml.get_widget("media_virtualization").get_active()
        self.cfg.media_utility = self.frame_xml.get_widget("media_utility").get_active()
        if self.cfg.plugins.modrebrand:
            self.cfg.rebrand = self.frame_xml.get_widget("rebrand").get_active()

    def check_options(self):
        mi = self.frame_xml.get_widget("media_installation").get_active()
        ml = self.frame_xml.get_widget("media_live").get_active()
        mv = self.frame_xml.get_widget("media_virtualization").get_active()
        mu = self.frame_xml.get_widget("media_utility").get_active()

        # Check if anything is selected
        if not mi and not ml and not mv and not mu:
            self.log.error(_("No media types selected, select at least one media type."))
            return False
        else:
            return True

class SelectMediaInstallation:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(PIXMAPS_FILES + "select_media.png")

        gui.add_buttons()

        self.restore_options()

        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        self.gui.displaySelectMediaAdvanced()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            if self.cfg.media_live:
                self.gui.displaySelectMediaLive()
            elif self.cfg.media_virtualization:
                self.gui.displaySelectMediaVirtualization()
            elif self.cfg.media_utility:
                self.gui.displaySelectMediaUtility()
            else:
                self.gui.displayRevisorConfiguration()

    def restore_options(self):
        self.frame_xml.get_widget("media_installation_cd").set_active(self.cfg.media_installation_cd)
        self.frame_xml.get_widget("media_installation_dvd").set_active(self.cfg.media_installation_dvd)
        self.frame_xml.get_widget("media_installation_tree").set_active(self.cfg.media_installation_tree)
        self.frame_xml.get_widget("media_installation_unified").set_active(self.cfg.media_installation_unified)
        if self.cfg.plugins.modcobbler:
            self.frame_xml.get_widget("media_installation_pxe").set_active(self.cfg.media_installation_pxe)
        else:
            self.frame_xml.get_widget("media_installation_pxe").set_active(False)
            self.frame_xml.get_widget("media_installation_pxe").set_sensitive(False)

    def store_options(self):
        self.cfg.media_installation_cd = self.frame_xml.get_widget("media_installation_cd").get_active()
        self.cfg.media_installation_dvd = self.frame_xml.get_widget("media_installation_dvd").get_active()
        self.cfg.media_installation_tree = self.frame_xml.get_widget("media_installation_tree").get_active()
        self.cfg.media_installation_unified = self.frame_xml.get_widget("media_installation_unified").get_active()
        self.cfg.media_installation_pxe = self.frame_xml.get_widget("media_installation_pxe").get_active()

    def check_options(self):
        mic = self.frame_xml.get_widget("media_installation_cd").get_active()
        mid = self.frame_xml.get_widget("media_installation_dvd").get_active()
        mit = self.frame_xml.get_widget("media_installation_tree").get_active()
        miu = self.frame_xml.get_widget("media_installation_unified").get_active()
        mip = self.frame_xml.get_widget("media_installation_pxe").get_active()

        # Check if anything is selected
        if not mic and not mid and not mit and not miu and not mip:
            self.log.error(_("No installation media type selected, select at least one type of installation media."))
            return False
        else:
            return True

class SelectMediaLive:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(PIXMAPS_FILES + "select_media.png")

        gui.add_buttons()
        self.restore_options()
        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        if self.cfg.media_installation:
            self.gui.displaySelectMediaInstallation()
        else:
            self.gui.displaySelectMediaAdvanced()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            if self.cfg.media_virtualization:
                self.gui.displaySelectMediaVirtualization()
            elif self.cfg.media_utility:
                self.gui.displaySelectMediaUtility()
            else:
                self.gui.displayRevisorConfiguration()

    def restore_options(self):
        self.frame_xml.get_widget("media_live_optical").set_active(self.cfg.media_live_optical)
        self.frame_xml.get_widget("media_live_thumb").set_active(self.cfg.media_live_thumb)
        self.frame_xml.get_widget("media_live_hd").set_active(self.cfg.media_live_hd)

    def store_options(self):
        self.cfg.media_live_optical = self.frame_xml.get_widget("media_live_optical").get_active()
        self.cfg.media_live_thumb = self.frame_xml.get_widget("media_live_thumb").get_active()
        self.cfg.media_live_hd = self.frame_xml.get_widget("media_live_hd").get_active()

    def check_options(self):
        mlo = self.frame_xml.get_widget("media_live_optical").get_active()
        mlt = self.frame_xml.get_widget("media_live_thumb").get_active()
        mlh = self.frame_xml.get_widget("media_live_hd").get_active()

        # Check if anything is selected
        if not mlo and not mlt and not mlh:
            self.log.error(_("No live media type selected, select at least one type of live media."))
            return False
        else:
            return True

class SelectMediaVirtualization:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(PIXMAPS_FILES + "select_media.png")

        gui.add_buttons()
        self.restore_options()
        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        if self.cfg.media_live:
            self.gui.displaySelectMediaLive()
        elif self.cfg.media_installation:
            self.gui.displaySelectMediaInstallation()
        else:
            self.gui.displaySelectMediaAdvanced()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            if self.cfg.media_utility:
                self.gui.displaySelectMediaUtility()
            else:
                self.gui.displayRevisorConfiguration()

    def restore_options(self):
        self.frame_xml.get_widget("media_virtual_vmware_appliance").set_active(self.cfg.media_virtual_vmware_appliance)
        self.frame_xml.get_widget("media_virtual_vmware_guest").set_active(self.cfg.media_virtual_vmware_guest)
        self.frame_xml.get_widget("media_virtual_xen").set_active(self.cfg.media_virtual_xen)
        self.frame_xml.get_widget("media_virtual_kvm").set_active(self.cfg.media_virtual_kvm)

    def store_options(self):
        self.cfg.media_virtual_vmware_appliance = self.frame_xml.get_widget("media_virtual_vmware_appliance").get_active()
        self.cfg.media_virtual_vmware_guest = self.frame_xml.get_widget("media_virtual_vmware_guest").get_active()
        self.cfg.media_virtual_xen = self.frame_xml.get_widget("media_virtual_xen").get_active()
        self.cfg.media_virtual_kvm = self.frame_xml.get_widget("media_virtual_kvm").get_active()

    def check_options(self):
        mvva = self.frame_xml.get_widget("media_virtual_vmware_appliance").get_active()
        mvvg = self.frame_xml.get_widget("media_virtual_vmware_guest").get_active()
        mvx = self.frame_xml.get_widget("media_virtual_xen").get_active()
        mvk = self.frame_xml.get_widget("media_virtual_kvm").get_active()

        # Check if anything is selected
        if not mvva and not mvvg and not mvx and not mvk:
            self.log.error(_("No virtualization media type selected, select at least one type of virtualization media."))
            return False
        else:
            return True

class SelectMediaUtility:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.splash = self.frame_xml.get_widget("select_media_splash")
        self.splash.set_from_file(PIXMAPS_FILES + "select_media.png")

        gui.add_buttons()

        self.restore_options()

        self.connect_button_signals()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_back_clicked(self, button):
        self.store_options()
        if self.cfg.media_virtualization:
            self.gui.displaySelectMediaVirtualization()
        elif self.cfg.media_live:
            self.gui.displaySelectMediaLive()
        elif self.cfg.media_installation:
            self.gui.displaySelectMediaInstallation()
        else:
            self.gui.displaySelectMediaAdvanced()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            self.gui.displayRevisorConfiguration()

    def restore_options(self):
        self.frame_xml.get_widget("media_utility_rescue").set_active(self.cfg.media_utility_rescue)

    def store_options(self):
        self.cfg.media_utility_rescue = self.frame_xml.get_widget("media_utility_rescue").get_active()

    def check_options(self):
        mur = self.frame_xml.get_widget("media_utility_rescue").get_active()

        # Check if anything is selected
        if not mur:
            self.log.error(_("No utility media type selected, select at least one type of utility media."))
            return False
        else:
            return True

class SelectMediaRebrand:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        self.restore_options()

        self.connect_button_signals()

    def button_back_clicked(self, button):
        self.store_options()
        if self.cfg.kickstart_manifest:
            # Using kickstart file
            if not self.cfg.kickstart_manifest_customize and not self.cfg.kickstart_options_customize:
                # No customize, go back to kickstart config
                self.gui.displayLoadKickstart()
            else:
                # Customizing package selection, go back to package selection
                self.gui.displayPackageSelection()
        else:
            # Not using kickstart, go back to package selection
            self.gui.displayPackageSelection()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()
            if self.cfg.media_live_optical or self.cfg.media_live_thumb:
                if self.cfg.kickstart_options_customize:
                    self.gui.displayLMBasic()
                else:
                    self.log.debug(_("Doing Live Media but not customizing kickstart options"))
                    self.gui.displayReadyScreen()
            else:
                self.gui.displayReadyScreen()

    def restore_options(self):
        self.frame_xml.get_widget("product_name").set_text(self.cfg.product_name)
        self.frame_xml.get_widget("product_path").set_text(self.cfg.product_path)
        self.frame_xml.get_widget("iso_basename").set_text(self.cfg.iso_basename)
        self.frame_xml.get_widget("iso_label").set_text(self.cfg.iso_label)
        self.frame_xml.get_widget("version").set_text(self.cfg.version)
        self.frame_xml.get_widget("comps").set_text(self.cfg.comps)
        self.frame_xml.get_widget("rebrand_packages").set_text(self.cfg.rebrand_packages)
        self.frame_xml.get_widget("rebrand_directory").set_text(self.cfg.rebrand_directory)
        self.frame_xml.get_widget("release_pkgs").set_text(self.cfg.release_pkgs)
        self.frame_xml.get_widget("release_files").set_text(self.cfg.release_files)

    def store_options(self):
        self.cfg.product_name = self.frame_xml.get_widget("product_name").get_text()
        self.cfg.product_path = self.frame_xml.get_widget("product_path").get_text()
        self.cfg.iso_basename = self.frame_xml.get_widget("iso_basename").get_text()
        self.cfg.iso_label = self.frame_xml.get_widget("iso_label").get_text()
        self.cfg.version = self.frame_xml.get_widget("version").get_text()
        self.cfg.comps = self.frame_xml.get_widget("comps").get_text()
        self.cfg.rebrand_packages = self.frame_xml.get_widget("rebrand_packages").get_text()
        self.cfg.rebrand_directory = self.frame_xml.get_widget("rebrand_directory").get_text()
        self.cfg.release_pkgs = self.frame_xml.get_widget("release_pkgs").get_text()
        self.cfg.release_files = self.frame_xml.get_widget("release_files").get_text()

    def check_options(self):
        if self.frame_xml.get_widget("product_name").get_text() == "":
            self.log.error(_("No Product Name specified"))
            return False
        if self.frame_xml.get_widget("product_path").get_text() == "":
            self.log.error(_("No Product Path specified"))
            return False
        if self.frame_xml.get_widget("iso_basename").get_text() == "":
            self.log.error(_("No base name for the ISO(s) specified"))
            return False
        if self.frame_xml.get_widget("iso_label").get_text() == "":
            self.log.error(_("No label for the ISO(s) specified"))
            return False
        if self.frame_xml.get_widget("version").get_text() == "":
            self.log.error(_("No version number specified"))
            return False
        if self.frame_xml.get_widget("comps").get_text() == "":
            self.log.error(_("No comps no glory"))
            return False
        if not os.access(self.frame_xml.get_widget("comps").get_text(), os.R_OK):
            self.log.error(_("Unable to find comps file. No comps no glory"))
            return False

        return True

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)
