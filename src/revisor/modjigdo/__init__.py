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

import os, sys, re

from optparse import OptionParser

# Translation
from revisor.translate import _, N_

# What it needs to do:
# - Given a checkbox to jigdofy whatever /installation media/ we compose, this stuff gets triggered
# - Create a subdirectory jigdo/ in self.cfg.destination_directory
# - Touch the jigdo file inside that directory
# - Use the installation tree
# - Generate the templates
# - Edit the .jigdo file to somehow use the repositories we used to compose the tree/media

# Problems:
# - When composing off Fedora/, jigdofy still requires you to specify the updates/ repo, and uses some packages from these
# updates/ repository as well.
# - We can't specify an online repo to use for comparing the ISO contents with the repository data, can we?
#

class RevisorJigdo:
    def __init__(self):
        # Check if jigdo is installed.
        if not os.access("/usr/bin/jigdo", os.R_OK):
            raise SystemError, _("Package jigdo not installed")

        pass

    def set_defaults(self, defaults):
        pass

    def add_options(self, parser):
        """Adds a Jigdo Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        jigdo_group = parser.add_option_group("Jigdo Options")
        jigdo_group.add_option( "--jigdo-tree",
                                dest    = "jigdo_tree",
                                action  = "store_true",
                                default = False,
                                help    = _("Generate Jigdo files and templates using the installation tree"))

        jigdo_group.add_option( "--jigdo-repos",
                                dest    = "jigdo_repos",
                                action  = "store_true",
                                default = False,
                                help    = _("Generate Jigdo files against the Revisor YUM Cache (labels different repositories)."))

    def check_options(self, cfg, cli_options):
        """Given a list of specified command line options in the OptionParser format
        this one checks if it's all OK"""

        self.cfg = cfg

        # If the cli_options values are any different from the defaults...
        if cli_options.jigdo_tree and cli_options.jigdo_repos:
            cfg.log.error(_("You cannot use both the installation tree and the yum cache to build Jigdo templates against."), recoverable=False)

        elif cli_options.jigdo_tree:
            self.cfg.jigdo_tree = cli_options.jigdo_tree

        elif cli_options.jigdo_repos:
            self.cfg.jigdo_repos = cli_options.jigdo_repos

    def post_compose_media_installation(self):
        """This is the hook where Revisor is supposed to generate .jigdo and .iso.template files"""

        # Create a list of dicts with the yum info
        repos = []
        for repo_id in self.cfg.yumobj.repos.repos.keys():
            repo = self.cfg.yumobj.repos.repos[repo_id]
            repos.append({ 'label': "%s-%s" % (repo.id,self.cfg.architecture),
                           'path': "%s/%s" % (self.cfg.yumobj.conf.cachedir,repo.id),
                           'baseurl': repo.baseurl,
                           'mirrorlist': repo.mirrorlist })

        #for built_iso in self.cfg.built_iso_images:
            #print """
            #jigdo_obj = pyjigdo.GenerateJigdo(isofile=built_iso['location'],
                                              #jigdofile=self._jigdofile(built_iso['location']),
                                              #templatefile=self._templatefile(built_iso['location']),
                                              #info=repos)
#"""