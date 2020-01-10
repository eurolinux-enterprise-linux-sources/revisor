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

from revisor.translate import _, N_

class RevisorCLI:
    """The Revisor CLI Interface"""
    def __init__(self, base):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log

    def run(self):
        """Run Forest, RUN!"""
        self.cfg.load_kickstart(self.cfg.kickstart_file)
        # Let's check for the existance of the directories we are going to work with:
        # Since there may be mounts in there, if it fails we *need* to cancel
        if not self.cfg.check_working_directory():
            sys.exit(1)

        # Let's check for the existance of the directories in which our products go:
        self.cfg.check_destination_directory()

        self.base.setup_yum()

        self.base.lift_off()

