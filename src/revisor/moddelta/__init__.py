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
import re
import revisor.progress

# Translation
from revisor.translate import _, N_

class RevisorDelta:
    """ Revisor class to interact with delta generation calls. """

    def __init__(self):
        """ Get things setup """

        # Check if /usr/bin/makedeltarpm is available
        if not os.access("/usr/bin/makedeltarpm", os.R_OK):
            raise SystemError, _("Package deltarpm not installed")

        pass

    def buildiso(self, old, new, destination_directory, callback=None):
        """ Build a deltaiso """
        deltaimagename = "%s.delta" % (new)
        command = ["/usr/bin/makedeltaiso", old, new, deltaimagename]
        self.base.run_command(command, callback=callback)
        sha1file = open(os.path.join(destination_directory,"iso","SHA1SUM"), 'a')
        self.base.run_command(['/usr/bin/sha1sum', deltaimagename], rundir=os.path.join(destination_directory,"iso"), output=sha1file)
        sha1file.close()

    def build_iso_deltas(self):
        if os.path.isdir(self.cfg.delta_old_image):
            for root, dirs, files in os.walk(self.cfg.delta_old_image):
                files.sort()
                for file in files:
                    pbar = self.base.progress_bar("Generating Delta ISO Image %s" % file)
                    deltacallback = revisor.progress.DeltaCallback(pbar, self.cfg.number_of_packages)
                    self.buildiso(os.path.join(root,file), os.path.join(self.cfg.destination_directory,"iso",file), self.cfg.destination_directory, callback=deltacallback)
        else:
            pbar = self.base.progress_bar("Generating Delta ISO Image %s" % self.cfg.delta_old_image)
            deltacallback = revisor.progress.DeltaCallback(pbar, self.cfg.number_of_packages)
            self.buildiso(self.cfg.delta_old_image, os.path.join(self.cfg.destination_directory,"iso",os.path.basename(self.cfg.delta_old_image)), self.cfg.destination_directory, callback=deltacallback)

    def add_options(self, parser):
        """Adds a Delta Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        delta_group = parser.add_option_group("Delta Options")
        delta_group.add_option( "--delta",
                                dest    = "delta_old_image",
                                action  = "store",
                                default = "",
                                help    = _("Generate a delta ISO image. Currently only valid for a single disc or directory holding Installation Media ISOs named exactly the same as the product."),
                                metavar = "[old-iso-image]")

    def set_defaults(self, defaults):
        """This function isn't here"""
        pass
    
    def check_options(self, cfg, cli_options):
        pass