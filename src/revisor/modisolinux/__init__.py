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

class RevisorIsolinux:
    def __init__(self):
        """Let's you supply a custom isolinux.cfg"""
        pass

    def set_defaults(self, defaults):
        pass

    def add_options(self, parser):
        """Adds a Rebrand Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        isolinux_group = parser.add_option_group("Isolinux Options")
        isolinux_group.add_option( "--isolinux-cfg",
                                dest    = "isolinux_cfg",
                                action  = "store",
                                default = "",
                                help    = _("Custom isolinux.cfg to replace the standard isolinux.cfg with."),
                                metavar = "[file]")

    def check_options(self, cfg, cli_options):
        """This function checks the option rebrand"""
        self.cfg = cfg
        self.log = cfg.log
        if not cli_options.isolinux_cfg == self.cfg.defaults.isolinux_cfg:
            if self.cfg.kickstart_default:
                self.log.warning(_("Both --kickstart-default and --isolinux-cfg have been specified, while they are mutually exclusive. --isolinux-cfg is going to be used."))
                self.cfg.kickstart_default = False

            # FIXME: Test if the file is readable
            self.cfg.isolinux_cfg = cli_options.isolinux_cfg
        elif not cli_options.isolinux_cfg == self.cfg.isolinux_cfg:
            if self.cfg.kickstart_default:
                self.log.warning(_("Both --kickstart-default and --isolinux-cfg have been specified, while they are mutually exclusive. --isolinux-cfg is going to be used."))
                self.cfg.kickstart_default = False
        else:
            self.cfg.isolinux_cfg = False

    def check_setting_isolinux_cfg(self, val):
        if os.access(val, os.R_OK):
            return True
        else:
            self.log.error(_("File %s is not readable") % (val))
            return False

    def post_exec_buildinstall(self):
        if self.cfg.isolinux_cfg == False:
            self.log.debug(_("How come isolinux_cfg is set to False?"),level=9)

        if self.cfg.isolinux_cfg == "":
            self.log.debug(_("How come isolinux_cfg is an empty string?"),level=9)

        if not self.cfg.isolinux_cfg == False and not self.cfg.isolinux_cfg == "":
            self.log.debug(_("Going to replace isolinux/isolinux.cfg with %s") % (self.cfg.isolinux_cfg), level=7)
            try:
                os.unlink(os.path.join(self.cfg.working_directory, "revisor-install", self.cfg.version, self.cfg.model, self.cfg.architecture, "os", "isolinux", "isolinux.cfg"))
                self.log.debug(_("Deleted the old isolinux.cfg"), level=9)
                try:
                    shutil.copy(self.cfg.isolinux_cfg, os.path.join(self.cfg.working_directory, "revisor-install", self.cfg.version, self.cfg.model, self.cfg.architecture, "os", "isolinux", "isolinux.cfg"))
                    self.log.debug(_("Inserted the new isolinux.cfg"), level=9)
                except:
                    self.log.warning(_("Could not copy in the new isolinux.cfg"))
            except:
                self.log.warning(_("Could not unlink the old isolinux.cfg?"))
        else:
            self.log.debug(_("Not replacing isolinux.cfg"),level=9)
