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

class RevisorMock:
    def __init__(self):
        """Let's you supply a custom isolinux.cfg"""
        pass

    def set_defaults(self, defaults):
        pass

    def add_options(self, parser):
        """Adds Mock Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        mock_options = parser.add_option_group(_("Mock Options"))

        mock_options.add_option("--mock-cfg",
                                dest    = "mock_cfg",
                                action  = "store",
                                default = "",
                                help    = _("Mock configuration name to use."),
                                metavar = "[mock-config]")

    def check_options(self, cfg, cli_options):
        """This function checks the option rebrand"""
        self.cfg = cfg
        self.log = cfg.log

    def pre_exec_buildinstall(self):
        from mock.backend import Root

        # mock -v -r fedora-10-i386 clean
        # mock -v -r fedora-10-i386 init
        # mock -v -r fedora-10-i386 install
        pass
