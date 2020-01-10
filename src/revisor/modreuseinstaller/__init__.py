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

import os
import fnmatch
import re
import shutil
import sys
import subprocess
import yum.Errors

# Translation
from revisor.translate import _, N_

class RevisorReuseinstaller:
    def __init__(self):
        """Let's you reuse the installer images from a previous spin"""
        pass

    def set_defaults(self, defaults):
        pass

    def add_options(self, parser):
        """Adds a ReuseInstaller Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        reuseinstaller_group = parser.add_option_group("Re-Use Installer Images Options")
        reuseinstaller_group.add_option( "--reuse",
                                dest    = "reuse",
                                action  = "store",
                                default = "",
                                help    = _("The URI to a tree we're supposed to reuse the installer images from."),
                                metavar = "<uri>")

    def check_options(self, cfg, cli_options):
        """This function checks the option rebrand"""
        self.cfg = cfg
        self.log = cfg.log
        if cfg.reuse:
            self.cfg.runtime.packages_list['installation']['require']['all']['all'] = []

        if not cli_options.reuse == "":
            self.cfg.reuse = cli_options.reuse

            if self.cfg.architecture in [ "ppc", "ppc64" ]:
                files = [ "images/boot.iso", "ppc/ppc32/vmlinuz", "ppc/ppc64/vmlinuz" ]
            else:
                files = [ "isolinux/isolinux.cfg", "isolinux/isolinux.bin", "isolinux/vmlinuz", "isolinux/initrd.img", "images/boot.iso" ]
            # FIXME: This only does local trees right now
            for file in files:
                if not os.access("%s/%s" % (cli_options.reuse,file), os.R_OK):
                    self.cfg.reuse = False
                    self.log.error(_("Could not access %s/%s, required for reusing a previous tree. Cancelling the reuse of installer images") % (cli_options.reuse,file), recoverable=True)

    def pre_exec_buildinstall(self):
        # FIXME: This only does local trees right now (no http:// etc.)
        # FIXME: Use .treeinfo for information on what to copy

        if not self.cfg.reuse:
            print self.cfg.reuse
            return

        if self.cfg.architecture in [ "ppc", "ppc64" ]:
            dirs = [ "etc", "images", "ppc" ]
        else:
            dirs = [ "EFI", "isolinux", "images" ]

        target = os.path.join(self.cfg.working_directory, "revisor-install", self.cfg.version, self.cfg.model, self.cfg.architecture, "os")

        for dir in dirs:
            if os.access(os.path.join(self.cfg.reuse, dir), os.R_OK):
                self.log.debug(_("Copying %s/%s to %s/%s") % (self.cfg.reuse, dir, target, dir), level=9)
                shutil.copytree("%s/%s" % (self.cfg.reuse, dir), "%s/%s" % (target, dir))

        self.log.debug(_("Copying %s/.discinfo to %s/.discinfo") % (self.cfg.reuse, target), level=9)
        shutil.copy("%s/.discinfo" % (self.cfg.reuse), target)
        if os.access("%s/.treeinfo" % (self.cfg.reuse), os.R_OK):
            self.log.debug(_("Copying %s/.treeinfo to %s/.treeinfo") % (self.cfg.reuse, target), level=9)
            shutil.copy("%s/.treeinfo" % (self.cfg.reuse), target)

