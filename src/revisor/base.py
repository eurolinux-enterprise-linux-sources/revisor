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

import imgcreate
import logging
from ConfigParser import SafeConfigParser
from ConfigParser import RawConfigParser
import string
import subprocess
import time
import math
import re
import revisor
import rpmUtils.arch
import shutil
import pwd
import fnmatch
import yum
import yum.misc
import yum.packageSack

from revisor.cfg import Defaults, Runtime
import revisor.cfg
import revisor.image
from revisor import misc
import revisor.progress
import revisor.kickstart as kickstart
import revisor.image

# Import constants
from revisor.constants import *

# Translation
from revisor.translate import _, N_

class RevisorBase:
    """RevisorBase holds common functions shared amongst our CLI and GUI mode"""
    def __init__(self, revisor):
        """Initializes the RevisorBase class with the options specified from the command line.
        Launches our plugin detection.
        Creates a logger instance
        Creates a configuration store
        Detects whether we are in CLI or GUI mode
        Sets the logger configuration
        Sets up the final configuration store
        Sets up yum as far as possible
        Sets up Revisor kickstart as far as possible"""

        # Get the options parser, it's valuable ;-)
        self.parser = revisor.parser

        # The options it has defined are valuable too
        self.cli_options = revisor.cli_options
        self.plugins = revisor.plugins
        self.plugins.base = self

        # At this point, 'self' isn't much yet, so:
        # first create a simple logger instance that won't do much,
        # then create a configuration store with that logger,
        # then start detecting the mode that we are in (GUI / CLI),
        # then let the logger know about the configuration store,
        # then /really/ set up the configuration store (now that it has a
        #     valid logger that knows about the configuration store),
        #
        # Create logger
        self.create_logger()

        # Create ConfigStore (it needs the logger to be created!)
        self.create_configstore()

        # Detect our mode (options or try/except)
        self.detect_mode()

        # Let the logger know about cfg (it needs a ConfigStore instance!)
        self.log.set_config(self.cfg)

        # Then really setup the ConfigStore (because that needs a logger!)
        self.cfg.setup_cfg()

        misc.check_selinux(log=self.log)

        self.cfg.setup_yum()
        self.cfg.setup_ks()

    def run(self):
        """Split into either running CLI, Server, Hub or GUI"""
        if self.cfg.cli_mode:
            self.log.debug(_("Running Revisor in CLI mode..."), level=1)
            import revisor.cli
            self.cli = revisor.cli.RevisorCLI(self)
            self.cli.run()
        elif hasattr(self.cfg,"server_mode") or hasattr(self.cfg,"hub_mode"):
            # Check hub_mode,
            # Then check server_mode,
            # If we have both attributes, but none is set, fall back to GUI mode
            if self.cfg.hub_mode:
                self.log.debug(_("Running Revisor in Hub mode..."), level=1)
                self.hub = self.plugins.modhub
                self.cfg.gui_mode = False #hack!
                self.hub.run(base=self)
#            elif self.cfg.composer_mode:
#                self.log.debug(_("Running Revisor in Composer mode..."), level=1)
#                self.composer = self.plugins.modcomposer
#                self.cfg.gui_mode = False #hack!
#                self.composer.run(base=self)
            elif self.cfg.server_mode:
                self.log.debug(_("Running Revisor in RPC Server mode..."), level=1)
                self.server = self.plugins.modserver
                self.server.run(base=self)
            elif self.cfg.gui_mode:
                self.log.debug(_("Running Revisor in GUI mode..."), level=1)
                self.gui = self.plugins.modgui
                self.gui.run(base=self)

        # And, finally, fall back to GUI mode
        elif self.cfg.gui_mode:
            self.log.debug(_("Running Revisor in GUI mode..."), level=1)
            self.gui = self.plugins.modgui
            self.gui.run(base=self)

    def create_logger(self):
        """Create a logger instance using cli_options.debuglevel"""
        if not self.cli_options.debuglevel == None:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO
            self.cli_options.debuglevel = 0

        # Initialize logger
        self.log = revisor.logger.Logger(loglevel=loglevel, debuglevel=self.cli_options.debuglevel, logfile=self.cli_options.logfile)

    def create_configstore(self):
        """Initialize Configuration Store"""
        self.cfg = revisor.cfg.ConfigStore(self)

    def detect_mode(self):
        """Detect whether we run in CLI or in GUI mode. (GUI is default)

        Headless creates a RevisorBase object that does nothing on its own.
        Useful for spawning your army of Revisor daemons."""

        if self.cli_options.gui_mode:
            self.cfg._set_gui_mode()
        elif self.cli_options.cli_mode:
            self.cfg._set_cli_mode()
        elif hasattr(self.cli_options,"server_mode"):
            if not self.cli_options.server_mode:
                try:
                    import gtk
                    import gtk.glade
                    import gobject
                    import gtk.gdk as gdk
                    self.cfg._set_gui_mode()
                except ImportError:
                    self.cfg._set_cli_mode()
        else:
            try:
                import gtk
                import gtk.glade
                import gobject
                import gtk.gdk as gdk
                self.cfg._set_gui_mode()
            except ImportError:
                self.cfg._set_cli_mode()

    def show_help(self, keyword):
        """Some routine to trigger so that help (given a keyword) is being shown"""
        if self.cfg.gui_mode:
            self.gui.base_buttons_xml.get_widget("button_information").set_sensitive(False)
            # Drop to current user, wow we need to fix having to run GTK as root :-/
            # This code might be able to allow us to have a protected "we need root" class
            # when needing to run things as uid 0
            # This works, but does not allow us to attach to an already running firefox
            running_user = os.getlogin()
            target_uid = pwd.getpwnam(running_user).pw_uid
            location = "%s%s" % (DOCS_BASEPATH, keyword)
            pid = os.fork()
            if not pid:
                os.setreuid(target_uid, target_uid)
                self.log.info(_("Opening up %s") % location)
                try:
                    import webbrowser
                    webbrowser.open(location, new=2)
                except ImportError:
                    self.log.info(_("No 'webbrowser module, trying htmlview"))
                    try:
                        os.execv("/usr/bin/htmlview", [location])
                    except OSError:
                        self.log.error(_("Cannot fork process showing help, go to: %s") % location)
                sys.exit(0)
            else:
                self.gui.base_buttons_xml.get_widget("button_information").set_sensitive(True)
        else:
            self.log.warning(_("Cannot show Help in CLI mode, go to: %s") % location)

    def setup_yum(self):
        """Setup the yum object"""

        # Let's make sure the cfg.setup_yum() is run
        self.cfg.setup_yum()

        self.cfg.yumobj.pbar = self.progress_bar(_("Loading Repositories"), callback=True)

        self.log.debug(_("Getting configuration from %s") % self.cfg.main, level=2)

        try:
            if hasattr(self.cfg.yumobj,"preconf"):
                self.cfg.yumobj.preconf.fn = self.cfg.main
                self.cfg.yumobj.preconf.init_plugins = True
                self.cfg.yumobj.preconf.plugin_types = (yum.plugins.TYPE_CORE,)
                self.cfg.yumobj.preconf.debuglevel = self.cfg.debuglevel
                self.cfg.yumobj.preconf.errorlevel = self.cfg.debuglevel
                self.cfg.yumobj._getConfig()
            elif hasattr(self.cfg.yumobj,"_getConfig"):
                self.cfg.yumobj._getConfig(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
            else:
                self.cfg.yumobj.doConfigSetup(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
                self.log.debug(_("Using deprecated YUM function: %s()") % "doConfigSetup", level=7)
        except:
            self.log.error(_("yum.YumBase.doConfigSetup failed, probably an invalid configuration file %s") % self.cfg.main, recoverable=False)

        try:
            if not self.cfg.repo_override:
                self.cfg.reposSetup(callback=self.cfg.yumobj.pbar)
                repo_setup = True
            if self.cfg.repo_override:
                # Clear all the repos we have enabled from the model, and inject our override repo(s)
                for repo in self.cfg.yumobj.repos.repos.keys():
                    self.cfg.yumobj.repos.delete(str(repo))

                for repo in self.cfg.repo_override:
                    repoObj = yum.yumRepo.YumRepository(repo["name"])
                    repoObj.setAttribute('name', repo["name"])
                    repoObj.setAttribute('baseurl', repo["baseurl"])
                    repoObj.setAttribute('gpgcheck', repo["gpgcheck"])
                    self.cfg.yumobj.repos.add(repoObj)
                    self.cfg.yumobj.repos.enableRepo(repoObj.id)

                repo_setup=True

            #for repo in self.cfg.added_repos:
                #print "Adding custom repo %s to the yum repositories" % repo.id
                #repo.setAttribute('basecachedir', self.cfg.yumobj.conf.cachedir)
                #self.cfg.yumobj.repos.add(repo)
                #self.cfg.yumobj.repos.enableRepo(repo.id)

            #for repo in self.cfg.yumobj.repos.repos.keys():
                #print str(repo)

            #for repo in self.cfg.yumobj.repos.listEnabled():
                #print repo.name

        except yum.Errors.LockError:
            self.cfg.yumobj.pbar.destroy()
            self.log.error(_("Another application is running which is accessing software information."), recoverable=False)
            repo_setup = False

        except revisor.errors.RevisorDownloadError, e:
            self.cfg.yumobj.pbar.destroy()
            self.log.error(_("Fatal Error: Unable to retrieve software information.\n" + \
                            "\tThis could be caused by one of the following:\n" + \
                            "\t - not having a network connection available,\n" + \
                            "\t - Server refusing connections,\n" + \
                            "\t - Using a mirror that isn't fully synchronized,\n" + \
                            "\t - Misconfigured repositories."), recoverable=self.cfg.gui_mode)
            repo_setup = False

        if repo_setup:

            self.log.debug(_("Setting up a Transaction Set"), level=6)
            if hasattr(self.cfg.yumobj,"_getTs"):
                self.cfg.yumobj._getTs()
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doTsSetup", level=7)
                self.cfg.yumobj.doTsSetup()

            self.log.debug(_("Getting myself a piece of the RPMDB"), level=6)
            if hasattr(self.cfg.yumobj,"_getRpmDB"):
                self.cfg.yumobj._getRpmDB()
            elif hasattr(self.cfg.yumobj,"doSetupRPMDB"):
                self.log.debug(_("Using deprecated YUM function: %s()") % "doSetupRPMDB", level=7)
                self.cfg.yumobj.doSetupRPMDB()
            elif hasattr(self.cfg.yumobj,"doRpmDBSetup"):
                self.log.debug(_("Apparently we're running on an Enterprise Linux system (we can tell from the way yum sets up the RPM Database)"), level=7)
                self.cfg.yumobj.doRpmDBSetup()

            self.log.debug(_("Getting Repository Information"), level=6)
            if hasattr(self.cfg.yumobj,"_getRepos"):
                self.cfg.yumobj._getRepos()
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doRepoSetup", level=7)
                self.cfg.yumobj.doRepoSetup()

            self.log.debug(_("Arch list = %s") % self.cfg.arch_list, level=9)

            self.log.debug(_("Getting the Package Sacks"), level=6)
            try:
                if hasattr(self.cfg.yumobj,"_getSacks"):
                    self.cfg.yumobj._getSacks(archlist=self.cfg.arch_list)
                else:
                    self.log.debug(_("Using deprecated YUM function: %s()") % "doSackSetup", level=7)
                    self.cfg.yumobj.doSackSetup(archlist=self.cfg.arch_list)
            except:
                pass

            self.log.debug(_("All OK so far, %d packages in the Package Sack") % len(self.cfg.yumobj.pkgSack.simplePkgList()), level=9)

            self.cfg.yumobj.pbar.destroy()
            return True
        else:
            self.cfg.yumobj.pbar.destroy()
            return False

    def pkglist_from_ksdata(self, groupList=[], packageList=[], excludedList=[], ignore_list=[]):
        """
            Takes valid groupList, packageList and excludedList such
            as in kickstart package manifests, and selects packages
            available in the PackageSack using these lists. The way
            it does so depends on whether we are doing Installation
            Media Respins.

            See also:

            - kickstart_uses_pkgsack_exclude
            - revisor.kickstart.pkglist_from_ksdata_livecdtools()
            - revisor.kickstart.pkglist_from_ksdata_normal()
            - revisor.kickstart.pkglist_from_ksdata_respin()
        """

        self.log.debug(_("Building a nice package list from ksdata, and adding it to the transaction"), level=6)

        self.log.debug(_("Package sack excludes are now: %r") % self.cfg.yumobj.conf.exclude)

        if self.cfg.kickstart_uses_pkgsack_exclude:
            # Exclude the packages in the excludedList from the PackageSack.
            # The packages in the excludedList are not available to the
            # YUM object anymore, and so are not pulled into the compose no
            # matter what.

            # Warn about the consequences of kickstart_uses_pkgsack_exclude
            # in combination with mode_respin.

            if self.cfg.mode_respin:
                self.log.warning(_("You've configured Revisor to use " + \
                                   "PackageSack excludes and Respin mode. " + \
                                   "The results are not going to resemble " + \
                                   "a true \"Re-Spin\""))

            for pkg in excludedList:
                self.cfg.yumobj.conf.exclude.append(pkg)

            self.log.debug(_("Using pkgsack excludes, the list of packages " + \
                             "to exclude is now: %r")
                             % self.cfg.yumobj.conf.exclude, level=9)

            # Redo the population of the PackageSack with our new excludes.
            try:
                if hasattr(self.cfg.yumobj,"_getSacks"):
                    self.cfg.yumobj._getSacks(archlist=self.cfg.arch_list)
                else:
                    self.log.debug(_("Using deprecated YUM function: %s()")
                                     % "doSackSetup", level=7)
                    self.cfg.yumobj.doSackSetup(archlist=self.cfg.arch_list)
            except:
                pass

        # Actually, let's figure out what mode we're in and call something
        #
        # Live Media:
        #
        # In live media composes, it is of essence to select packages using
        # yum.selectGroup() and yum.install()
        #
        # Installation Media:
        #
        # Depending on whether we are in respin mode, we either select the
        # packages using YUM's internal search mode, or manually.

        self.log.debug(_("What we're getting from pykickstart is: " + \
                    "%d groups, %d packages and %d excluded packages. " + \
                    "%d packages are being explicitly ignored.")
                    % (
                        len(groupList),
                        len(packageList),
                        len(excludedList),
                        len(ignore_list)
                    ),
                    level=9)


        pbar = self.progress_bar(_("Select kickstart packages"))

        if self.cfg.media_live:
            self.log.debug(_("Kickstart mode: livecd-tools"), level=8)
            kickstart.pkglist_from_ksdata_livecdtools(
                                                        self.log,
                                                        self.cfg,
                                                        pbar=pbar,
                                                        groupList=groupList,
                                                        packageList=packageList,
                                                        excludedList=excludedList,
                                                        ignore_list=ignore_list)
        elif self.cfg.mode_respin:
            if self.cfg.media_installation:
                self.log.debug(_("Kickstart mode: respin"))
                kickstart.pkglist_from_ksdata_respin(
                                                        self.log,
                                                        self.cfg,
                                                        pbar=pbar,
                                                        groupList=groupList,
                                                        packageList=packageList,
                                                        excludedList=excludedList)
            else:
                self.log.debug(_("Kickstart mode: normal"))
                kickstart.pkglist_from_ksdata_normal(
                                                        self.log,
                                                        self.cfg,
                                                        pbar=pbar,
                                                        groupList=groupList,
                                                        packageList=packageList,
                                                        excludedList=excludedList,
                                                        ignore_list=ignore_list)
        else:
            self.log.debug(_("Kickstart mode: normal"))
            kickstart.pkglist_from_ksdata_normal(
                                                    self.log,
                                                    self.cfg,
                                                    pbar=pbar,
                                                    groupList=groupList,
                                                    packageList=packageList,
                                                    excludedList=excludedList,
                                                    ignore_list=ignore_list)

        pbar.destroy()

    def pkglist_from_ksdata_livecdtools(self, *args, **kw):
        self.log.warning(_("Deprecated function called: " + \
                           "base.pkglist_from_ksdata_livecdtools(). Use " + \
                           "kickstart.pkglist_from_ksdata_livecdtools() " + \
                           "instead."))

        kickstart.pkglist_from_ksdata_livecdtools(*args, **kw)

    def pkglist_from_ksdata_normal(self, *args, **kw):
        self.log.warning(_("Deprecated function called: " + \
                           "base.pkglist_from_ksdata_normal(). Use " + \
                           "kickstart.pkglist_from_ksdata_normal() " + \
                           "instead."))

        kickstart.pkglist_from_ksdata_normal(*args, **kw)

    def pkglist_from_ksdata_respin(self, *args, **kw):
        self.log.warning(_("Deprecated function called: " + \
                           "base.pkglist_from_ksdata_respin(). Use " + \
                           "kickstart.pkglist_from_ksdata_respin() " + \
                           "instead."))

        kickstart.pkglist_from_ksdata_respin(*args, **kw)

    def progress_bar(self, title="", parent=None, xml=None, callback=False):
        """This function should be used to determine the type of progress bar we need.
        There's three types:
            - GUI Dialog Progress Bar (separate dialog, window pops up)
            - GUI Nested Progress Bar (no separate dialog, progress bar is in gui.frame_xml)
            - CLI Progress Bar

        This function also determines whether we should have a Callback Progress Bar"""

        self.log.debug(_("Initting progress bar for ") + title, level=9)

        if self.cfg.gui_mode:
            try:
                if hasattr(self.gui,"BuildMedia"):
                    self.gui.BuildMedia.show_task_list()
            except:
                self.log.debug(_("Apparently we have not yet entered the Build Media stage"), level=9)

            if callback:
                if not self.gui.frame_xml.get_widget("part_progress") == None:
                    return revisor.progress.ProgressCallbackGUI(title=title, parent=self.gui, xml=self.gui.frame_xml)
                elif not self.gui.main_window == None:
                    return revisor.progress.ProgressCallbackGUI(title=title, parent=self.gui, xml=self.gui.frame_xml)
                else:
                    return revisor.progress.ProgressCallbackGUI(title=title, parent=parent, xml=xml)
            else:
                if not self.gui.frame_xml.get_widget("part_progress") == None:
                    return revisor.progress.ProgressGUI(title=title, parent=self.gui, xml=self.gui.frame_xml)
                elif not self.gui.main_window == None:
                    return revisor.progress.ProgressGUI(title=title, parent=self.gui, xml=xml)
                else:
                    return revisor.progress.ProgressGUI(title=title, parent=parent, xml=xml)
        else:
            if callback:
                return revisor.progress.ProgressCallbackCLI(title=title)
            else:
                return revisor.progress.ProgressCLI(title=title)

#    def set_mode(self, mode):
#        self.mode = mode

    def get_package_deps(self, po, pbar):
        """Add the dependencies for a given package to the
           transaction info"""

        self.log.debug(_("Checking dependencies for %s.%s") % (po.name, po.arch), level=8)

        pbar.cur_task += 1.0
        reqs = po.requires
        provs = po.provides

        for req in reqs:
            if self.resolved_deps.has_key(req):
                pbar.cur_task += 1.0
                pbar.set_fraction(pbar.cur_task/pbar.num_tasks)
                continue

            (r,f,v) = req
            if r.startswith('rpmlib(') or r.startswith('config('):
                pbar.cur_task += 1.0
                pbar.set_fraction(pbar.cur_task/pbar.num_tasks)
                continue

            deps = self.cfg.yumobj.whatProvides(r, f, v).returnPackages()

            if not deps:
#                pbar.cur_task += 1.0
                self.log.warning(_("Unresolvable dependency %s %s %s in %s.%s") % (r, f, v, po.name, po.arch))
                continue

            depsack = yum.packageSack.ListPackageSack(deps)

            for dep in depsack.returnNewestByNameArch():
                self.cfg.yumobj.tsInfo.addInstall(dep)
                self.log.debug(_("Added %s-%s:%s-%s.%s for %s-%s:%s-%s.%s (requiring %s %s %s)") % (dep.name, dep.epoch, dep.version, dep.release, dep.arch, po.name, po.epoch, po.version, po.release, po.arch, r, f, v), level=9)

    def check_dependencies_conflicts(self):
        self.log.debug(_("Checking dependencies - allowing conflicts within the package set"), level=5)
        pbar = self.progress_bar(_("Resolving Dependencies"), callback=True)
        pbar.num_tasks = float(len(self.cfg.yumobj.tsInfo.getMembers()))

        # Hook in modrebrand to replace fedora-logos
        self.cfg.plugins.exec_hook("pre_resolve_dependencies")

        (resolved_deps, final_pkgobjs) = revisor.misc.resolve_dependencies_inclusive(self.cfg.yumobj, logger=self.log, pbar=pbar)

        # Hook in modrebrand to replace fedora-logos
        self.cfg.plugins.exec_hook("post_resolve_dependencies")

        pbar.destroy()

        # Create a self-sustaining tree?
        if self.cfg.installation_mode_ss:

            self.log.debug(_("Pulling in build requirements"))

            pbar = self.progress_bar(_("Resolving Build Dependencies"), callback=True)

            (resolved_deps, final_pkgobjs) = revisor.misc.get_source_package_builddeps(self.cfg.yumobj, logger=self.log, pbar=pbar, arch_list=self.cfg.arch_list, resolved_deps=resolved_deps, final_pkgobjs=final_pkgobjs)

            pbar.destroy()

        # Include all binary rpms?
        if self.cfg.installation_mode_full:
            (resolved_deps, final_pkgobjs) = revisor.misc.get_source_package_binary_rpms(self.cfg.yumobj, logger=self.log, pbar=pbar, resolved_deps=resolved_deps, final_pkgobjs=final_pkgobjs)

        # Now, if the excluded packages have not been excluded by yum's exclude setting,
        # try to determine the packages that got pulled in anyway, and leave a huge big
        # scrap on the whiteboard

        if not self.cfg.kickstart_uses_pkgsack_exclude:
            incl_pkgs = []
            for txmbr in self.cfg.yumobj.tsInfo.getMembers():
                if txmbr.po.name in self.cfg.ksobj._get("packages","excludedList"):
                    incl_pkgs.append(txmbr.po.name)

            if len(incl_pkgs) > 0:
                self.log.warning(_("The following packages were excluded using the kickstart package manifest, but were included for dependency resolving:\n - %s") % '\n - '.join(incl_pkgs))

    def check_dependencies_no_conflicts(self):
        """Check the dependencies"""
        self.log.debug(_("Checking dependencies - not allowing any conflicts within the package set"), level=5)
        pbar = self.progress_bar(_("Resolving Dependencies"), callback=True)

        # Hook in modrebrand to replace fedora-logos
        self.cfg.plugins.exec_hook("pre_resolve_dependencies")

        dsCB = revisor.progress.dscb(pbar, self.cfg.yumobj, self.cfg)
        self.cfg.yumobj.dsCallback = dsCB

        try:
            (res, resmsg) = self.cfg.yumobj.buildTransaction()
            if res != 2:
                # FIXME:
                # - Dependency resolving may fail yet continue in case of composing installation media
                #   - which is not supposed to go to cobbler
                #   - which does not include the kickstart

                self.cfg.recoverable=True

                if res == 1:
                    # We at least now that live media is going to fail (transaction cannot be executed)
                    if self.cfg.media_live:
                        self.cfg.recoverable = self.cfg.gui_mode
                    elif self.cfg.kickstart_include:
                        self.cfg.recoverable = self.cfg.gui_mode
                    else:
                        self.cfg.plugins.exec_hook("dependency_resolve_fail")

                    self.log.error(_("""Unable to resolve dependencies for some packages selected:\n\n%s""" % (string.join(resmsg, "\n"))), recoverable=self.cfg.recoverable)

                else:
                    # End of dependency resolving
                    msg = _("Unable to build transaction")
                    for m in resmsg:
                        msg = "%s %s" % (msg,m)
                    self.log.error(msg, recoverable=False)
            else:
                self.log.debug(_("Successfully built transaction: ret %s, msg %s") % (res, ' '.join(resmsg)))

        except yum.Errors.RepoError, errmsg:
            self.cfg.yumobj.dsCallback = None
            pbar.destroy()

            self.log.error(_("""Errors where encountered while downloading package headers:\n\n%s""" % (errmsg)))

        self.cfg.yumobj.dsCallback = None
        pbar.destroy()


        self.cfg.yumobj.tsInfo.makelists()
        if not len(self.cfg.yumobj.tsInfo.getMembers()) == self.cfg.ts_length_pre_depsolve and self.cfg.kickstart_exact_nevra:
            self.log.warning("%d packages now vs. %d from the kickstart package manifest" % (len(self.cfg.yumobj.tsInfo.getMembers()), self.cfg.ts_length_pre_depsolve))
            self.log.error(_("The package set after dependency resolving does not match the packages selected in the kickstart manifest"), recoverable=False)
            sys.exit(0)

    def check_dependencies(self, style=None):
        if self.cfg.everything_spin: return

        if not style:
            if self.cfg.dependency_resolve_allow_conflicts:
                self.check_dependencies_conflicts()
            else:
                self.check_dependencies_no_conflicts()
        else:
            style()

        self.populate_stats()

    def enable_debuginfo_repositories(self):
        revisor.misc.enable_repositories("debuginfo", self.cfg.yumobj, self.log, self.cfg.arch_list)

    def disable_debuginfo_repositories(self):
        revisor.misc.disable_repositories("debuginfo", self.cfg.yumobj, self.log, self.cfg.arch_list)

    def enable_source_repositories(self):
        revisor.misc.enable_repositories("source", self.cfg.yumobj, self.log, self.cfg.arch_list)

    def disable_source_repositories(self):
        revisor.misc.disable_repositories("source", self.cfg.yumobj, self.log, self.cfg.arch_list)

    def download_debuginfo_packages(self):
        """
            Download debuginfo packages using self.polist
        """
        self.enable_debuginfo_repositories()

        warnings = []

        self.log.debug(_("Creating a list of RPMs to include -debuginfo for"), level=9)
        for po in self.polist:
            debuginforpm = "%s-debuginfo" % po.name
            try:
                debuginfopos = self.cfg.yumobj.pkgSack.searchNevra(name=debuginforpm, epoch=po.epoch, ver=po.version, rel=po.release, arch=po.arch)
                for debuginfopo in debuginfopos:
                    if "debuginfo" in debuginfopo.repoid:
                        if not debuginfopo in self.debuginfopolist:
                            self.debuginfopolist.append(debuginfopo)
                        else:
                            self.log.debug(_("Debuginfo RPM PO already in the list"), level=9)
                    else:
                        self.log.debug(_("Debuginfo RPM found in non-debuginfo repository %s") % (debuginfopo.repoid), level=9)
            except IndexError:
                warnings.append("Cannot find a debuginfo rpm for %s-%s:%s-%s.%s") % (po.name,po.epoch,po.version,po.release,po.arch)

        pbar = self.progress_bar(_("Downloading Debuginfo Packages"))

        revisor.misc.download_packages(self.debuginfopolist, self.log, self.cfg, pbar)

        pbar.destroy()

        self.disable_debuginfo_repositories()

    def download_source_packages(self):
        """Download source packages using self.polist"""

        self.enable_source_repositories()

        self.cfg.plugins.exec_hook("pre_download_source_packages")

        self.log.debug(_("Creating a list of SRPMs"), level=9)
        for po in self.polist:
            srpm = po.returnSimple('sourcerpm').split('.src.rpm')[0]
            if not srpm in self.srpmlist:
                self.srpmlist.append(srpm)

        for srpm in self.srpmlist:
            (sname, sver, srel) = srpm.rsplit('-', 2)
            try:
                srpmpos = self.cfg.yumobj.pkgSack.searchNevra(name=sname, ver=sver, rel=srel, arch='src')
                for srpmpo in srpmpos:
                    if "source" in srpmpo.repoid:
                        if not srpmpo in self.srpmpolist:
                            self.srpmpolist.append(srpmpo)
                        else:
                            self.log.debug(_("Source RPM PO already in the list"), level=9)
                    else:
                        self.log.debug(_("Source RPM found in non-source repository %s") % (srpmpo.repoid), level=9)
            except IndexError:
                self.log.error(_("Error: Cannot find a source rpm for %s") % srpm)

        pbar = self.progress_bar(_("Downloading Source Packages"))

        revisor.misc.download_packages(self.srpmpolist, self.log, self.cfg, pbar)

        pbar.destroy()

        self.cfg.plugins.exec_hook("post_download_source_packages")

        self.disable_source_repositories()

    def download_packages(self):

        self.cfg.plugins.exec_hook("pre_download_packages")

        dlpkgs = map(lambda x: x.po, filter(lambda txmbr:
                                            txmbr.ts_state in ("i", "u"),
                                            self.cfg.yumobj.tsInfo.getMembers()))

        self.polist = dlpkgs

        pbar = self.progress_bar(_("Downloading Packages"))

        revisor.misc.download_packages(self.polist, self.log, self.cfg, pbar)

        pbar.destroy()

        self.cfg.plugins.exec_hook("post_download_packages")

        if self.cfg.getsource:
            self.download_source_packages()

        if self.cfg.getdebuginfo:
            self.download_debuginfo_packages()

    def pkglist_required(self, mode='installation'):

        required_pkgs = []
        suggested_pkgs = []
        allarch_pkgs = []
        onearch_pkgs = []
        packages_to_skip = []

        # These versions do not require you include anything anymore, as they compose
        # against the external repositories used to compose the tree, rather then
        # the tree itself

        if self.cfg.version_from in [ "F9", "F10", "F11", "F12", "F13", "DEVEL" ] and mode == "installation":
            packages_to_add = []
            required_pkgs = ['kernel']
            if self.cfg.architecture not in [ "ppc", "ppc64" ]:
                required_pkgs.extend(['grub'])

            if self.cfg.version_from not in [ "F10", "F11", "F12", "F13", "DEVEL" ]:
                if self.cfg.architecture not in [ "ppc", "ppc64" ]:
                    required_pkgs.extend(['kernel-xen'])

            suggested_pkgs = []
        else:
            required_pkgs = revisor.misc.resolve_pkgs(self.cfg.yumobj, self.cfg.get_package_list(mode, ['require']), log=self.log)
            suggested_pkgs = revisor.misc.resolve_pkgs(self.cfg.yumobj, self.cfg.get_package_list(mode, ['suggest']), log=self.log)
            allarch_pkgs = revisor.misc.resolve_pkgs(self.cfg.yumobj, self.cfg.get_package_list(mode, ['allarch']), log=self.log)
            onearch_pkgs = revisor.misc.resolve_pkgs(self.cfg.yumobj, self.cfg.get_package_list(mode, ['onearch']), log=self.log)

            packages_to_add = required_pkgs + suggested_pkgs + allarch_pkgs + onearch_pkgs
            packages_to_skip = []

        # Make sure that if we are not in respin mode, we add the flexibility of overriding what we select
        # as required, by skipping adding extra or other packages with out list if they are already in the transaction
        # (from kickstart, for those who were wandering)
        for pkg_tuple in self.cfg.yumobj.tsInfo.pkgdict.keys():
            # Make sure we don't delete any user selected options with "best" package magic
            for package in packages_to_add:
                if str(pkg_tuple[0]) == str(package) and not package in allarch_pkgs:
                    self.log.debug(_("Overriding auto package selection with user package selection for %s..." % package), level=4)
                    packages_to_skip.append(package)

        for pkg in required_pkgs:

            try:
                pkgs = self.cfg.yumobj.pkgSack.returnNewestByName(pkg)

                if not pkg in packages_to_skip:
                    if not pkg in allarch_pkgs or pkg in onearch_pkgs:
                        pkgs = self.cfg.yumobj.bestPackagesFromList(pkgs)
                for po in pkgs:
                    self.cfg.yumobj.tsInfo.addInstall(po)
                    self.log.debug(_("Adding required package %s-%s:%s-%s.%s") % (po.name, po.epoch, po.version, po.release, po.arch), level=4)
            except yum.Errors.PackageSackError, e:
                # This list has already been resolved
                self.log.error(_("%s. This is a required package.") % e.value, recoverable=self.cfg.gui_mode)
                return False

        for pkg in suggested_pkgs:
            # If available, add them
            try:
                pkgs = self.cfg.yumobj.pkgSack.returnNewestByName(pkg)
                if not pkg in packages_to_skip:
                    if not pkg in allarch_pkgs or pkg in onearch_pkgs:
                        pkgs = self.cfg.yumobj.bestPackagesFromList(pkgs)
                for po in pkgs:
                    self.cfg.yumobj.tsInfo.addInstall(po)
                    self.log.debug(_("Adding suggested package %s-%s:%s-%s.%s") % (po.name, po.epoch, po.version, po.release, po.arch), level=4)
            except:
                pass

        # From the list of packages that need all architectures
        for pkg in allarch_pkgs:
            if not pkg in packages_to_skip:
                try:
                    pkgs = self.cfg.yumobj.pkgSack.returnNewestByName(pkg)
                    for po in pkgs:
                        self.cfg.yumobj.tsInfo.addInstall(po)
                        self.log.debug(_("Adding all-arch package %s-%s:%s-%s.%s") % (po.name, po.epoch, po.version, po.release, po.arch), level=4)
                except:
                    pass

        #self.added_pkgs = []

        #for package in packages_to_add:
            #if not package in packages_to_skip:
                #self.added_pkgs.append(package)

        #self.log.debug(_("Packages that do not need to be on the media: %s") % str(self.added_pkgs), level=9)

        return True

    def lift_off(self):
        """Do the actual thing. Dance the salsa."""
        self.srpmlist = []
        self.debuginfopolist = []
        self.srpmpolist = []
        self.polist = []

        groupList = self.cfg.ksobj._get("packages","groupList")
        packageList = self.cfg.ksobj._get("packages","packageList")
        excludedList = self.cfg.ksobj._get("packages","excludedList")

        if self.cfg.media_installation:
            ignore_list = self.cfg.get_package_list(['installation'],['allarch'],['all',self.cfg.architecture],['all',self.cfg.version_from])

            if (self.cfg.kickstart_manifest and not self.cfg.i_did_all_this) or not self.cfg.gui_mode:
                self.pkglist_from_ksdata(groupList=groupList, packageList=packageList, excludedList=excludedList, ignore_list=ignore_list)

            if self.pkglist_required():
                self.check_dependencies()
                self.report_sizes()
                self.download_packages()
                self.buildInstallationMedia()
            else:
                self.log.error(_("Did not succeed in adding in all required packages"), recoverable=False)

#            # If we've done installation media, we want to remove all packages we added
#            # as required packages and that were not in the original list
#            for pkg in self.cfg.yumobj.tsInfo.pkgdict.keys():
#                if not pkg in self.cfg.pkglist_selected_tups:
#                    self.log.debug(_("Removing %s from tsInfo") % str(pkg))
#                    self.cfg.yumobj.tsInfo.remove(pkg)
#                else:
#                    self.log.debug(_("Not removing %s from tsInfo") % str(pkg))

        if self.cfg.media_live:
            ignore_list = self.cfg.get_package_list(['live'],['allarch'],['all',self.cfg.architecture],['all',self.cfg.version_from])
            if self.cfg.gui_mode:
                if not self.cfg.i_did_all_this:
                    self.pkglist_from_ksdata(groupList=groupList, packageList=packageList, excludedList=excludedList, ignore_list=ignore_list)
            else:
                self.pkglist_from_ksdata(groupList=groupList, packageList=packageList, excludedList=excludedList, ignore_list=ignore_list)
#            self.check_dependencies(style=self.check_dependencies_no_conflicts)

            if self.pkglist_required(mode='live'):
                self.check_dependencies(style=self.check_dependencies_no_conflicts)
                self.report_sizes()
                self.download_packages()
                self.buildLiveMedia()
            else:
                self.log.error(_("Did not succeed in adding in all required packages"))

        if self.cfg.gui_mode:
            # Show Finshed Screen
            self.gui.displayFinished()

    def populate_stats(self):
        """ Populate the stats displayed on the ready screen, based on our yum transaction. """
        pbar = self.progress_bar(_("Populating statistics"))
        pkgs = self.cfg.yumobj.tsInfo.getMembers()
        self.cfg.payload_packages = len(pkgs)

        archivesize = 0
        installedsize = 0
        packagesize =0

        current = 0.0
        total = float(len(pkgs))

        for pkg in pkgs:
            current += 1.0
            try:
                archivesize += pkg.po.archivesize
            except KeyError, e:
                self.log.debug(_("Package %s-%s:%s-%s.%s does not seem to have a archivesize header") % (pkg.po.name, pkg.po.epoch, pkg.po.version, pkg.po.release, pkg.po.arch))
            except AttributeError, e:
#                self.log.debug(_("No attribute archivesize for package %s") % pkg.po.name)
                archivesize += int(pkg.po.returnSimple('archivesize'))

            try:
                installedsize += pkg.po.installedsize
            except KeyError, e:
                self.log.debug(_("Package %s-%s:%s-%s.%s does not seem to have a installedsize header") % (pkg.po.name, pkg.po.epoch, pkg.po.version, pkg.po.release, pkg.po.arch))
            except AttributeError, e:
#                self.log.debug(_("No attribute installedsize for package %s") % pkg.po.name)
                installedsize += int(pkg.po.returnSimple('installedsize'))

            try:
                packagesize += pkg.po.packagesize
            except KeyError, e:
                self.log.debug(_("Package %s-%s:%s-%s.%s does not seem to have a packagesize header") % (pkg.po.name, pkg.po.epoch, pkg.po.version, pkg.po.release, pkg.po.arch))
            except AttributeError, e:
#                self.log.debug(_("No attribute packagesize for package %s") % pkg.po.name)
                packagesize += int(pkg.po.returnSimple('packagesize'))

            pbar.set_fraction(total/current)

        self.cfg.payload_installmedia = packagesize
        if archivesize > installedsize:
            self.cfg.payload_livemedia = archivesize
        elif installedsize > archivesize:
            self.cfg.payload_livemedia = installedsize
        else:
            self.cfg.payload_livemedia = installedsize

        self.log.debug(_("Total size of all packages (archivesize): %s %s") % revisor.misc.size_me(archivesize), level=4)
        self.log.debug(_("Total size of all packages, (installedsize): %s %s") % revisor.misc.size_me(installedsize), level=4)
        self.log.debug(_("Total size of all packages, (packagesize): %s %s") % revisor.misc.size_me(packagesize), level=4)

        pbar.destroy()

    def report_sizes(self):
        """Of all packages in the transaction report the installedsize and packagesize, sorted"""

        if not self.cfg.report_sizes:
            return

        list_installedsize = []
        list_packagesize = []
        list_archivesize = []

        pkgs = self.cfg.yumobj.tsInfo.getMembers()
        for pkg in pkgs:
            if hasattr(pkg.po,"installedsize"):
                list_installedsize.append("%d %s-%s-%s.%s" % (pkg.po.installedsize,pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))
            else:
                list_installedsize.append("unknown %s-%s-%s.%s" % (pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))

            if hasattr(pkg.po,"packagesize"):
                list_packagesize.append("%d %s-%s-%s.%s" % (pkg.po.packagesize,pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))
            else:
                list_packagesize.append("unknown %s-%s-%s.%s" % (pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))

            if hasattr(pkg.po,"archivesize"):
                list_archivesize.append("%d %s-%s-%s.%s" % (pkg.po.packagesize,pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))
            else:
                list_archivesize.append("unknown %s-%s-%s.%s" % (pkg.po.name,pkg.po.version,pkg.po.release,pkg.po.arch))

        list_installedsize = self.numeric_rev_sort(list_installedsize)
        list_packagesize = self.numeric_rev_sort(list_packagesize)
        list_archivesize = self.numeric_rev_sort(list_archivesize)

        print "== " + _("Report of the %d most space consuming packages") % self.cfg.report_sizes_length + " =="

        print "\nInstall Sizes (RPM installedsize header):\n"
        i = 0
        for line in list_installedsize:
            (size,name) = line.split(' ')
            (size,unit) = revisor.misc.size_me(size)
            print "%s %s for %s" % (size,unit,name)
            i += 1
            if i > self.cfg.report_sizes_length:
                break

        print "\nPackage (RPM) Sizes (RPM packagesize header):\n"
        i = 0
        for line in list_packagesize:
            (size,name) = line.split(' ')
            (size,unit) = revisor.misc.size_me(size)
            print "%s %s for %s" % (size,unit,name)
            i += 1
            if i > self.cfg.report_sizes_length:
                break

        print "\nPackage (RPM) Sizes (RPM archivesize header):\n"
        i = 0
        for line in list_archivesize:
            (size,name) = line.split(' ')
            (size,unit) = revisor.misc.size_me(size)
            print "%s %s for %s" % (size,unit,name)
            i += 1
            if i > self.cfg.report_sizes_length:
                break

    def numeric_rev_sort(self, alist):
        indices = map(self._generate_index, alist)
        decorated = zip(indices, alist)
        decorated.sort()
        decorated.reverse()
        return [ item for index, item in decorated ]

    def _generate_index(self, str):
        """
        Splits a string into alpha and numeric elements, which
        is used as an index for sorting"
        """
        #
        # the index is built progressively
        # using the _append function
        #
        index = []
        def _append(fragment, alist=index):
            if fragment.isdigit(): fragment = int(fragment)
            alist.append(fragment)

        # initialize loop
        prev_isdigit = str[0].isdigit()
        current_fragment = ''
        # group a string into digit and non-digit parts
        for char in str:
            curr_isdigit = char.isdigit()
            if curr_isdigit == prev_isdigit:
                current_fragment += char
            else:
                _append(current_fragment)
                current_fragment = char
                prev_isdigit = curr_isdigit
        _append(current_fragment)
        return tuple(index)

    def buildInstallationMedia(self):
        from revisor import pungi

        self.plugins.exec_hook("pre_compose_media_installation")

        # Actually do work.
        if not self.cfg.architecture == 'source':

            # init some
            mypungi = pungi.RevisorPungi(self)

            try:
                os.makedirs(os.path.join(mypungi.destdir,
                                         self.cfg.version,
                                         self.cfg.model,
                                         self.cfg.architecture))
            except:
                pass

            pbar = self.progress_bar(_("Linking in binary packages"))

            pkgdir = os.path.join(  mypungi.destdir,
                                    self.cfg.version,
                                    self.cfg.model,
                                    self.cfg.architecture,
                                    "os",
                                    self.cfg.product_path)

            revisor.misc.link_pkgs(self.polist, pkgdir, copy_local=self.cfg.copy_local, pbar=pbar, log=self.log)
            pbar.destroy()

            if self.cfg.getsource:
                pbar = self.progress_bar(_("Linking in source packages"))

                pkgdir_src = os.path.join(  mypungi.destdir,
                                            self.cfg.version,
                                            self.cfg.model,
                                            "source",
                                            "SRPMS")
                revisor.misc.link_pkgs(self.srpmpolist, pkgdir_src, copy_local=self.cfg.copy_local, pbar=pbar, log=self.log)

                pbar.destroy()

            if self.cfg.getdebuginfo:
                pbar = self.progress_bar(_("Linking in debuginfo packages"))

                pkgdir_debuginfo = os.path.join(mypungi.destdir,
                                                self.cfg.version,
                                                self.cfg.model,
                                                self.cfg.architecture,
                                                "debug")

                revisor.misc.link_pkgs(self.debuginfopolist, pkgdir_debuginfo, copy_local=self.cfg.copy_local, pbar=pbar, log=self.log)

                pbar.destroy()

            pbar = self.progress_bar(_("Creating Repository Information"), callback=True)
            pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)

            database = True
            if os.access("/etc/centos-release", os.R_OK):
                database = False
            elif os.access("/etc/redhat-release", os.R_OK) and not os.access("/etc/fedora-release", os.R_OK):
                database = False

            mypungi.doCreateRepo(database=database,callback=pungicallback)
            pbar.destroy()

            if self.cfg.getsource:
                pbar = self.progress_bar(_("Source Repo Information"), callback=True)
                pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)

                database = True
                if os.access("/etc/centos-release", os.R_OK):
                    database = False
                elif os.access("/etc/redhat-release", os.R_OK) and not os.access("/etc/fedora-release", os.R_OK):
                    database = False

                mypungi.doCreateRepo(database=database,basedir=pkgdir_src,callback=pungicallback,comps=False,repoview=False)
                pbar.destroy()

            if self.cfg.getdebuginfo:
                pbar = self.progress_bar(_("Debuginfo Repo Information"), callback=True)
                pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)

                database = True
                if os.access("/etc/centos-release", os.R_OK):
                    database = False
                elif os.access("/etc/redhat-release", os.R_OK) and not os.access("/etc/fedora-release", os.R_OK):
                    database = False

                mypungi.doCreateRepo(database=database,basedir=pkgdir_debuginfo,callback=pungicallback,comps=False,repoview=False)
                pbar.destroy()

            self.plugins.exec_hook('pre_exec_buildinstall')

            # FIXME: Optionally recompose installer images
            pbar = self.progress_bar(_("Building Installation Images"))

            if self.cfg.architecture in [ "ppc", "ppc64" ]:
                files = [ "images/boot.iso", "ppc/ppc32/vmlinuz", "ppc/ppc64/vmlinuz" ]
            else:
                files = [ "isolinux/isolinux.cfg", "isolinux/isolinux.bin", "isolinux/vmlinuz", "isolinux/initrd.img", "images/boot.iso" ]

            run_buildinstall = False
            for file in files:
                if not os.access("%s/revisor-install/%s/%s/%s/os/%s" % (self.cfg.working_directory, self.cfg.version, self.cfg.model, self.cfg.architecture, file), os.R_OK):

                    run_buildinstall = True

            if run_buildinstall:
                pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
                mypungi.doBuildinstall(callback=pungicallback)
            else:
                self.log.debug(_("Using already existing installer images"), level=4)

            pbar.destroy()

            # This doesn't work, doh!
#            # Nuke stage2.img
#            if self.cfg.install_nogr:
#                try:
#                    os.unlink(os.path.join(self.cfg.working_directory, "revisor-install", self.cfg.version, self.cfg.model, self.cfg.architecture, "os", "images", "stage2.img"))
#                except:
#                    pass

            self.plugins.exec_hook('post_exec_buildinstall')

            pbar = self.progress_bar(_("Linking in release notes"))
            pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
            mypungi.doGetRelnotes(callback=pungicallback)
            pbar.destroy()

            tree_location = '%s/os' % os.path.join(mypungi.destdir,
                                                                    self.cfg.version,
                                                                    self.cfg.model,
                                                                    self.cfg.architecture)

            # Add updates.img into the tree
            if self.cfg.updates_img:
                self.log.debug(_("Copying updates.img from %s to %s") % (self.cfg.updates_img, os.path.join(tree_location, "images/updates.img")), level=8)
                shutil.copy(revisor.misc.get_file(self.cfg.updates_img), os.path.join(tree_location, 'images/updates.img'))

            # FIXME: Add linux updates to isolinux/isolinux.cfg as well

            if not self.cfg.copy_dir == "":
                if os.access(self.cfg.copy_dir, os.R_OK):
                    mypungi.doCopyDir(copy_dir=self.cfg.copy_dir)
                else:
                    self.log.warning(_("copy_dir '%s' not accessible") % self.cfg.copy_dir)

# Relevant code to USB Installation Media
# Has the size of the tree compared to the size of the USB Thumb Drive

            calc_size_str = subprocess.Popen(['/usr/bin/du',
                                            '-sbLl',
                                            tree_location],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
            calc_size_str = calc_size_str.split()[0]
            self.cfg.mediatypes["unified"]["size"] = int(calc_size_str) + 1
            self.log.debug(_("Size of the installation tree is %s MB") % str(int(calc_size_str) / 1024 / 1024))

            override_retval = ""

            # So, what would the number of discs be?
            for num in self.cfg.mediatypes["index"].keys():
                mediatype = self.cfg.mediatypes["index"][num]

                # Do we even compose this type?
                exec("retval = %s" % self.cfg.mediatypes[mediatype]["compose"])

                # If not, we want to just continue on to the next media
                if not retval:
                    self.cfg.mediatypes[mediatype]["compose"] = False
                    continue

                # Apparently we do compose this media type, but has a previous media
                # type been set to compose, and does it have multiple discs?
                # Because if it hasn't, there's no need to compose a DVD of whatever
                # fits on a single CD, for example.
                if not override_retval == "hihi":
                    self.cfg.mediatypes[mediatype]["compose"] = retval
                else:
                    self.cfg.mediatypes[mediatype]["compose"] = False

                if mediatype == "unified":
                    self.cfg.mediatypes[mediatype]["discs"] = 1
                elif self.cfg.mediatypes[mediatype]["size"] > int(calc_size_str):
                    self.cfg.mediatypes[mediatype]["discs"] = 1
                else:
                    self.cfg.mediatypes[mediatype]["discs"] = int(math.ceil(self.cfg.mediatypes["unified"]["size"] / self.cfg.mediatypes[mediatype]["size"])) + 1

                if self.cfg.mediatypes[mediatype]["discs"] > 1:
                    self.cfg.do_packageorder = True
                else:
                    # Heej if my discnumber is one the rest doesn't have to compose!
                    override_retval = "hihi"

            # Now, we know everything!
            # And we lived happily ever after
            if self.cfg.gui_mode:
                self.gui.BuildMedia.extend_task_list()

# FIXME
# This runs without progress or anything
            if self.cfg.do_packageorder and self.cfg.pkgorder_file == "":
                import pkgorder

                # On EL5, the yum cache is placed under the installroot
                # That makes our lives difficult, hihi
                # So, make sure that if we're on el_linux, the repository gets
                # bind mounted and configured appropriately

                pbar = self.progress_bar(_("Running pkgorder"))

                ds = pkgorder.PackageOrderer(self)

                try:
                    os.makedirs(os.path.join(self.cfg.yumobj.cachedir,"anaconda","headers"))
                except:
                    pass

                ds.createConfig()

                ds.setup()

                pbar.set_fraction(1.0/28.0)

                #ds.printMatchingPkgs("kernel*")
                #ds.printMatchingPkgs("iscsi-*")
                #ds.printMatchingPkgs("*firmware*")

                ds.addPackages([ "kernel*", "iscsi-*", "mkinitrd", "mdadm", "*firmware*" ])

                ds.addPackages(['authconfig', 'chkconfig', 'mkinitrd', 'rhpl', 'system-config-firewall-tui'])

                pbar.set_fraction(2.0/38.0)

                if self.cfg.version_from == "F7":
                    # Here is where we add groups
                    ds.addGroups(["core", "base", "text-internet"])

                    pbar.set_fraction(3.0/38.0)

                    ds.addGroups(["base-x", "dial-up",
                                    "graphical-internet", "editors",
                                    "graphics", "gnome-desktop", "sound-and-video",
                                    "printing"])

                    pbar.set_fraction(11.0/38.0)

                    ds.addGroups(["office", "engineering-and-scientific",
                                "authoring-and-publishing", "games"])

                    pbar.set_fraction(15.0/38.0)

                    ds.addGroups(["web-server", "ftp-server", "sql-server",
                                "mysql", "server-cfg", "dns-server",
                                "smb-server", "admin-tools"])

                    pbar.set_fraction(23.0/38.0)

                    ds.addGroups(["kde-desktop", "development-tools", "development-libs",
                                "gnome-software-development", "eclipse",
                                "x-software-development",
                                "java-development", "kde-software-development",
                                "mail-server", "network-server", "legacy-network-server"])

                elif self.cfg.version_from in [ "F8", "F9", "F10", "F11", "F12", "F13", "DEVEL" ]:
                    # Here is where we add groups
                    groups_default = []
                    groups_nondefault = []
                    groups_nondefault_support = []

                    groupList = [grp.name for grp in self.cfg.ksobj._get("packages","groupList")]

                    self.log.debug(_("Running with grouplist: %r") % groupList, level=9)

                    packageList = self.cfg.ksobj._get("packages","packageList")
                    self.log.debug(_("Running with packagelist: %r") % packageList, level=9)

                    pbar.current = 0.0

                    num_groups = len(groupList)
                    pbar.total = float(num_groups)

                    self.log.debug(_("Appending group core and base"), level=7)

                    ds.addGroups(["core"])
                    ds.addGroups(["base"])

                    for group in self.cfg.yumobj.comps.groups:
                        # Do not do this because the installer still has all the groups available
                        #if not group.groupid in groupList:
                            #continue

                        # These groups have already been added
                        if group.name in [ 'core', 'base' ]:
                            continue

                        if hasattr(group,"default"):
                            if bool(group.default):
                                groups_default.append(group.groupid)
                            elif group.groupid.endswith("-support"):
                                groups_nondefault_support.append(group.groupid)
                            else:
                                groups_nondefault.append(group.groupid)
                        else:
                            groups_nondefault.append(group.groupid)

                    self.log.debug(_("Appending default groups %r") % groups_default, level=7)
                    ds.addGroups(groups_default)
                    pbar.current += float(len(groups_default))
                    pbar.set_fraction(pbar.current/pbar.total)

                    # Now, make sure that any packages listed in the kickstart end
                    # up on the first possible disc as well. But not when composing
                    # the everything spin, please
                    if not self.cfg.everything_spin:
                        ds.addPackages(packageList)

                    for group in groups_nondefault:
                        # Do not do this because the installer still has all the groups available
                        #if group not in groupList:
                            #continue

                        self.log.debug(_("Appending non-default group %s") % group, level=7)
                        ds.addGroups([group])
                        pbar.current += 1.0
                        pbar.set_fraction(pbar.current/pbar.total)

                    for group in groups_nondefault_support:
                        # Do not do this because the installer still has all the groups available
                        #if group not in groupList:
                            #continue

                        self.log.debug(_("Appending non-default support group %s") % group, level=7)
                        # Speed things up!
                        #ds.addGroups([group])
                        pbar.current += 1.0
                        pbar.set_fraction(pbar.current/pbar.total)

                    # Everthing else but kernels
                    for po in ds.pkgSack.returnPackages():
                        ds.printMatchingPkgs(os.path.basename(po.localPkg()))

                    pbar.destroy()

                else:
                    # These are default
                    ds.addGroups(["core", "base", "base-x"])

                    pbar.set_fraction(3.0/38.0)

                    ds.addGroups(["dial-up", "text-internet", "editors", "fonts", "games"])

                    pbar.set_fraction(8.0/38.0)

                    ds.addGroups(["gnome-desktop", "graphical-internet"])

                    pbar.set_fraction(10.0/38.0)

                    ds.addGroups(["hardware-support", "java", "office", "graphics", "printing"])

                    pbar.set_fraction(15.0/38.0)

                    ds.addGroups(["legacy-fonts", "sound-and-video"])

                    pbar.set_fraction(17.0/38.0)

                    ds.addGroups(["engineering-and-scientific",
                                "authoring-and-publishing",
                                "kde-desktop"])

                    pbar.set_fraction(20.0/38.0)

                    ds.addGroups(["web-server", "ftp-server", "sql-server",
                                "mysql", "server-cfg", "dns-server",
                                "smb-server", "admin-tools"])

                    pbar.set_fraction(28.0/38.0)

                    ds.addGroups(["development-tools", "development-libs",
                                "gnome-software-development", "eclipse",
                                "x-software-development",
                                "java-development", "kde-software-development",
                                "mail-server", "network-server", "legacy-network-server"])

                    pbar.set_fraction(34.0/38.0)

                    ds.addGroups(["news-server", "legacy-software-development"])

                # Everthing else but kernels
                for po in ds.pkgSack.returnPackages():
                    ds.printMatchingPkgs(os.path.basename(po.localPkg()))

                pbar.destroy()

#                if el_linux:
#                    rc = subprocess.call(["/bin/umount", dst])

            elif self.cfg.do_packageorder and os.access(self.cfg.pkgorder_file, os.R_OK):
                self.log.debug(_("Not running package ordering, using file %s instead") % self.cfg.pkgorder_file, level=9)
            else:
                self.log.debug(_("Not running package ordering"), level=9)

            if not self.cfg.kickstart_save == "":
                # FIXME: Maybe we want to offer in destdir dumping along with absolute dumping?
                # For now, it's just "give us a location to save to"
                f = open(self.cfg.kickstart_save, "w")
                f.write(self.cfg.ksobj.__str__())
                f.close()

            if self.cfg.kickstart_include:
# FIXME
                # This needs some more work because the kickstart file may have been
                # generated during our run, partially modified during our run, and may not have
                # been used at all
                if self.cfg.use_kickstart_file:
                    shutil.copyfile(self.cfg.kickstart_file, os.path.join(mypungi.topdir,"ks.cfg"))
                else:
                    f = open(os.path.join(mypungi.topdir,"ks.cfg"), "w")
                    f.write(self.cfg.ksobj.__str__())
                    f.close()

                if self.cfg.kickstart_default:
                    f = open(os.path.join(mypungi.topdir,"isolinux","isolinux.cfg"),"rw+")
                    buf = f.read()
                    # Replace an existent "label ks" because we want to append our own
                    buf = buf.replace("label ks\n  kernel vmlinuz\n  append ks initrd=initrd.img\n","")
#                    buf = buf.replace("#prompt 1","prompt 1")
                    buf = buf.replace("menu default\n","")
                    buf = buf.replace("default linux","default ks")
#                    buf = buf.replace("default vesamenu.c32","default ks")
                    f.seek(0)
                    f.write(buf)
                    f.write("label ks\n  menu label " + _("^Install using kickstart") + "\n  menu default\n  kernel vmlinuz\n  append initrd=initrd.img ks=cdrom:/ks.cfg %s\n" % self.cfg.im_append)
                    f.close()

# Do some really neat routine here
            for num in self.cfg.mediatypes["index"].keys():
                mediatype = self.cfg.mediatypes["index"][num]

                discs = self.cfg.mediatypes[mediatype]["discs"]
                size = self.cfg.mediatypes[mediatype]["size"]
                discdir = self.cfg.mediatypes[mediatype]["discdir"]
                label = self.cfg.mediatypes[mediatype]["label"]

                if self.cfg.mediatypes[mediatype]["compose"]:
                    os.symlink(mypungi.topdir,"%s-%s" % (mypungi.topdir, discdir))

                    for i in range(2, discs+1):
                        try:
                            os.makedirs("%s-%s-disc%d" % (mypungi.topdir, discdir, i))
                        except:
                            pass

                    if discs > 1:
                        # Split Tree
                        pbar = self.progress_bar(_("Splitting Build Tree (%s)") % label)
                        pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
                        mypungi.doSplittree(media_size=size,discdir=discdir,callback=pungicallback)
                        pbar.destroy()

                        # Split repo
                        pbar = self.progress_bar(_("Splitting Repository (%s)") % label)
                        pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
                        mypungi.doCreateSplitrepo(discdir=discdir,callback=pungicallback)
                        pbar.destroy()

                    # Now that we're done splitting the tree, re-init some numbers (cause the number of discs may have changed)
                    discs = self.cfg.mediatypes[mediatype]["discs"]

# Not sure this fixes anything
#                    os.symlink(os.path.join(mypungi.topdir,"repodata"), os.path.join(mypungi.topdir,self.cfg.product_path,"repodata"))

                    # Create ISOs
                    if discs > 1:
                        for disc in range(1, discs+1):
                            pbar = self.progress_bar(_("Creating %s ISO Image #%d") % (label, disc))
                            pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
                            mypungi.doCreateIso(mediatype=mediatype, disc=disc, callback=pungicallback)
                            pbar.destroy()
                    else:
                        pbar = self.progress_bar(_("Creating %s ISO Image") % label)
                        pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
                        mypungi.ALL_workaround()
                        mypungi.doCreateIso(mediatype=mediatype, callback=pungicallback)
                        pbar.destroy()

# Insert code to USB Installation Media
# Compose the USB Installation Media here

            if len(self.cfg.built_iso_images) > 0:

                if not self.cfg.skip_implantisomd5:
                    # For all images but source images; implant the md5 into the ISO for the media check
                    # FIXME: Well, it seems we don't deal with source images here.
                    pbar = self.progress_bar(_("Implanting MD5 into ISO Images"))
                    total = float(len(self.cfg.built_iso_images))
                    cur = 0.0
                    for built_image in self.cfg.built_iso_images:
                        isofile = built_image["location"]
                        pbar.set_markup(isofile)
                        #mediatype = built_image["mediatype"]
                        #if not mediatype == 'source':
                        self.log.debug(_("Implanting md5 into ISO Image: %s" % (isofile)))
                        if os.access("/usr/lib/anaconda-runtime/implantisomd5", os.R_OK):
                            self.run_command(['/usr/lib/anaconda-runtime/implantisomd5', isofile])
                        elif os.access("/usr/bin/implantisomd5", os.R_OK):
                            self.run_command(['/usr/bin/implantisomd5', isofile])
                        else:
                            self.log.error(_("Cannot implant ISO md5sum"), recoverable=True)

                        cur += 1.0
                        pbar.set_fraction(cur/total)
                    pbar.destroy()

                if not self.cfg.skip_sha1sum:
                    # Do some SHA1SUMMONING
                    pbar = self.progress_bar(_("Creating SHA1SUMs for Images"))
                    total = float(len(self.cfg.built_iso_images))
                    cur = 0.0
                    for built_image in self.cfg.built_iso_images:
                        isofile = os.path.basename(built_image["location"])
                        pbar.set_markup(isofile)
                        isodir = os.path.dirname(built_image["location"])
                        # shove the sha1sum into a file
                        sha1file = open(os.path.join(isodir,"SHA1SUM"), 'a')
                        self.run_command(['/usr/bin/sha1sum', isofile], rundir=isodir, output=sha1file)
                        sha1file.close()
                        cur += 1.0
                        pbar.set_fraction(cur/total)
                    pbar.destroy()

        if self.cfg.media_utility_rescue:
            pbar = self.progress_bar(_("Creating Rescue ISO Image"))
            pungicallback = revisor.progress.PungiCallback(pbar, pungi=mypungi, cfg=self.cfg)
            mypungi.create_rescue_disk(callback=pungicallback)
            pbar.destroy()

        # Does not work yet because anaconda doesn't allow installations from expanded trees on a hard drive
        if self.cfg.media_installation_usb:
            pbar = self.progress_bar(_("Creating USB Key Installer"))
            usb_file = os.path.join(self.cfg.working_directory,"%s-%s-%s-USB.img" % (self.cfg.iso_basename, self.cfg.version, self.cfg.architecture))
            self.run_command(["qemu-img", "create", usb_file, self.cfg.usb_size])
            self.run_command(["mkdosfs", usb_file])

            usb_mount_location = os.path.join(self.cfg.working_directory, "revisor-usb")

            # Maybe make the directory
            try:
                os.makedirs(usb_mount_location)
            except:
                pass

            usb_mount = imgcreate.fs.LoopbackMount(usb_file, usb_mount_location)
            usb_mount.mount()

            # Copy files over
            #shutil.copytree(mypungi.topdir, usb_mount_location)
            src = mypungi.topdir
            dst = usb_mount_location

            names = os.listdir(src)
            for name in names:
                srcname = os.path.join(src, name)
                dstname = os.path.join(dst, name)
                if os.path.isdir(srcname):
                    shutil.copytree(srcname, dstname)
                else:
                    shutil.copy2(srcname, dstname)

            # Modify isolinux.cfg
            # FIXME: Some action here
            # Move it to syslinux.cfg
            shutil.move(os.path.join(usb_mount_location,"isolinux","isolinux.cfg"),os.path.join(usb_mount_location,"isolinux","syslinux.cfg"))
            # Move isolinux/ to syslinux/
            shutil.move(os.path.join(usb_mount_location,"isolinux"),os.path.join(usb_mount_location,"syslinux"))
            # Unmount disk
            usb_mount.unmount()

            # Run syslinux
            self.run_command(["syslinux", "-d", "syslinux", usb_file])

            shutil.move(usb_file,os.path.join(self.cfg.destination_directory, "usb"))

        self.cfg.plugins.exec_hook('post_compose_media_installation')

        if self.cfg.getsource:
            tree_dst = os.path.join(self.cfg.destination_directory,"os","source")
            tree_src = os.path.join(mypungi.destdir,self.cfg.version,self.cfg.model,"source")

            # Find the number of files in tree_src for a progress bar
            num_files = 0
            for root, dirs, files in os.walk(tree_src):
                num_files += len(files)

            try:
                if self.cfg.copy_local:
                    self.log.debug(_("Copying %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                    shutil.copytree(tree_src,tree_dst)
                else:
                    try:
                        self.log.debug(_("Moving %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                        shutil.move(tree_src,tree_dst)
                    except Exception, e:
                        self.log.error(_("Moving of the source tree failed (trying copy):\n\n%s") % '\n'.join(e), recoverable=True)
                        shutil.copytree(tree_src,tree_dst)
            except Exception, e:
                self.log.error(_("Copying of the source tree failed:\n\n%s") % '\n'.join(e), recoverable=True)

        if self.cfg.getdebuginfo:
            tree_dst = os.path.join(self.cfg.destination_directory,"debug")
            tree_src = os.path.join(mypungi.destdir,self.cfg.version,self.cfg.model,self.cfg.architecture,"debug")

            # Find the number of files in tree_src for a progress bar
            num_files = 0
            for root, dirs, files in os.walk(tree_src):
                num_files += len(files)

            try:
                if self.cfg.copy_local:
                    self.log.debug(_("Copying %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                    shutil.copytree(tree_src,tree_dst)
                else:
                    try:
                        self.log.debug(_("Moving %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                        shutil.move(tree_src,tree_dst)
                    except Exception, e:
                        self.log.error(_("Moving of the source tree failed (trying copy):\n\n%s") % '\n'.join(e), recoverable=True)
                        shutil.copytree(tree_src,tree_dst)
            except Exception, e:
                self.log.error(_("Copying of the source tree failed:\n\n%s") % '\n'.join(e), recoverable=True)

        if self.cfg.media_installation_tree:
            tree_dst = os.path.join(self.cfg.destination_directory,"os",self.cfg.architecture)
            tree_src = mypungi.topdir

            # Find the number of files in tree_src for a progress bar
            num_files = 0
            for root, dirs, files in os.walk(tree_src):
                num_files += len(files)

            try:
                if self.cfg.copy_local:
                    self.log.debug(_("Copying %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                    shutil.copytree(tree_src,tree_dst)
                else:
                    try:
                        self.log.debug(_("Moving %s to %s (%d files)") % (tree_src,tree_dst,num_files), level=1)
                        shutil.move(tree_src,tree_dst)
                    except Exception, e:
                        self.log.error(_("Moving of the installation tree failed (trying copy):\n\n%s") % '\n'.join(e), recoverable=True)
                        shutil.copytree(tree_src,tree_dst)
            except Exception, e:
                self.log.error(_("Copying of the installation tree failed:\n\n%s") % '\n'.join(e), recoverable=True)


    def buildLiveMedia(self):
        # Get our object from pilgrim
        pseudo_creator = revisor.image.RevisorImageCreator(self, self.cfg.architecture)

        liveImage = pseudo_creator.imagecreator

        pbar = self.progress_bar(_("Creating ext3 filesystem"))

        liveImage.mount(self.cfg.lm_base_on)
        pbar.destroy()

        liveImage.install()

        pbar = self.progress_bar(_("Configuring System"))
        try:
            liveImage.configure()
        except IOError, e:
            if e.errno == 2:
                pass
            else:
                raise IOError, e

        if self.cfg.lm_user_configuration:
            useradd = ['/usr/sbin/useradd']
            if len(self.cfg.lm_user_comment) > 0:
                useradd.extend(['-c', self.cfg.lm_user_comment])
            useradd.append(self.cfg.lm_user_name)
            self.run_command(useradd, preexec_fn=liveImage._instroot)

            if self.cfg.lm_user_auto_login:
                f = open("%s%s" % (liveImage._instroot,"/etc/gdm/custom.conf"),"a")
                f.write(self.cfg.gdm_auto_login % {'username': self.cfg.lm_user_name})
                f.close()

            if self.cfg.lm_user_wheel:
                self.run_command(["/usr/bin/gpasswd", "-a", self.cfg.lm_user_name, "wheel"], preexec_fn=liveImage._instroot)

                if self.cfg.lm_wheel_sudo_no_passwd:
                    self.run_command(["sed", "-i", "-e", "'s/^#\s*%wheel.*NOPASSWD/%wheel ALL=(ALL) NOPASSWD: ALL/g'", "/etc/sudoers"], preexec_fn=liveImage._instroot)

        pbar.destroy()

        if self.cfg.lm_chroot_shell:
            print "Launching shell. Exit to continue."
            print "----------------------------------"
            liveImage.launch_shell()

        if self.cfg.copy_dir:
            self.log.info(_("Copying copy_dir %s to install_root %s") % (self.cfg.copy_dir,liveImage._instroot))
            # So what is the destination directory?
            src_dir = self.cfg.copy_dir
            dst_dir = "%s/%s"

            for root, dirs, files in os.walk(src_dir):
                real_dst = dst_dir % (liveImage._instroot, root.replace(src_dir,''))

                if not os.access(real_dst, os.R_OK):
                    self.log.debug(_("Creating %s") % real_dst)
                    os.makedirs(real_dst)

                for file in files:
                    self.log.debug(_("Copying %s to %s") % (os.path.join(root,file), os.path.join(real_dst,file)))
                    shutil.copyfile(os.path.join(root,file), os.path.join(real_dst,file))

        liveImage.unmount()
        liveImage.package(destdir=os.path.join(self.cfg.destination_directory,"live"))

        if self.cfg.getbinary:
            # Link the localPkg() result into the build tree
            pbar = self.progress_bar(_("Linking in binary packages"))
            pkgdir = os.path.join(  self.cfg.destination_directory,
                                    "os",
                                    self.cfg.architecture,
                                    self.cfg.product_path)

            revisor.misc.link_pkgs(self.polist, pkgdir, copy_local=self.cfg.copy_local, pbar=pbar, log=self.log)

            pbar.destroy()

        if self.cfg.getsource:
            pbar = self.progress_bar(_("Linking in Source packages"))
            pkgdir_src = os.path.join(  self.cfg.destination_directory,
                                        "os",
                                        "source",
                                        "SRPMS")

            self.enable_source_repositories()

            revisor.misc.link_pkgs(self.srpmpolist, pkgdir_src, copy_local=self.cfg.copy_local, pbar=pbar, log=self.log)

            self.disable_source_repositories()

        pbar.destroy()

        isoname = "%s-%s-Live-%s.iso" % (self.cfg.iso_basename, self.cfg.version, self.cfg.architecture)

        sha1file = open(os.path.join(self.cfg.destination_directory,"live","SHA1SUM"), 'w')
        self.run_command(['/usr/bin/sha1sum', '-b', isoname], rundir=os.path.join(self.cfg.destination_directory,"live"), output=sha1file)
        sha1file.close()

    def set_run_command_callback(self, callback=None):
        self.run_command_callback = callback

    def run_command(self, command, rundir=None, output=subprocess.PIPE, error=subprocess.STDOUT, inshell=False, env=None, callback=None, preexec_fn=None):
        """Run a command and log the output."""

        if rundir == None:
            rundir = os.path.join(self.cfg.working_directory,"revisor-rundir")
        self.log.debug(_("Setting rundir to %s") % rundir)

        if not os.access(rundir, os.R_OK):
            try:
                os.makedirs(rundir)
            except:
                self.log.debug(_("Directory %s could not be created. Aborting"), recoverable=False)

        self.log.debug(_("Running command: %s") % ' '.join(command))
        self.log.debug(_("Extra information: %s %s %s") % (rundir, inshell, env))

        if output == subprocess.PIPE:
            p1 = subprocess.Popen(command, cwd=rundir, stdout=output, stderr=error, shell=inshell, env=env, preexec_fn=preexec_fn)

            while p1.poll() == None:
                try:
                    returncode = int(p1.poll())
                except:
                    if output == subprocess.PIPE:
                        try:
                            line = p1.stdout.readline()
                            if not line == "":
                                callback.parse_line(command, line)
                        except:
                            pass
                    if error == subprocess.PIPE:
                        try:
                            line = p1.stderr.readline()
                            if not line == "":
                                self.log.debug(line.strip())
                        except:
                            pass
        else:
            p1 = subprocess.Popen(command, cwd=rundir, stdout=output, stderr=error, preexec_fn=preexec_fn)
            (out, err) = p1.communicate()

        if p1.returncode != 0:
            self.log.error(_("Got an error from %s (return code %s)") % (command[0],p1.returncode), recoverable=self.cfg.gui_mode)
