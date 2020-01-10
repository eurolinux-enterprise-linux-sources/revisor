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

from cobbler import api
from xmlrpclib import ServerProxy
import sys, socket, os

# Translation
from revisor.translate import _, N_

class RevisorCobbler(api.BootAPI):
    """ Revisor class to interact with cobbler. """

    def newProfile(self, name, distro, kickstart):
        """ A Simple call to interact with the base cobbler API to add a profile. """
        # cobbler profile add --name=string --distro=string [--kickstart=url] [--kopts=string] [--ksmeta=string] [--virt-file-size=gigabytes]
        # [--virt-ram=megabytes]
        profile_info = {'name': name, 'distro': distro, 'kickstart': kickstart}
        profile = self.new_profile()
        profile.from_datastruct(profile_info)
        self.profiles().add(profile, with_copy=self.sync_flag)
        self.saveChanges()

    def addCompose(self, location, name, callback=None):
        """ Add the compose to cobbler. This does both newDistro() and newProfile() """
        #ostdout = sys.stdout
        #sys.stdout = callbacka
        #FIXME: Enable a callback so we can do something with the stdout from cobbler
        # for now, it is just being shown to the end user.
        self.import_tree(location, name)
        #FIXME: We need to also import the current kickstart render into the profile
        #sys.stdout = ostdout

    def listOptions(self, server=None, port=25151, display=False):
        """ A Simple call to interact with the base cobbler API to return a list of what distros and profiles we have access to. """
        # cobbler list
        retList = []
        if not server:
            for d in self.distros():
                distro = {"name": d.name}
                profiles = []
                for p in self.profiles():
                    if p.distro == d.name:
                        profiles.append(p.name)
                distro["profiles"] = profiles
                retList.append(distro)
        else:
            server_url = "http://%s:%s" % (server, port)
            cobblerserver = RevisorCobblerServer(server_url)
            try:
                cobbler_version = cobblerserver.version()
            except socket.error:
                self.log.error(_("There is a problem connecting to %s" % server_url), recoverable=False)

            for d in cobblerserver.get_distros():
                distro = {"name": d["name"]}
                profiles = []
                for p in cobblerserver.get_profiles():
                    if p["distro"] == d["name"]:
                        profiles.append(p["name"])
                distro["profiles"] = profiles
                retList.append(distro)

        if display:
            if retList:
                for distro_data in retList:
                    print _(" Distro: %s\n  Existing Profiles:" % distro_data["name"])
                    for profile in distro_data["profiles"]:
                        print _("   Profile: %s" % profile)
                    print "\n"
            else: print _("No listing found on cobbler server.")
        else: return retList

    def saveChanges(self):
        """ Do what needs to be done to save all our changes. """
        self.serialize()
        self.sync()

    def add_options(self, parser):
        """Adds a Cobbler Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""

        cobbler_group = parser.add_option_group("Cobbler Options")
        cobbler_group.add_option(   "--cobbler-add",
                                    dest    = "cobbler_add",
                                    action  = "store",
                                    default = "",
                                    help    = _("Add compose to a Cobbler server as both a Distribution and Profile."),
                                    metavar = "[name]")

        cobbler_group.add_option(   "--cobbler-add-profile",
                                    dest    = "cobbler_add_profile",
                                    action  = "store",
                                    default = "",
                                    help    = _("Add compose options as a Profile to a Cobbler server. [Requires --cobbler-use-distro]"),
                                    metavar = "[profile-name]")

        cobbler_group.add_option(   "--cobbler-use-distro",
                                    dest    = "cobbler_use_distro",
                                    action  = "store",
                                    default = "",
                                    help    = _("Use a Cobbler distro as source for package data."),
                                    metavar = "[distro-name]")

        cobbler_group.add_option(   "--cobbler-use-profile",
                                    dest    = "cobbler_use_profile",
                                    action  = "store",
                                    default = "",
                                    help    = _("Use a Cobbler profile as source for kickstart data."),
                                    metavar = "[profile-name]")

        cobbler_group.add_option(   "--cobbler-list",
                                    dest    = "cobbler_list",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("List options provided by cobbler."))

        cobbler_group.add_option(   "--cobbler-server",
                                    dest    = "cobbler_server",
                                    action  = "store",
                                    default = "127.0.0.1",
                                    help    = _("Use remote cobbler server."),
                                    metavar = "[server-address]")
        cobbler_group.add_option(   "--cobbler-port",
                                    dest    = "cobbler_port",
                                    action  = "store",
                                    default = "25151",
                                    help    = _("Remote cobbler server port."),
                                    metavar = "[server-port]")

    def set_defaults(self, defaults):
        defaults.media_installation_pxe = False
        defaults.cobbler_add_profile = ""
        defaults.cobbler_add_distro = ""
        defaults.cobbler_use_distro = ""
        defaults.cobbler_use_profile = ""
        defaults.cobbler_add = ""
        defaults.cobbler_list = False
        defaults.cobbler_server = "127.0.0.1"
        defaults.cobbler_port = "25151"

    def post_compose_media_installation(self):
        """ Actually run any needed cobbler interaction for post compose. """
        # Run an import against the current working directory
        if self.cfg.cobbler_add != "": self.addCompose(self.cfg.working_directory, self.cfg.cobbler_add)

    def check_setting_cobbler_list(self, val):
        """Check the cobbler_list setting. Valid values are:
        - a Server Name
        - an IP Address
        - localhost (default)"""

        # FIXME: modcobbler.check_setting_cobbler_list()
        return True

    def check_setting_cobbler_server(self, val):
        """Check the cobbler_server setting. Valid values are:
        - a Server Name
        - an IP address
        - localhost (default)

        Practically does the same as modcobbler.check_setting_cobbler_list(), but also
        attempts to make a connection."""

        # FIXME: modcobbler.check_setting_cobbler_server()
        return True

    def check_options(self, cfg, cli_options):
        """Checks the options in self.cfg, combined with the options in cli_options, as far as this
        module is concerned. Note that if we set runtime variables (like "media_live"), we need
        to set those in cfg."""

        self.cfg = cfg
        self.cli_options = cli_options

        if self.cfg.cobbler_add:
            self.cfg.media_installation_pxe = True

        if self.cfg.cli_mode:
            if not self.cfg.cobbler_server == "127.0.0.1":
                if not self.cfg.cobbler_use_distro and not self.cfg.cobbler_use_profile:
                    ## No use-distro and no use-profile. Default to list:
                    self.cfg.cobbler_list = True
                if not self.cfg.cobbler_use_distro and not self.cfg.cobbler_use_profile:
                    self.cfg.log.error(_("Specifying a Cobbler server is only supported for read-only actions. Currently, --cobbler-use-distro and --cobbler-use-profile."), recoverable=False)

            ## Find and use a cobbler distro as a source for package data (as a repo)
            if self.cfg.cobbler_use_distro:
                distro_found = False
                if self.cfg.cobbler_server == "127.0.0.1":
                    distros = self.distros() # FIXME: Look into using cobbler provided find()
                    for distro in distros:
                        if distro.name == self.cfg.cobbler_use_distro:
                            self.repo_override.append({"name": distro.name, "baseurl": distro.ks_meta["tree"], "gpgcheck": 0})
                            self.cfg.kickstart_repos = True
                            distro_found = True
                else:
                    server_url = "http://%s:%s" % (self.cfg.cobbler_server, self.cfg.cobbler_port)
                    self.cobblerserver = RevisorCobblerServer(server_url)
                    try:
                        self.cobbler_version = self.cobblerserver.version()
                    except socket.error:
                        self.cfg.log.error(_("There is a problem connecting to %s" % server_url), recoverable=False)
                    distros = self.cobblerserver.get_distros() # FIXME: Look into using cobbler provided find()
                    for distro in distros:
                        if distro["name"] == self.cfg.cobbler_use_distro:
                            distro_found = True

                if not distro_found:
                    self.cfg.log.error(_("The distro '%s' does not exist." % (self.cfg.cobbler_use_distro)), recoverable=False)

            ## Find and use a cobbler profile as both a source for kickstart data
            if self.cfg.cobbler_use_profile:
                kickstart_url = ""
                profile_obj = False

                if self.cfg.cobbler_server == "127.0.0.1":
                    profiles = self.profiles() # FIXME: Look into using cobbler provided find()
                    for profile in profiles:
                        if profile.name == self.cfg.cobbler_use_profile:
                            profile_obj = profile

                    if not profile_obj:
                        self.cfg.log.error(_("The profile '%s' does not exist." % (self.cfg.cobbler_use_profile)), recoverable=False)

                    kickstart = os.path.join(profile_obj.settings.webdir, 'kickstarts', profile_obj.name, 'ks.cfg')
                    if not os.access(kickstart, os.R_OK):
                        kickstart = 'http://%s/cblr/svc/op/ks/profile/%s' % (profile_obj.server, profile_obj.name)
                    else:
                        kickstart = "file://%s" % kickstart

                    self.cfg.kickstart_file = kickstart

                else:
                    server_url = "http://%s:%s" % (self.cfg.cobbler_server, self.cfg.cobbler_port)
                    self.cobblerserver = RevisorCobblerServer(server_url)
                    try:
                        self.cobbler_version = self.cobblerserver.version()
                    except socket.error:
                        print self.log.error(_("There is a problem connecting to %s" % server_url), recoverable=False)
                    profiles = self.cobblerserver.get_profiles() # FIXME: Look into using cobbler provided find()
                    for profile in profiles:
                        if profile["name"] == self.cfg.cobbler_use_profile:
                            profile_obj = profile

                    if not profile_obj:
                        self.cfg.log.error(_("The profile '%s' does not exist." % (self.cfg.cobbler_use_profile)), recoverable=False)

                    kickstart = 'http://%s/cblr/svc/op/ks/profile/%s' % (self.cfg.cobbler_server, profile_obj["name"])

                    self.cfg.kickstart_file = kickstart

        if self.cfg.media_installation_pxe:
            self.cfg.media_installation = True

class RevisorCobblerServer(ServerProxy):

    def __init__(self, url=None):
        ServerProxy.__init__(self, url, allow_none=True)

