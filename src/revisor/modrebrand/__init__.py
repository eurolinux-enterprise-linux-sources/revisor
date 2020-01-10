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
import revisor.misc
import shutil
import sys
import subprocess
import yum.Errors

# Translation
from revisor.translate import _, N_

class RevisorRebrand:
    def __init__(self):
        """This module allows rebranding"""
        pass

    def set_defaults(self, defaults):
        defaults.rebrand_packages = "system-release system-release-notes system-logos"

    def pre_resolve_dependencies(self):
        """Ensure that packages related to rebranding are actually being replaced."""
        if not self.cfg.rebrand:
            self.log.debug(_("Not rebranding pre_resolve_dependencies"), level=9)
            return

        # Find what provides the capabilities listed in self.cfg.rebrand_packages
        # Trim their names to brand names
        # Remove all packages <brand>-*
        # Add the brand from self.cfg.rebrand.lower().replace(' ','').strip()
        # Add the brand from generic if that fails

        for capability in self.cfg.rebrand_packages.split():
            pkgs = self.cfg.yumobj.whatProvides(capability, None, None).returnPackages()
            for po in pkgs:
                try:
                    if po.name.startswith(self.cfg.rebrand):
                        self.log.debug(_("Adding %s-%s-%s.%s") % (po.name, po.version, po.release, po.arch), level=9)
                        self.cfg.yumobj.addInstall(po)
                    else:
                        self.log.debug(_("Removing %s-%s-%s.%s") % (po.name, po.version, po.release, po.arch), level=9)
                        self.cfg.yumobj.tsInfo.remove(po)
                except:
                    pass

    def post_resolve_dependencies(self):
        """Ensure that no branded packages have been pulled in by dependency resolving"""
        pass

    def add_options(self, parser):
        """Adds a Rebrand Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        rebrand_group = parser.add_option_group("Rebrand Options")
        rebrand_group.add_option( "--rebrand-name",
                                dest    = "rebrand",
                                action  = "store",
                                default = "",
                                help    = _("Rebrand name. Revisor will select <name>-logos, <name>-release and <name>-release-notes packages, if available."),
                                metavar = "<name>")

    def check_options(self, cfg, cli_options):
        """This function checks the option rebrand"""
        self.cfg = cfg
        self.log = cfg.log
        if not cli_options.rebrand == "":
            self.log.debug(_("Setting rebrand to %s") % cli_options.rebrand, level=9)
            # Check if there's a space in the brand name
            self.cfg.rebrand = cli_options.rebrand
            # FIXME: Maybe set iso_label, iso_basename and product_name from this string right now as well
            # Consider these values have been deliberitly set to different values
        elif not self.cfg.rebrand:
            self.cfg.rebrand = False
