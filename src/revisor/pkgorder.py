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
#
# Based on 'anaconda-runtime' pkgorder by:
# Paul Nasrat <pnasrat@redhat.com>
# Copyright 2005 Red Hat, Inc.
#

import os
import glob
import revisor.misc
import rpm
import rpmUtils
import shutil
import string
import sys
import yum
from yum.packageSack import PackageSack

import tempfile

#import iutil
#

# Translation
from revisor.translate import _, N_

class PackageOrderer(yum.YumBase):
    """The revisor package orderer that allows changes to yum and RPM in between releases,
    as well as package ordering customization"""

    def __init__(self, base):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log

        self.resolved_deps = {}
        self.final_pkgobjs = {}

        yum.YumBase.__init__(self)

        self.processed = {}

        # Boo
        if hasattr(self, "arch"):
            if self.arch == "i386":
                self.arch = "i686"

        # We're gonna use this an awful lot
        self.toppath = os.path.join(self.cfg.working_directory,"revisor-install",self.cfg.version,self.cfg.model,self.cfg.architecture,"os")

        self.cfg.pkgorder_file = os.path.join(self.cfg.working_directory,"revisor-install","pkgorder-file")
        # If we have a pkgorder file set already, see if we can use that one.
        self.log.debug("Setting pkgorder_file to %s" % self.cfg.pkgorder_file)

        self.testpath = tempfile.mkdtemp(dir=os.path.join(self.cfg.working_directory,"revisor-install"), prefix="pkgorder-root-")
        os.makedirs(os.path.join(self.testpath,"etc"))

    def addGroups(self, groupLst):
        for group in groupLst:
            # If no such group exists, skip it
            if not self.comps.has_group(group):
                continue

            # If the group is not in the kickstart groups, skip it
            #if not group in self.cfg.ksobj._get("packages","groupList"):
                #continue

            self.log.debug(_("Adding group: %s") % group, level=9)

            grp = self.comps.return_group(group)

            if self.cfg.pkgorder_style == "yum":
                self.selectGroup(grp)

            else:
#                packageLst = grp.mandatory_packages.keys() + grp.default_packages.keys() + grp.optional_packages.keys()
                packageLst = grp.mandatory_packages.keys() + grp.default_packages.keys()

                self.log.debug(_("The following packages are in group %s: %r") % (group, packageLst), level=9)

                for pkg in packageLst:
                    try:
                        pkgs = self.pkgSack.returnNewestByName(pkg)
                        for po in pkgs:
                            self.install(po)
                            self.log.debug(_("Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                    except yum.Errors.PackageSackError, e:
                        pass

                # Add the conditionals because frankly we don't know if they are going to be selected
                # during the installation process. In package ordering though, whether they end up on
                # the corrent disc is more important
                for condreq, cond in grp.conditional_packages.iteritems():
                    self.log.debug(_("Testing condition: %s / %s") % (condreq, cond), level=9)
                    try:
                        pkgs = self.pkgSack.returnNewestByName(condreq)
                        for po in pkgs:
                            self.install(po)
                            self.log.debug(_("Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                    except yum.Errors.PackageSackError, e:
                        pass


        if self.cfg.pkgorder_style == "yum":
            self.resolveDeps()
        else:
            self.log.debug(_("%d dependencies already resolved") % len(self.resolved_deps.keys()), level=9)
            (self.resolved_deps, self.final_pkgobjs) = revisor.misc.resolve_dependencies_inclusive(self, logger=self.log, resolved_deps=self.resolved_deps, final_pkgobjs=self.final_pkgobjs)

        for po in self.final_pkgobjs.keys():
            self.printMatchingPkgs(os.path.basename(po.localPkg()))

    def addPackages(self, packageLst):
        (exactmatched, matched, unmatched) = yum.packages.parsePackages(self.pkgSack.returnPackages(), packageLst, casematch=0)
        matches = exactmatched + matched

        self.log.debug(_("Adding package(s): %r") % [match.name for match in matches], level=9)

        map(self.install, filter(lambda x: self.pkgSack.returnNewestByName(), matches))

        if self.cfg.pkgorder_style == "yum":
            self.resolveDeps()
        else:
            (self.resolved_deps, self.final_pkgobjs) = revisor.misc.resolve_dependencies_inclusive(self, logger=self.log, resolved_deps=self.resolved_deps, final_pkgobjs=self.final_pkgobjs)
            #revisor.misc.resolve_dependencies_inclusive(self, logger=self.log, resolved_deps=self.resolved_deps, final_pkgobjs=self.final_pkgobjs)

        for po in self.final_pkgobjs.keys():
            self.printMatchingPkgs(os.path.basename(po.localPkg()))

    def processTransaction(self):
        del self.ts
        self.initActionTs()
        self.populateTs(keepold=0)
        self.ts.check()
        self.ts.order()
        for txmbr in self.ts.ts.getKeys():
            self.printMatchingPkgs(os.path.basename(txmbr.po.localPkg()))

    def createConfig(self):
        yumconfstr = """
[main]
distroverpkg=redhat-release
gpgcheck=0
reposdir=/dev/null
exclude=*debuginfo*
debuglevel=9
logfile=/var/log/yum.log
installroot=%(testpath)s
cachedir=%(cachedir)s

[anaconda]
name=Anaconda
baseurl=file://%(toppath)s
enabled=1
    """ % { "toppath": self.toppath, "testpath": self.testpath, "cachedir": self.cfg.yumobj.conf.cachedir }

        try:
            f = open(os.path.join(self.testpath,"etc","yum.conf"),"w")
            f.write(yumconfstr)
            f.close()
            return os.path.join(self.testpath,"etc","yum.conf")
        except:
            self.log.error(_("Unable to create yum configuration file for package ordering at %s") % os.path.join(self.testpath,"etc","yum.conf"))

    def printMatchingPkgs(self, filename):
        if self.processed.has_key(filename): return

        # If the file does not exist then what are we doing here?
        if not os.path.exists(os.path.join(self.toppath,self.cfg.product_path,filename)): return

        f = open(self.cfg.pkgorder_file,"a")
        f.write(filename + "\n")
        f.close()
        self.processed[filename] = True
        self.log.debug(_("-> package %s") % filename)

    def doFileLogSetup(self, uid, logfile):
        pass

    #def doLoggingSetup(self, *args, **kwargs):
        #pass

    def setup(self,pbar=None):

        if not pbar == None:
            self.pbar = pbar

        if hasattr(self,"preconf"):
            self.preconf.fn = self.cfg.main
            self.preconf.init_plugins = True
            self.preconf.plugin_types = (yum.plugins.TYPE_CORE,)
            self.preconf.debuglevel = self.cfg.debuglevel
            self.preconf.errorlevel = self.cfg.debuglevel

            #self.preconf.arch = rpmUtils.ArchStorage()

            self._getConfig()
        elif hasattr(self,"_getConfig"):
            self._getConfig(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
        else:
            self.doConfigSetup(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
            self.log.debug(_("Using deprecated YUM function: %s()") % "doConfigSetup", level=7)

        #try:
            #if hasattr(self,"preconf"):
                #self.preconf.fn = self.cfg.main
                #self.preconf.init_plugins = True
                #self.preconf.plugin_types = (yum.plugins.TYPE_CORE,)
                #self.preconf.debuglevel = self.cfg.debuglevel
                #self.preconf.errorlevel = self.cfg.debuglevel

                #self.preconf.arch = rpmUtils.ArchStorage()

                #self._getConfig()
            #elif hasattr(self,"_getConfig"):
                #self._getConfig(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
            #else:
                #self.doConfigSetup(fn=self.cfg.main, plugin_types=(yum.plugins.TYPE_CORE,))
                #self.log.debug(_("Using deprecated YUM function: %s()") % "doConfigSetup", level=7)
        #except:
            #self.log.error(_("yum.YumBase.doConfigSetup failed, probably an invalid configuration file %s") % self.cfg.main, recoverable=False)

        self.doRepoSetup()
        if hasattr(self,"_getTs"):
            self._getTs()
        else:
            self.log.debug(_("Using deprecated YUM function: %s()") % "doTsSetup")
            self.doTsSetup()

        if hasattr(self,"_getGroups"):
            self._getGroups()
        elif hasattr(self,"doGroupSetup"):
            self.doGroupSetup()

        if hasattr(self,"_getRpmDB"):
            self._getRpmDB()
        elif hasattr(self,"doSetupRPMDB"):
            self.log.debug(_("Using deprecated YUM function: %s()") % "doSetupRPMDB")
            self.doSetupRPMDB()
        elif hasattr(self,"doRpmDBSetup"):
            self.log.debug(_("Using deprecated YUM function: %s()") % "doRpmDBSetup")
            self.doRpmDBSetup()

        if not pbar == None:
            self.repos.callback = pbar

        if hasattr(self,"_getRepos"):
            self._getRepos()
        else:
            self.log.debug(_("Using deprecated YUM function: %s()") % "doRepoSetup")
            self.doRepoSetup()

#            self.log.debug(_("Arch list = %s") % self.cfg.arch_list)

        try:
            if hasattr(self,"_getSacks"):
                self._getSacks(archlist=self.cfg.arch_list)
            else:
                self.log.debug(_("Using deprecated YUM function: %s()") % "doSackSetup")
                self.doSackSetup(archlist=self.cfg.arch_list)
        except:
            pass

        if not pbar == None:
            self.pbar.destroy()

    def getDownloadPkgs(self):
        pass
