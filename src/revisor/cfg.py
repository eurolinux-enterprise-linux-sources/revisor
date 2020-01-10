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

import datetime
import libxml2
import os
import revisor
from revisor.constants import *
from revisor.errors import *
import shutil
import subprocess
import sys
import time
import urlparse

import pykickstart

from ConfigParser import SafeConfigParser

import yum
from yum.constants import *
import yum.Errors
import logging

from revisor.translate import _, N_

import kickstart

class ConfigStore:
    """This ConfigStore holds all options available in Revisor, including Kickstart Data and Handlers,
    so that these are available to both the GUI and the CLI mode."""
    def __init__(self, base):
        # We get a RevisorBase instance
        self.log = base.log
        self.plugins = base.plugins
        self.cli_options = base.cli_options
        self.parser = base.parser

        # The point of all this is that we can compare our defaults to our cli_options
        # and runtime.

        # Look, we want defaults
        self.defaults = Defaults(self.plugins)

        # This is where we check our parser for the defaults being set there.
        self.set_defaults_from_cli_options()

        # But, they should be available in our class as well
        for option in self.defaults.__dict__.keys():
            setattr(self,option,self.defaults.__dict__[option])

        # There is also a number of runtime specific variables
        self.runtime = Runtime(self.plugins, self.defaults)

        # Which should also be available here
        for option in self.runtime.__dict__.keys():
            self.log.debug(_("Setting %s to %r") % (option, self.runtime.__dict__[option]), level=9)
            setattr(self,option,self.runtime.__dict__[option])

##
## Mode related
##
    def _set_gui_mode(self):
        self.gui_mode = True
        self.cli_mode = False

    def _set_cli_mode(self):
        self.cli_mode = True
        self.gui_mode = False

    def setup_cfg(self):
        """This sets up the configuration store. An existing self.log is mandatory"""
        # First set the options from the configuration file
        self.options_set_from_config()

        # Then override those with the command line specified options
        self.options_set_from_commandline()

        # Now that we know about any of the options, it's about time we check them!
        self.check_options()

    def set_defaults_from_cli_options(self):
        for long_opt in self.parser.__dict__['_long_opt'].keys():
            if long_opt == "--help":
                continue
            setattr(self.defaults,self.parser._long_opt[long_opt].dest,self.parser._long_opt[long_opt].default)

    def check_package_selection(self, only_clear_data=False):
        """ A function to check some key things about our selected packages. """

        self.package_Xorg = False
        self.package_windowmanager_gnome = False
        self.package_windowmanager_kde = False
        self.package_windowmanager_xfce = False

        if not only_clear_data:
            pkgs = self.yumobj.tsInfo.getMembers()
            for pk in pkgs:
                if pk.name in ('xorg-x11-server-Xorg',):
                    self.package_Xorg = True
                elif pk.name in ('kdebase',):
                    self.package_windowmanager_kde = True
                elif pk.name in ('gnome-session',):
                    self.package_windowmanager_gnome = True
                elif pk.name in ('xfce-session',):
                    self.package_windowmanager_xfce = True

    def get_comps(self):
        """Get me a comps file no matter what it takes. Return a filename."""
        if self.revisor_comps:
            return self.comps

        # Create our own comps from the repositories
        # Thanks to pungi (but we can't use that code
        # because we can't launch it for EL5)

        if not os.access("/usr/bin/xsltproc", os.R_OK):
            # No xsltproc no glory
            return self.comps

        self.comps = os.path.join(self.working_directory,"revisor-install",self.version,self.model,"comps.xml")

        doc = libxml2.newDoc("1.0")
        dtd = doc.newDtd('comps', '-//Red Hat, Inc.//DTD Comps info//EN', 'comps.dtd')
        doc.addChild(dtd)
        comps = doc.newChild(doc.ns(), 'comps', None)

        grps = []
        cats = []
        comps_list = []

        for repo in self.yumobj.repos.repos.values():
            if repo.enabled:
                try:
                    groupfile = repo.getGroups()
                except yum.Errors.RepoMDError, e:
                    self.log.debug(_("No group data found for %s") % repo.id)
                    pass
                except AttributeError, e:
                    self.log.debug(_("Why is yum throwing AttributeErrors? %s") % e)
                else:
                    repo_comps = libxml2.parseFile(groupfile)
                    repo_root = repo_comps.children # skip dtd
                    repo_root = repo_root.next # the <comps>
                    nodes = repo_root.walk_breadth_first()

                    for n in nodes:
                        if (n.type == 'element'):
                            if (n.name == 'group'):
                                n.unlinkNode()
                                grps.append(n)
                            elif (n.name == 'category'):
                                n.unlinkNode()
                                cats.append(n)
                    comps_list.append(repo_comps)

        for n in grps:
            comps.addChild(n)
        for n in cats:
            comps.addChild(n)

        doc.saveFormatFileEnc(self.comps, 'UTF-8', True)
        doc.freeDoc()

        for comps in comps_list:
            comps.freeDoc()

        del(grps)
        del(cats)

        return self.comps

    def retired_get_comps(self):
        """Get me a comps file no matter what it takes. Return a filename."""
        if self.revisor_comps:
            return self.comps

        # Create our own comps from the repositories
        # Thanks to pungi (but we can't use that code
        # because we can't launch it for EL5)

        if not os.access("/usr/bin/xsltproc", os.R_OK):
            # No xsltproc no glory
            return self.comps

        self.comps = os.path.join(self.working_directory,"revisor-install",self.version,self.revisor_model,"comps.xml")
        ourcomps = open(self.comps, "w")

        ourcomps.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE comps PUBLIC \"-//Red Hat, Inc.//DTD Comps info//EN\" \"comps.dtd\">\n<comps>\n")

        for repo in self.yumobj.repos.repos.values():
            try:
                groupfile = repo.getGroups()
            except yum.Errors.RepoMDError, e:
                self.log.debug(_("No group data found for %s") % repo.id)
                pass
            except AttributeError, e:
                self.log.debug(_("Why is yum throwing AttributeErrors? %s") % e)
            else:
                start = 1
                end = -1
                compslines = open(groupfile, 'r').readlines()
                for line in compslines:
                    if line.startswith('</comps>'):
                        end = compslines.index(line)

                for line in compslines:
                    if line.startswith('<comps>') or line.startswith('<comps xmlns="">'):
                        start = compslines.index(line) + 1

                ourcomps.writelines(compslines[start:end])

        ourcomps.write("\n</comps>\n")
        ourcomps.close()

        return self.comps

##
##
## Functions that can load and test regular configuration files
##
##

    def check_working_directory(self):
        """From the Revisor Configuration Files and other settings,
        check for the directory hierarchy"""

        self.log.debug(_("Checking working directories"))
        complain = False
        if os.access(os.path.join(self.working_directory,"pungi-revisor"), os.R_OK):
            complain = True
        if os.access(os.path.join(self.working_directory,"revisor-install"), os.R_OK):
            complain = True
        if os.access(os.path.join(self.working_directory,"revisor"), os.R_OK):
            complain = True
        if os.access(os.path.join(self.working_directory,"revisor-rundir"), os.R_OK):
            complain = True
        if os.access(os.path.join(self.working_directory,"revisor-livecd"), os.R_OK):
            complain = True

        self.plugins.exec_hook('check_working_directory')

        if complain:
            if not self.answer_yes:
                self.log.warning(_("The directories Revisor uses in %s already exist. This could possibly hold data from a previous run. Please remove or move them to a safe location, then confirm to continue. If you do not move or remove the files, Revisor will simply delete them." % self.working_directory))
            else:
                self.log.debug(_("The directories Revisor uses in %s already exist. Revisor deleted them." % self.working_directory))
            complain = False
            if os.access(os.path.join(self.working_directory,"pungi-revisor"), os.R_OK):
                shutil.rmtree(os.path.join(self.working_directory,"pungi-revisor"))
            if os.access(os.path.join(self.working_directory,"revisor-install"), os.R_OK):
                shutil.rmtree(os.path.join(self.working_directory,"revisor-install"))
            if os.access(os.path.join(self.working_directory,"revisor"), os.R_OK):
                if os.path.ismount("%s%s" % (self.working_directory,"revisor")):
                    for f in ["/sys", "/proc", "/dev/pts", "/dev", "/selinux", "/yum-cache", "/var/cache/yum", ""]:
                        if os.path.ismount("%s%s%s" % (self.working_directory,"revisor",f)):
                            self.log.debug(_("%s%s%s is a mount, trying to unmount") % (self.working_directory,"revisor",f))
                            try:
                                rc = subprocess.call(["/bin/umount", "%s%s%s" % (self.working_directory,"revisor",f)])
                            except OSError, e:
                                self.log.error(_("Unable to unmount %s%s%s with error:\n\n%s\n\nPlease resolve the issue and continue.") % (self.working_directory,"revisor",f,e))
                                return False
                        else:
                            self.log.debug(_("%s%s%s is not a mount") % (self.working_directory,"revisor",f))

                    buf = subprocess.Popen(["/sbin/losetup", "-a"], stdout=subprocess.PIPE).communicate()[0]
                    for line in buf.split("\n"):
                        # loopdev: fdinfo (filename)
                        fields = line.split()
                        if len(fields) != 3:
                            continue
                        if ( "data/os.img" in fields[2] or "data/LiveOS/ext3fs.img" ) and "revisor" in fields[2]:
                            loopdev = fields[0][:-1]
                            rc = subprocess.call(["/sbin/losetup", "-d", loopdev])
                            break

                try:
                    shutil.rmtree("%s%s" % (self.working_directory,"revisor"))
                    # Then, recreate them
                    os.makedirs("%s/%s" % (self.working_directory,"revisor/etc"))
                    # And copy in our main
                    shutil.copyfile(self.main,"%s/%s" % (self.working_directory,"revisor/etc/yum.conf"))
                except OSError, e:
                    self.log.error(_("Unable to unmount %s%s with error:\n\n%s\n\nPlease resolve the issue and continue.") % (self.working_directory,"revisor",e))
                    return False

            if os.access(os.path.join(self.working_directory,"revisor-rundir"), os.R_OK):
                shutil.rmtree(os.path.join(self.working_directory,"revisor-rundir"))

            if os.access(os.path.join(self.working_directory,"revisor-livecd"), os.R_OK):
                shutil.rmtree(os.path.join(self.working_directory,"revisor-livecd"))

        self.plugins.exec_hook('delete_working_directory')

        return True

    def check_destination_directory(self):
        """From the Revisor Configuration Files and other settings,
        check for the directory hierarchy"""

        self.log.debug(_("Checking destination directories"))

        self.destination_directory = os.path.join(self.destination_directory,self.model)

        self.log.debug(_("Set destination directory to %s") % self.destination_directory)

        if os.access(self.destination_directory, os.R_OK):
            complain = False
            for key in DESTDIRS.keys():
                if os.access(os.path.join(self.destination_directory,key), os.R_OK):
                    for item in DESTDIRS[key]:
                        if hasattr(self,item):
                            if getattr(self,item):
                                complain = True

            # Also check directories that plugins manage
            self.plugins.exec_hook('check_destination_directory')

            if complain or self.plugins.return_true_boolean_from_plugins('complain_destination_directory'):
                if not self.answer_yes:
                    self.log.warning(_("The directories Revisor uses in %s already exist. This could possibly hold data from a previous run. Please remove or move them to a safe location, then confirm to continue. If you do not move or remove the files, Revisor will simply delete them." % self.destination_directory))
                else:
                    self.log.debug(_("The directories Revisor uses in %s already exist. Revisor deleted them." % self.destination_directory))

                complain = False

                for key in DESTDIRS.keys():
                    remove = False
                    if os.access(os.path.join(self.destination_directory,key), os.R_OK):
                        for item in DESTDIRS[key]:
                            if hasattr(self,item):
                                if getattr(self,item):
                                    remove = True

                        if remove:
                            shutil.rmtree(os.path.join(self.destination_directory,key))

            # Also delete directories that plugins manage
            self.plugins.exec_hook('delete_destination_directory')

        for key in DESTDIRS.keys():
            create = False
            if not os.access(os.path.join(self.destination_directory,key), os.R_OK):
                for item in DESTDIRS[key]:
                    if hasattr(self,item):
                        if getattr(self,item):
                            create = True
            if create:
                while not os.access(os.path.join(self.destination_directory,key), os.R_OK):
                    try:
                        os.makedirs(os.path.join(self.destination_directory,key))
                    except:
                        self.log.error(_("Cannot access %s, please check the permissions so we can try again." % os.path.join(self.destination_directory,key)))

        # Also create directories that plugins manage
        self.plugins.exec_hook('create_destination_directory')

##
##
##  Yum related stuff
##
##

    def setup_yum(self):
        # You do like having your own package sack, don't you?
        self.yumobj = yum.YumBase()

        #if self.debuglevel > self.yumobj.conf.debuglevel:
            #self.log.debug(_("Bumping YUMs debuglevel (%d) to our debuglevel (%d)") % (self.yumobj.conf.debuglevel,self.debuglevel), level=2)
            #self.yumobj.conf.debuglevel=self.debuglevel
            #self.log.debug(_("YUMs debuglevel now %d") % self.yumobj.conf.debuglevel, level=9)

        if self.architecture == "i386":
            self.arch_list = yum.rpmUtils.arch.getArchList('athlon')
            self.yumobj.compatarch = 'athlon'
        elif self.architecture == "ppc":
            self.arch_list = yum.rpmUtils.arch.getArchList('ppc64')
            self.yumobj.compatarch = 'ppc64'
        elif self.architecture == 'sparc':
            self.arch_list = yum.rpmUtils.arch.getArchList('sparc64v')
            self.yumobj.compatarch = 'sparc64v'
        else:
            self.arch_list = yum.rpmUtils.arch.getArchList(self.architecture)
            self.yumobj.compatarch = self.architecture

        self.log.debug(_("Architecture list: %r") % self.arch_list)

    def reposSetup(self, callback=None, thisrepo=None):
        # We shouldn't run for all keys(), but for all repos
        tmpparser = SafeConfigParser()
        tmpparser.read(self.main)

        if not self.repo_override:
            for item in tmpparser._sections:
                # Maybe if item in self.repos.keys()... but that fuck up matching development against
                # extras-development... Right?
                try:
                    r = self.repos[item]
                    # Override source repositories
                    if item[:-6] == "source":
                        continue

                    if r:
                        self.yumobj.repos.enableRepo(item)
                    else:
                        self.yumobj.repos.disableRepo(item)
                except:
                    pass

            for repo in self.added_repos:
                repo.setAttribute('basecachedir', self.yumobj.conf.cachedir)
                self.yumobj.repos.add(repo)
                self.yumobj.repos.enableRepo(repo.id)

            for repo in self.repos_kickstart:
                # Test if the repository has a name that already exists
                if repo.name in self.yumobj.repos.repos.keys():
                    self.log.warning(_("Repository %s specified in the kickstart already exists") % repo.name)
                    repo.name = "%s-kickstart" % repo.name
                repoObj = yum.yumRepo.YumRepository(repo.name)
                repoObj.setAttribute('name', repo.name)
                if not repo.baseurl == "":
                    self.log.debug(_("Setting repo.baseurl to %s") % self._substitute_vars(repo.baseurl))
                    repoObj.setAttribute('baseurl', self._substitute_vars(repo.baseurl))
                if not repo.mirrorlist == "":
                    self.log.debug(_("Setting repo.mirrorlist to %s") % self._substitute_vars(repo.mirrorlist))
                    repoObj.setAttribute('mirrorlist', self._substitute_vars(repo.mirrorlist))
                if hasattr(repo, "includepkgs"):
                    repoObj.includepkgs = repo.includepkgs
                if hasattr(repo, "excludepkgs"):
                    repoObj.exclude = repo.excludepkgs
                self.yumobj.repos.add(repoObj)
                self.yumobj.repos.enableRepo(repo.name)

        if callback:
            self.yumobj.repos.callback = callback
            callback.num_tasks += 10

        self.yumobj.doLock(YUM_PID_FILE)

        if not self.mode_devel:
            if hasattr(self.yumobj,"cleanMetadata"):
                self.yumobj.cleanMetadata()
            else:
                self.log.debug(_("Could not clean metadata you might be working with old data"))
            if hasattr(self.yumobj,"cleanSqlite"):
                self.yumobj.cleanSqlite()
            else:
                self.log.debug(_("Could not clean metadata you might be working with old data"))

        if callback: callback.next_task()
        try:
            if hasattr(self.yumobj,"_getRepos"):
                self.yumobj._getRepos(thisrepo)
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doRepoSetup")
                self.yumobj.doRepoSetup(thisrepo)
        except yum.Errors.RepoError, e:
            raise RevisorDownloadError, e

        if callback: callback.next_task()

        try:
            if hasattr(self.yumobj,"_getGroups"):
                self.yumobj._getGroups()
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doGroupSetup")
                self.yumobj.doGroupSetup()
        except yum.Errors.GroupsError, e:
            self.log.warning(_("No groups present! Error was: %s") % e)
        except yum.Errors.RepoError, e:
            raise RevisorDownloadError, e

        if callback: callback.next_task(next = 5) # hack... next should be long

        try:
            if hasattr(self.yumobj,"_getSacks"):
                self.yumobj._getSacks(archlist=self.arch_list)
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doSackSetup")
                self.yumobj.doSackSetup(archlist=self.arch_list)
        except yum.Errors.RepoError, e:
            raise RevisorDownloadError, e

        if callback: callback.next_task(incr=3)

        if callback: self.yumobj.repos.callback = None

    def _substitute_vars(self, string):
        string = string.replace("$basearch", self.architecture)
        string = string.replace("$arch", self.architecture)
        string = string.replace("$releasever", self.version)
        return string

##
##
## Kickstart related stuff
##
##

    def test_ks(self, file):
        ksobj_test = kickstart.RevisorKickstart(self)
        ksobj_test.create_parser()

        try:
            ksobj_test.read_file(file)
            return True
        except Exception, e:
            print e
            return False

    def setup_ks(self):
        self.ksobj = kickstart.RevisorKickstart(self)
        self.ksobj.create_parser()

    def load_kickstart(self, fn, packages=True):
        """Function loads a kickstart from a file, yes it does.
        Set the 'packages' parameter to include or exclude the
        package manifest"""
        self.kickstart_file = fn
        self.ksobj.read_file(fn)

    def set_kickstart_file(self,val):
        self.kickstart_file = val

    def config_to_kickstart(self,ks):
        """This would be a function that writes the configstore
        out to a pykickstart object"""
        pass

    def set_authconfig(self):
        self.ksobj._set("authconfig","authconfig", val=self.nis_auth + self.ldap_auth + self.kerberos_auth + self.hesiod_auth + self.samba_auth + self.nscd_auth)

##
##
## Revisor Configuration related stuff
##
##

    def check_setting_main(self, val):
        if val == "/etc/yum.conf":
            self.log.error(_("You cannot choose the system's yum configuration file /etc/yum.conf for use with Revisor. Aborting."), recoverable=False)
        elif not os.access(val, os.R_OK):
            self.log.error(_("File %s does not exist (used as 'main' configuration directive in model %s)") % (val,self.model), recoverable=self.gui_mode)
            return False

        # If the file does exist, make sure it does not have $releasever, $basearch or $arch anywhere
        config = SafeConfigParser()
        config.read(val)
        complain = False
        for section in config._sections:
            for key in [ "baseurl", "mirrorlist" ]:
                if config.has_option(section,key):
                    for item in [ "$releasever", "$basearch", "$arch" ]:
                        try:
                            if config.get(section,key).index(item):
                                complain = True
                        except:
                            pass

        if complain:
            self.log.error(_("YUM Configuration file %s uses one of the following variables: %s, %s or %s. Please edit the configuration file and substitute those variables for the actual values") % (val,"$releasever", "$basearch", "$arch"), recoverable=self.gui_mode)
            return False

        return True

    def check_setting_iso_label(self, val):
        if len(val) > 32:
            self.log.warning(_("The ISO label cannot be longer then 32 characters due to Joliet limitations"))
            return False
        else:
            return True

    def check_setting_kickstart_file(self, val):
        if not self.cli_options.kickstart_file == val and not self.cli_options.kickstart_file == self.defaults.kickstart_file:
            val = self.cli_options.kickstart_file

        if not os.access(val, os.R_OK):
            self.log.error(_("Kickstart file %s cannot be read.") % val)
            return False
        else:
            self.test_ks(val)
            return True

    def check_setting_comps(self, val):
        if not os.access(val, os.R_OK):
            self.log.warning(_("The file configured as a comps file (%s) cannot be read. When composing installation media, this is FATAL.") % val)
            return False
        else:
            return True

    def check_setting_updates_img(self, val):
        if os.path.isfile(val):
            if not os.access(val, os.R_OK):
                self.log.error(_("The updates.img specified isn't readable: %s") % val, recoverable=self.gui_mode)
                return False
            else:
                return True
        else:
            self.log.debug(_("Updates.img seems to not be a file... Is it an URL?"), level=8)
            # Is it an URL?
            if not urlparse.urlparse(val).scheme == "":
                return True
            else:
                return False

    def check_setting_lm_preffered_kernel(self, val):
        if val in ["normal", "PAE", "xen", "debug"]:
            return True
        else:
            self.log.error(_("Preferred kernel should be one of: normal, PAE, xen, debug."), recoverable=False)
        return False

    def check_setting_model(self, val):
        if self.check_model(val=val):
            if self.load_model(val=val):
                return True
        return False

    def check_setting_version_from(self, val):
        try:
            ver = pykickstart.version.stringToVersion(val)
            return True
        except:
            self.log.error(_("The version you selected as a base for pykickstart compatibility and required package sets does not exist"), recoverable=self.gui_mode)
            return False

    def check_setting_architecture(self, val):
        base_arch = yum.rpmUtils.arch.getBaseArch()
        arch_list = yum.rpmUtils.arch.getArchList(base_arch)

        if val in arch_list:
            return True
        else:
            self.log.error(_("You have selected a model with architecture %s which doesn't compose on the system architecture %s.") % (val,base_arch), recoverable=self.gui_mode)
            return False

    def options_set_from_config(self):
        """Sets the default configuration options for Revisor from a
        configuration file. Configuration file may be customized using
        the --config CLI option"""

        self.log.debug(_("Setting options from configuration file"), level=4)

        # Check from which configuration file we should get the defaults
        # Other then default?
        if not self.cli_options.config == self.defaults.config:
            self.config = self.cli_options.config

        config = self.check_config()
        self.load_config(config)

        self.check_model(config)
        self.load_model(config)

    def check_model(self, config=None, val=None):
        """From a configuration file, check a model (either global configuration, or default).
        If you do not pass it a valid SafeConfigParser (config), we create our own from self.config"""

        if config == None:
            config = SafeConfigParser()
            config.read(self.config)

        # During load_config(), the model could have been set already
        # Also, the CLI Option --model hasn't been used
        if val == None:
            # No specific model to check
            if not self.cli_options.model == "":
                # CLI option --model
                if not config.has_section(self.cli_options.model):
                    self.log.error(_("No model %s in configuration file %s") % (self.cli_options.model,self.config), recoverable=self.gui_mode)
                else:
                    self.log.debug(_("Setting model to %s") % self.cli_options.model, level=4)
                    self.model = self.cli_options.model
            elif config.has_section("revisor"):
                if config.has_option("revisor","model"):
                    # Configuration file has a model set
                    if not config.has_section(config.get("revisor","model")):
                        if self.cli_options.model == self.defaults.model:
                            if self.cli_mode:
                                # Not specifying a model and not configuring a model is fatal for CLI
                                self.log.error(_("No model specified on the command line and no existing model configuration in %s") % (self.config), recoverable=False)
                            else:
                                self.log.error(_("Model %s configured in configuration file %s, but there is no such model configuration") % (config.get("revisor","model"),self.config), self.gui_mode)
                        else:
                            # We should never end up here
                            pass
                    else:
                        # Configuration file has a model section, so use the model
                        self.model = config.get("revisor","model")
                elif self.cli_mode:
                    self.log.error(_("No model specified on the command line and no existing model configuration in %s") % self.config, recoverable=False)
            elif self.cli_mode:
                self.log.error(_("No model specified on the command line and no existing model configuration in %s") % self.config, recoverable=False)
        else:
            # Model passed to this function
            if not config.has_section(val):
                self.log.error(_("Tried to load model %s but it doesn't exist inconfiguration file %s") % (val,self.config), self.gui_mode)
            else:
                self.model = val

    def load_model(self, config=None, model=None):
        """Loads the options from a SafeConfigParser self.model section
        If you do not pass it a valid SafeConfigParser (config), we create our own from self.config"""
        if config == None:
            config = self.check_config(self.config)

        if not model == None:
            self.model = model

        # Of course we need a valid section for self.model
        if config.has_section(self.model):
            # Check our main configuration
            if not config.has_option(self.model,"main"):
                self.log.error(_("Model %s has no configuration directive 'main' which is required") % self.model, recoverable=False)

            for varname in self.defaults.__dict__.keys():
                self.log.debug(_("Testing for configuration parameter %s") % varname, level=9)
                if not config.has_option(self.model,varname):
                    continue

                # These are illegal variables
                if varname in ["model", "config"]:
                    continue

                if isinstance(self.defaults.__dict__[varname], int):
                    val = config.getint(self.model,varname)
                elif isinstance(self.defaults.__dict__[varname], bool):
                    val = config.getboolean(self.model,varname)
                elif isinstance(self.defaults.__dict__[varname], str):
                    val = config.get(self.model,varname)
                elif isinstance(self.defaults.__dict__[varname], list):
                    val = eval(config.get(self.model,varname))
                elif isinstance(self.defaults.__dict__[varname], dict):
                    val = eval(config.get(self.model,varname))

                if hasattr(self,"check_setting_%s" % varname):
                    exec("retval = self.check_setting_%s(%r)" % (varname, val))
                    if not retval:
                        continue

                # In some occassions, you will want $datestamp to be replaced with YYYYMMDD
                if isinstance(val, str):
                    val = val.replace("$datestamp",datetime.date.today().strftime("%Y%m%d"))

                setattr(self,varname,val)
                self.log.debug(_("Setting %s to %r (from configuration file model %s)") % (varname,val,self.model))

        # A little after-care for:
        # product_name, which leads to
        # iso_basename, which leads to
        # iso_label

        if not config.has_option(self.model, "iso_label"):
            if not config.has_option(self.model, "iso_basename"):
                if not config.has_option(self.model, "product_name"):
                    # Sorry, you leave me nothing here
                    self.product_name = "Fedora"
                    self.iso_basename = self.product_name
                    self.iso_label = self.iso_basename
                else:
                    self.iso_basename = self.product_name
                    self.iso_label = self.iso_basename
            else:
                self.iso_label = self.iso_basename
        else:
            # If iso_label has been set, you know what you are doing... right?
            pass

        return True

    def check_config(self, val=None):
        """Checks self.config or the filename passed using 'val' and returns a SafeConfigParser instance"""

        if val:
            config_file = val
        else:
            config_file = self.config

        if not os.access(config_file, os.R_OK):
            self.log.error(_("Configuration file %s not readable") % config_file, recoverable=self.gui_mode)

        config = SafeConfigParser()
        self.log.debug(_("Reading configuration file %s") % config_file, level=9)
        try:
            config.read(config_file)
        except:
            self.log.error(_("Invalid configuration file %s") % config_file, recoverable=self.gui_mode)

        if not config.has_section("revisor"):
            self.log.warning(_("No master configuration section [revisor] in configuration file %s") % config_file)

        return config

    def load_config(self, config):
        """Given a SafeConfigParser instance, loads a Revisor Configuration file and checks,
        then sets everything it can find."""
        if config.has_section("revisor"):
            # Walk this section and see if for each item, there is also
            # a default. Because, if there is no default, it cannot be set
            for varname in self.defaults.__dict__.keys():
                if not config.has_option("revisor",varname):
                    continue

                if isinstance(self.defaults.__dict__[varname], int):
                    val = config.getint("revisor",varname)
                elif isinstance(self.defaults.__dict__[varname], bool):
                    val = config.getboolean("revisor",varname)
                elif isinstance(self.defaults.__dict__[varname], str):
                    val = config.get("revisor",varname)
                elif isinstance(self.defaults.__dict__[varname], list):
                    val = eval(config.get("revisor",varname))
                elif isinstance(self.defaults.__dict__[varname], dict):
                    val = eval(config.get("revisor",varname))

                if hasattr(self,"check_setting_%s" % varname):
                    exec("retval = self.check_setting_%s(%r)" % (varname, val))
                    if not retval:
                        # We just don't set it, check_setting_%s should have
                        # taken care of the error messages
                        continue

                if not self.defaults.__dict__[varname] == val:
                    setattr(self,varname,val)
                    self.log.debug(_("Setting %s to %r (from configuration file)") % (varname,val))

    def options_set_from_commandline(self):
        """Overrides default options from the CLI"""
        self.log.debug(_("Setting options from command-line"))

        config = SafeConfigParser()
        config.read(self.config)

        # Now set the rest of the CLI options to
        for option in self.cli_options.__dict__.keys():
            if not self.cli_options.__dict__[option] == self.defaults.__dict__[option]:
                if hasattr(self,"check_setting_%s" % option):
                    exec("retval = self.check_setting_%s(%r)" % (option, self.cli_options.__dict__[option]))
                    if not retval:
                        continue
                    else:
                        setattr(self,option,self.cli_options.__dict__[option])
                        self.log.debug(_("Setting %s to %r (from command line)") % (option,self.cli_options.__dict__[option]), level=8)
                elif self.plugins.plugin_check_setting("check_setting",option,self.cli_options.__dict__[option]):
                    self.log.debug(_("Checked setting %s through plugin") % option, level=9)
                    setattr(self,option,self.cli_options.__dict__[option])
                else:
                    self.log.debug(_("No check_setting_%s()") % option, level=9)
                    setattr(self,option,self.cli_options.__dict__[option])
                    self.log.debug(_("Setting %s to %r (from command line)") % (option,self.cli_options.__dict__[option]), level=8)
            else:
                self.log.debug(_("Not setting %s to %r (command line matches default)") % (option, self.cli_options.__dict__[option]), level=9)

    def check_options(self):
        """Checks the combination of options set from the defaults, configuration files
        and command-line. Assumes that whatever setting could have been checked is checked
        already; the options themselves are VALID. Does not take into account the options
        specified by modules; these modules will need to have a check_options() callable
        attribute taking this ConfigurationStore and it's CLI Options (cli_options)."""

        if  self.media_installation_cd or \
            self.media_installation_dvd or \
            self.media_installation_dvd_duallayer or \
            self.media_installation_bluray or \
            self.media_installation_bluray_duallayer or \
            self.media_installation_usb or \
            self.media_installation_tree or \
            self.media_installation_unified:

            self.media_installation = True

        elif self.media_utility_rescue:

            self.media_installation = True
        else:
            self.media_installation = False

        if  self.media_live_optical or \
            self.media_live_thumb or \
            self.media_live_hd or \
            self.media_live_raw:

            self.media_live = True
        else:
            self.media_live = False

        if self.mode_respin and self.media_live:
            # Hmm what should we do here?
            pass

        # Check options from modules
        self.plugins.check_options(self)

        if self.updates_img and not self.media_installation:
            self.log.error(_("Updates.img is only usable with installation media. Please remove --updates-img or also build installation media."), recoverable=False)

        if not self.kickstart_file == "":
            if not self.test_ks(self.kickstart_file):
                self.log.error(_("Kickstart failed"), recoverable=self.gui_mode)
                return
            if os.access(self.kickstart_file, os.R_OK):
                self.use_kickstart_file = True
            elif hasattr(self,"cobbler_use_distro") and hasattr(self,"cobbler_use_profile"):
                if not self.cobbler_use_distro and not self.cobbler_use_profile:
                    if self.cli_mode:
                        self.log.error(_("Kickstart file %s not readable" % self.kickstart_file), recoverable=False)
                    else:
                        self.log.error(_("Kickstart file %s fails to load, continuing with defaults" % self.kickstart_file))
            else:
                if self.cli_mode:
                    self.log.error(_("Kickstart file %s not readable" % self.kickstart_file), recoverable=False)
                else:
                    self.log.error(_("Kickstart file %s fails to load, continuing with defaults" % self.kickstart_file))
        else:
            if self.cli_mode:
                self.log.error(_("No kickstart file specified"), recoverable=False)

        if self.cli_mode and not self.check_media():
            self.log.error(_("No media specified"), recoverable=False)

        if self.cli_mode:
            # Here, we need to check whether any media has been specified (at all!)
            # Give me a really neat routine for each and every one of the options we don't know about
            self.check_media()

    def check_media(self):
        """Checks if any media has been specified. Note that we may not
        know anything about any of the plugins (we'll need to test
        hasattr(self,media_*) a lot)"""

        # What are media settings?
        for media in self.__dict__:
            if media.startswith("media_") and len(media.split("_")) == 2:
                if getattr(self,media):
                    return True

        self.log.error(_("No media specified"), recoverable=False)

    def get_package_list(self, media_types=None, list_types=None, archs=None, versions=None):

        if not media_types:
            media_types = self.packages_list.keys()
        elif isinstance(media_types, str):
            media_types = [media_types]

        if not list_types:
            list_types = self.packages_list['installation'].keys()
        elif isinstance(list_types, str):
            list_types = [list_types]

        if not archs:
            archs = [ 'all', self.architecture ]

        if not versions:
            versions = [ 'all', self.version_from ]

        pkg_list = []

        for mtype in media_types:
            for ltype in list_types:
                for arch in archs:
                    for version in versions:
                        try:
                            self.log.debug(_("pulling self.packages_list[%r][%r][%r][%r]") % (mtype,ltype,arch,version), level=9)
                            pkg_list.extend(self.packages_list[mtype][ltype][arch][version])
                        except KeyError, e:
                            pass

        self.log.debug(_("returning pkg_list: %r") % pkg_list, level=9)
        return pkg_list

class Defaults:
    """This class holds options that are the defaults. They should not be changed.
    Note that a lot of the defaults are actually set with command line options. The
    options in this class have no CLI parameter equivalent."""
    def __init__(self, plugins):
        """Sets the default configuration options for Revisor"""

        self.plugins = plugins

        # The default mode is GUI mode but these variables hold
        # if anything has been forced
        self.gui_mode = False
        self.cli_mode = False
        self.server_mode = False
        self.hub_mode = False
        self.headless_mode = False

        # Report sizes maximum length
        self.report_sizes_length = 20

        # Sets which models we want to use for spinning
        # Either have an empty string here (takes 1 line) or have a lot
        # of useless code doing hasattr() and try/except (You'll see this often)
        self.main = ""

        # Show repos, hide repos
        self.repos_enablesource = False
        self.repos_enabledebuginfo = False
        self.repos_enabletesting = False
        self.repos_enabledevelopment = False

        # Use the package manifest from the kickstart file you provided earlier
        self.kickstart_manifest = False

        # Whether to include debuginfo packages
        self.getdebuginfo = False

        # Customize that package manifest. Works like a charm if packages have
        # become obsolete or fail dependencies.
        self.kickstart_manifest_customize = False
        self.kickstart_options_customize = False
        self.kickstart_repos = False

        # Whether to use yum's exclude setting(1), or just deselect packages(0)
        # The default for now is 0 (deselect packages)
        self.kickstart_uses_pkgsack_exclude = 0

        # Show advanced configuration. Allows for manual package version
        # selection, kickstart options override, chroot shell, etc.
        self.advanced_configuration = False

        # Sets the mode in which we depsolve:
        # Allow conflicts between the packages for install media, or
        # don't allow them so you can install everything?
        self.dependency_resolve_allow_conflicts = False

        # Whether to create the repoview metadata
        self.repoview = False

        # Skip creating an SHA1SUM for the ISO images?
        self.skip_sha1sum = False

        # Skip inserting the md5sum into the ISO images?
        # This relates to being able to perform media checks
        self.skip_implantisomd5 = False

        # Set this to True if you are creating an everything spin
        # NOTE that setting this to true will bypass dependency
        # resolving, will thus break non-everything spins
        # NOTE that "everything" may also not have all dependencies
        # required. Use repoclosure from yum-utils to see if there's
        # any _missing_ dependencies to confirm.
        self.everything_spin = False

        self.pkgorder_file = ""
        self.pkgorder_style = ""

        # Use fedora-release by default
        self.release_pkgs = "^fedora-release.*$"
        self.release_files = "eula.txt fedora.css GPL README-BURNING-ISOS-en_US.txt RELEASE-NOTES-en_US.html ^RPM-GPG img images stylesheet-images"

        # Installation Media Options
        # Append this when kickstart is set to boot by default:
        self.im_append = ''
        # Whether or not to include boot.iso on the optical media
        # The default is to not include it
        self.include_bootiso = 0

        # Live Media options
        self.lm_use_shadow = True
        self.lm_use_md5 = True
        self.lm_use_nis = False
        self.lm_use_ldap = False
        self.lm_use_kerberos = False
        self.lm_use_hesiod = False
        self.lm_use_samba = False
        self.lm_use_nscd = False

        # Include the binary packages in a nice tree when composing live media
        self.getbinary = False

        self.lm_user_configuration = False
        self.lm_user_name = "live"
        self.lm_user_comment = "Fedora Unity - Revisor"
        self.lm_user_password = "live"

        self.lm_user_auto_login = False
        self.lm_user_wheel = True
        self.lm_wheel_sudo_no_passwd = True
        self.lm_dump_current_profile = False

        # FIXME, we don't really use it and it doesn't have a CLI option
        self.lm_name = "Live"
        # /FIXME

        self.lm_base_on = None

        self.lm_fs_label = "fedora-" + time.strftime("%Y%m%d")
        self.lm_skip_fs_compression = False
        self.lm_skip_prelink = False
        self.lm_ignore_deleted = True
        self.lm_blocksize = 4096

        # short, long, options
        self.lm_bootloader_stanzas = [
                                        ("linux",      _("Run from image"),                "rhgb quiet"),
                                        ("runfromram", _("Run from RAM - requires 1 GB+"), "rhgb quiet live_ram")
                                     ]

        self.lm_bootloader_timeout = 10
        self.lm_bootloader_isolinux_extras = ""
        self.lm_hostname = "livecd.fedoraunity.org"
        self.lm_default_runlevel=3

        # Default architecture we're running for
        self.architecture = "i386"

        self.bugurl = "Your distribution's bug reporting URL"

        # Still reading?
        self.nis_auth = ""
        self.ldap_auth = ""
        self.kerberos_auth = ""
        self.hesiod_auth = ""
        self.samba_auth = ""
        self.nscd_auth = ""

        # Not all options are CLI options
        try:
            if hasattr(self.plugins,"set_defaults"):
                self.plugins.set_defaults(self)
        except:
            pass

#    def __setattr__(self, name, val):
#        return

class Runtime:
    def __init__(self, plugins, defaults):
        """Set runtime variables. Some will change, others will not.
        Point is, that the defaults (always!) differ from the runtime. So,
        set the runtime variable when something needs to be changed and leave
        the default!

        Another side effect is that we can load the defaults, compare them to options,
        and set them in runtime, without keeping track of what options can be set from
        configuration files, and which can't"""

        self.plugins = plugins

        # Set the defaults
        for option in defaults.__dict__.keys():
            self.__dict__[option] = defaults.__dict__[option]

        # Whether to use a kickstart file
        self.use_kickstart_file = True

        # The repositories from the kickstart file
        self.repos_kickstart = []

        # Media sizes, in bytes, disc directoryes and lables
        self.mediatypes =   {           "index":
                                                    {
                                                        0: "cd",
                                                        1: "dvd",
                                                        2: "dvd-dl",
                                                        3: "bluray",
                                                        4: "bluray-dl",
                                                        5: "unified"
                                                    },
                                        "cd":       {
                                                        "size": 685 * 1024 * 1024,
                                                        "discdir": "cd",
                                                        "label": "CD",
                                                        "discs": 0,
                                                        "compose": "self.cfg.media_installation_cd"
                                                    },
                                        "dvd":      {
                                                        "size": 4300 * 1024 * 1024,
                                                        "discdir": "dvd",
                                                        "label": "DVD",
                                                        "discs": 0,
                                                        "compose": "self.cfg.media_installation_dvd"
                                                    },
                                        "dvd-dl":   {
                                                        # A DVD Dual Layer image shows up as 8GiB,
                                                        # instead of twice the size of a DVD
                                                        "size": 8000 * 1024 * 1024,
                                                        "discdir": "dvd-dl",
                                                        "label": "DVD-DL",
                                                        "discs": 0,
                                                        "compose": "self.cfg.media_installation_dvd_duallayer"
                                                    },
                                        "bluray":   {
                                                        "size": 23000 * 1024 * 1024,
                                                        "discdir": "bluray",
                                                        "label": "Bluray",
                                                        "discs": 0,
                                                        "compose": "self.cfg.media_installation_bluray"
                                                    },
                                        "bluray-dl":   {
                                                        "size": 47000 * 1024 * 1024,
                                                        "discdir": "bluray-dl",
                                                        "label": "Bluray-DL",
                                                        "discs": 0,
                                                        "compose": "self.cfg.media_installation_bluray_duallayer"
                                                    },
                                        "unified":  {
                                                        "size": -1,
                                                        "discdir": "unified",
                                                        "label" : "",
                                                        "discs": 1,
                                                        "compose": "self.cfg.media_installation_unified"
                                                    }
                                    }

        self.version_map = {
            "7" : "F7",
            "8" : "F8",
            "9" : "F9",
            "10" : "F10",
            "5" : "RHEL5"
        }

        # Repo store for dialog population
        self.repos = {}

        self.tasks = []
        self.built_iso_images = []
        self.repo_override = []

        self.i_did_all_this = False

        self.available_packages = []

        # Runtime variables
        self.media_installation = False
        self.media_live = False
        self.media_utility = False

        self.package_Xorg = False
        self.package_windowmanager_gnome = False
        self.package_windowmanager_kde = False
        self.package_windowmanager_xfce = False

        # Track how many packages we are dealing with, useful for progressbars
        self.number_of_packages = 0

        # Set to not do package order by default
        self.do_packageorder = False

        self.cmd_mkisofs = ['/usr/bin/mkisofs', '-v', '-U', '-J', '-R', '-T', '-f']

        self.x86bootargs = ['-b', 'isolinux/isolinux.bin', '-c', 'isolinux/boot.cat',
                            '-no-emul-boot', '-boot-load-size', '4', '-boot-info-table']

        self.ia64bootargs = ['-b', 'images/boot.img', '-no-emul-boot']

        self.ppcbootargs = ['-part', '-hfs', '-r', '-l', '-sysid', 'PPC', '-no-desktop', '-allow-multidot', '-chrp-boot',
                            '-map', os.path.join('/usr/lib/anaconda-runtime/boot', 'mapping'),
                            '-magic', os.path.join('/usr/lib/anaconda-runtime/boot', 'magic'),
                            '-hfs-bless']

        self.sparcbootargs = ['-G', '/boot/isofs.b', '-B', '...', '-s', '/boot/silo.conf', '-sparc-label', '"sparc"']

        ##
        ## These are packages required, or suggested for Installation or Live Media
        ##

        # Layout:
        # self.packages_list[media_type][suggest|require|allarch|onearch][arch|all][version|all]
        # media_type = 'installation' or 'live'
        #
        # suggest = if available, include
        #           if not available, don't complain
        # require = if not available, die
        # allarch = do not select the best matching arch, instead include all compatarch
        # onearch = do not select all compatarchs, instead select the best matching arch
        #
        # arch = if specific for an architecture, or 'all' if apllicable to all architectures
        #
        # version = the kickstart.version.* string equivalent of versions, or 'all' if
        #           applicable to all versions
        #
        # Also note there is get_package_list(media_type(s),list_type(s),arch,version)
        self.packages_list = {
            "installation": {
                "require": {
                    "all": {
                        "all": [                # Note that this list contains /everything/ the installer can possibly need (rather extensively, even)
                            'acl',              # while some of it, if not most of it, is actually related to the graphical installer.
                            'anaconda',
                            'anaconda-runtime',
                            'atk',
                            'attr',
                            'audit-libs',
                            'authconfig',
                            'bash',
                            'beecrypt',
                            'bitmap-fonts-cjk',
                            'booty',
                            'bzip2',
                            'bzip2-libs',
                            'cairo',
                            'cjkunifonts-ukai',
                            'comps-extras',
                            'coreutils',
                            'cpio',
                            'cryptsetup-luks',
                            'db4',
                            'dbus',
                            'dbus-python',
                            'dejavu-fonts',
                            'dejavu-lgc-fonts',
                            'device-mapper',
                            'dmraid',
                            'dosfstools',
                            'dump',
                            'e2fsprogs',
                            'e2fsprogs-libs',
                            'elfutils-libelf',
                            'expat',
                            'findutils',
                            'firstboot',
                            'fontconfig',
                            'fonts-arabic',
                            'fonts-bengali',
                            'fonts-chinese',
                            'fonts-gujarati',
                            'fonts-hindi',
                            'fonts-ISO8859-2',
                            'fonts-ISO8859-9',
                            'fonts-japanese',
                            'fonts-kannada',
                            'fonts-korean',
                            'fonts-malayalam',
                            'fonts-oriya',
                            'fonts-punjabi',
                            'fonts-sinhala',
                            'fonts-tamil',
                            'fonts-telugu',
                            'freetype',
                            'ftp',
                            'gail',
                            'gdk-pixbuf',
                            'glib2',
                            'glibc',
                            'glibc-common',
                            'gnome-python2-canvas',
                            'gnome-python2-gtkhtml2',
                            'gnome-themes',
                            'gpm',
                            'groff',
                            'gtk2',
                            'gtk2-engines',
                            'gtkhtml2',
                            'gzip',
                            'hal',
                            'hdparm',
                            'hwdata',
                            'iputils',
                            'joe',
                            'kernel',
                            'krb5-libs',
                            'kudzu',
                            'less',
                            'libacl',
                            'libart_lgpl',
                            'libattr',
                            'libbdevid-python',
                            'libdhcp',
                            'libdhcp4client',
                            'libdhcp6client',
                            'libgcc',
                            'libgcrypt',
                            'libglade2',
                            'libgnomecanvas',
                            'libgpg-error',
                            'libidn',
                            'libjpeg',
                            'libnl',
                            'libpng',
                            'libtermcap',
                            'libselinux',
                            'libselinux-python',
                            'libsemanage',
                            'libsepol',
                            'libstdc++',
                            'libthai',
                            'libuser',
                            'libvolume_id',
                            'libxcb',
                            'libxml2',
                            'lvm2',
                            'man',
                            'mdadm',
                            'mkinitrd',
                            'mtools',
                            'mtr',
                            'mt-st',
                            'nash',
                            'ncurses',
                            'neon',
                            'net-tools',
                            'newt',
                            'nspr',
                            'nss',
                            'ntfsprogs',
                            'openssh',
                            'openssh-clients',
                            'pam',
                            'pango',
                            'parted',
                            'pciutils',
                            'pcre',
                            'policycoreutils',
                            'popt',
                            'prelink',
                            'procps',
                            'pycairo',
                            'pygobject2',
                            'pygtk2',
                            'pygtk2-libglade',
                            'pykickstart',
                            'pyparted',
                            'python',
                            'python-list',
                            'python-pyblock',
                            'python-urlgrabber',
                            'pyx86config',
                            'readline',
                            'rhpl',
                            'rhxpl',
                            'rpm',
                            'rpm-libs',
                            'rpm-python',
                            'rsh',
                            'rsync',
                            'samba-client',
                            'sazanami-fonts-gothic',
                            'sed',
                            'selinux-policy',
                            'selinux-policy-targeted',
                            'setup',
                            'slang',
                            'smartmontools',
                            'specspo',
                            'sqlite',
                            'synaptics',
                            'system-config-date',
                            'system-config-keyboard',
                            'taipeifonts',
                            'tar',
                            'tcp_wrappers',
                            'traceroute',
                            'tzdata',
                            'udev',
                            'urw-fonts',
                            'vnc-libs',
                            'vnc-server',
                            'Xft',
                            'xorg-x11',
                            'xorg-x11-100dpi-fonts',
                            'xorg-x11-base',
                            'xorg-x11-base-fonts',
                            'xorg-x11-drivers',
                            'xorg-x11-fonts-ISO8859-1-75dpi',
                            'xorg-x11-ISO8859-15-75dpi',
                            'xorg-x11-ISO8859-15-75dpi-fonts',
                            'xorg-x11-ISO8859-2-75dpi-fonts',
                            'xorg-x11-ISO8859-9-75dpi-fonts',
                            'xorg-x11-KOI8-R',
                            'xorg-x11-KOI8-R-75dpi-fonts',
                            'xorg-x11-libs',
                            'xorg-x11-libs-data',
                            'xorg-x11-server-Xorg',
                            'xorg-x11-xfs',
                            'yum',
                            'zenity',
                            'zlib'
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                            'busybox-anaconda',
                            'device-mapper-libs',
                            'gfs2-utils',
                            'iscsi-initiator-utils',
                            'jfsutils',
                            'keyutils-libs',
                            'libuser-python',
                            'newt-python',
                            'pirut',
                            'reiserfs-utils',
                            'rpcbind',
                            'udev-static',
                            'xfsdump',
                            'xfsprogs',
                            'yum-fedorakmod',
                            'yum-metadata-parser'
                        ],
                        "F7": [
                            'busybox-anaconda',
                            'device-mapper-libs',
                            'gfs2-utils',
                            'iscsi-initiator-utils',
                            'jfsutils',
                            'keyutils-libs',
                            'pirut',
                            'portmap',
                            'reiserfs-utils',
                            'udev-static',
                            'util-linux',
                            'xfsdump',
                            'xfsprogs',
                            'xorg-x11-fonts-base',
                            'yum-fedorakmod',
                            'yum-metadata-parser'
                        ],
                        "RHEL5": [
                            'portmap',
                            'python-elementtree',
                            'python-sqlite',
                            'util-linux',
                        ]
                    },
                    "i386": {
                        "all": [
                            'dmidecode',
                            'grub',
                            'kernel-xen',
                            'memtest86+',
                            'pcmciautils',
                            'syslinux'
                        ]
                    },
                    "x86_64": {
                        "all": [
                            'dmidecode',
                            'glibc',
                            'grub',
                            'kernel-xen',
                            'memtest86+',
                            'openssl',
                            'pcmciautils',
                            'syslinux'
                        ]
                    },
                    "ia64": {
                        "all": [
                            'dmidecode',
                            'elilo'
                        ]
                    },
                    "s390": {
                        "all": [
                            's390utils',
                            'binutils',
                            'tcp_wrappers',
                            'net-tools',
                            'openssh',
                            'openssh-server',
                            'login',
                            'initscripts',
                            'login',
                            'mount',
                            'grep',
                            'modutils',
                            'gawk',
                            'strace',
                            'xorg-x11-xauth',
                            'xorg-x11-libs'
                        ]
                    },
                    "ppc": {
                        "all": [
                            'glibc',
                            'hfsutils',
                            'openssl',
                            'pcmciautils',
                            'pdisk',
                            'yaboot'
                        ]
                    },
                    "ppc64": {
                        "all": [
                            'glibc',
                            'hfsutils',
                            'openssl',
                            'pcmciautils',
                            'pdisk',
                            'yaboot'
                        ]
                    }
                },
                "suggest": {
                },
                "allarch": {
                    "all": {
                        "all": [
                            'kernel',       # The installer builds against .i586 and .i686
                            'libbeagle',
                            'pm-utils'
                        ],
                    },
                    "i386": {
                        "all": [            # Both .i386 and .i686 need to be pulled in. i386 to build the installer with, and
                            'glibc',        # i686 to be installed on the system - should that be the best matching architecture.
                            'openssl'
                        ]
                    }
                },
                "onearch": {
                    "all": {
                    }
                }
            },
            "live": {
                "require": {
                    "all": {
                        "all": [
                            'syslinux',
                        ],
                        "DEVEL": [
                            'upstart',
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                            'sysvinit',
                        ],
                        "F7": [
                            'sysvinit',
                        ],
                        "RHEL5": [
                            'sysvinit',
                        ]
                    },
                    "i386": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "x86_64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    }
                },
                "suggest": {
                    "all": {
                        "all": [
                            'system-logos',
                            'wget'
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "i386": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "x86_64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    }
                },
                "allarch": {            # This relates to multilib I guess... No use-case yet, but it's in here anyway
                    "all": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "i386": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "x86_64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    }
                },
                "onearch": {
                    "all": {
                        "all": [
                            'kernel'
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "i386": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "x86_64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    },
                    "ppc64": {
                        "all": [
                        ],
                        "DEVEL": [
                        ],
                        "F10": [
                        ],
                        "F9": [
                        ],
                        "F8": [
                        ],
                        "F7": [
                        ],
                        "RHEL5": [
                        ]
                    }
                }
            }
        }

        # Nasty, but it saves us from requiring system-config-display/firstboot
        self.default_xorg_config = """

Section "ServerLayout"
        Identifier     "Default Layout"
        Screen      0  "Screen0" 0 0
        InputDevice    "Keyboard0" "CoreKeyboard"
EndSection

Section "InputDevice"
        Identifier  "Keyboard0"
        Driver      "kbd"
        Option      "XkbModel" "pc105"
        Option      "XkbLayout" "%s"
EndSection

Section "Device"
        Identifier  "Videocard0"
        Driver      "%s"
EndSection

Section "Screen"
        Identifier "Screen0"
        Device     "Videocard0"
        DefaultDepth     24
        SubSection "Display"
                Viewport   0 0
                Depth     24
        EndSubSection
EndSection

"""

        self.gdm_auto_login = """
[daemon]
TimedLoginEnable=true
TimedLogin=%(username)
TimedLoginDelay=10
"""

        self.added_repos = []

        self.ts_length_pre_depsolve = 0

# FIXME: I'm not sure if setting runtime variables from plugins is such a good idea
#
#        # Any runtime variables from our plugins?
#        self.plugins.set_runtime(self)

