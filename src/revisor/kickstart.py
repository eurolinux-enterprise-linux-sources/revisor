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

import fnmatch
import os
import re
import sys

import revisor.misc

import pykickstart
import pykickstart.constants as constants
import pykickstart.parser as parser
from urlgrabber import urlgrab

import yum.misc

# Translation
from revisor.translate import _, N_

class RevisorKickstart:
    """
        A robust kickstart object interfacing between Revisor and different
        pykickstart APIs.
    """

    def __init__(self, cfg=None):
        self.cfg = cfg

    def _reset(self):
        self.parser._reset()

    def create_parser(self):
        """
            Returns a regular kickstart parser
        """
        try:
            import pykickstart.version
            if not self.cfg == None:
                self.handler = pykickstart.version.makeVersion(version=pykickstart.version.stringToVersion(self.cfg.version_from))
            else:
                self.handler = pykickstart.version.makeVersion(version=pykickstart.version.stringToVersion("DEVEL"))

            self.parser = pykickstart.parser.KickstartParser(self.handler, missingIncludeIsFatal=False)
        except:
            import pykickstart.data
            self.ksdata = pykickstart.data.KickstartData()
            self.handler = pykickstart.parser.KickstartHandlers(self.ksdata)
            self.parser = pykickstart.parser.KickstartParser(self.ksdata, self.handler, missingIncludeIsFatal=False)

    def _handler(self):
        """Returns the kickstart data object instance if it's there,
        and if it's not, it returns the handler"""
        if hasattr(self,"ksdata"):
            return self.ksdata
        else:
            return self.handler

    def read_file(self, url):
        """Reads in a kickstart file and returns True on success or False on failure"""
        # FIXME
        # For some reason the code below shows 0 byte sized kickstarts at the new location in /var/tmp
        # urlgrabber though has urlgrab() and urlopen(), the latter of which is used by pykickstarts
        # readKickstart()
        #
        #kickstart_file_name = os.path.join(self.cfg.working_directory, "%s-ks.cfg" % self.cfg.model)
        #try:
            #urlgrab(url, filename=kickstart_file_name, copy_local=1)
        #except Exception, e:
            #self.cfg.log.error(_("Download of %s to %s failed." % (url, kickstart_file_name)), recoverable=False)
        #self.cfg.kickstart_file = kickstart_file_name
        #print "Kickstart file: %s" % self.cfg.kickstart_file
        #self.parser.readKickstart(kickstart_file_name)

        if not hasattr(self, "parser"):
            self.create_parser()

        self.parser.readKickstart(url)

    def _reset(self):
        self.parser._reset()

    def __str__(self):
        if hasattr(self,"ksdata"):
            kswriter = pykickstart.writer.KickstartWriter(self.ksdata)
            return kswriter.write()
        else:
            return "%s" % self.handler.__str__()

    def _get(self, item=None, val=None):
        # pykickstart >= 0.100
        if not item == None:
            if hasattr(self,"ksdata"):
                self_ref = self.ksdata
            else:
                self_ref = self.handler

            if hasattr(self_ref,item):
                if not val == None:
                    if hasattr(getattr(self_ref,item),val):
                        return getattr(getattr(self_ref,item),val)
                    elif isinstance(getattr(self_ref,item), dict):
                        return getattr(self_ref,item)[val]
                    else:
                        pass
                else:
                    return getattr(self_ref,item)
            elif hasattr(self_ref,val):
                return getattr(self_ref,val)

        elif hasattr(self,"ksdata"):
            return self.ksdata
        else:
            return self.handler

    def _set(self, item1, item2=None, val=None):
        # ks.item1 = val
        # ks.item1.item2 = val
        # ks.item1[item2] = val

        if hasattr(self,"ksdata"):
            self_ref = self.ksdata
        else:
            self_ref = self.handler

        if hasattr(self_ref,item1):
            if not item2 == None:
                self_ref = getattr(self_ref,item1)
                if hasattr(self_ref,item2):
                    setattr(self_ref,item2,val)
                elif isinstance(getattr(self_ref,item2), dict):
                    self_ref[item2] = val
                else:
                    raise AttributeError
            else:
                setattr(self_ref,item1,val)
        else:
            raise AttributeError

    def _NetworkData(self):
        if hasattr(self,"ksdata"):
            self.ks_net_data = pykickstart.data.KickstartNetworkData()
        else:
            self.ks_net_data = self.handler.NetworkData()
        return self.ks_net_data

    def _network_add(self, nd):
        if hasattr(self,"ksdata"):
            self.ksdata.network.add(nd)
        else:
            self.handler.network.add(nd)

    def _Group(self, name, include=None):
        if hasattr(self,"ksdata"):
            group = pykickstart.data.packages.Group(name)
        else:
            if include == None:
                include = constants.GROUP_DEFAULT
            group = pykickstart.parser.Group(name, include=include)
        return group

def select_groups(log=None, ksobj=None, groupList=[], groups=[]):
    """
        Selects an additional group that has not already been selected.

        Useful for groups such as @core and @base that do not need to be
        selected in a kickstart package manifest per-se, but are included
        by default.

        See also:
        - Line ~1242 in kickstart.py (anaconda GIT)

    """

    if ksobj == None:
        return groupList

    if log == None:
        log = logger.Logger()

    for group in groups:
        selected = False
        for ksgroup in groupList:
            if hasattr(ksgroup,"name"):
                group_name = ksgroup.name
            else:
                group_name = ksgroup

            if group_name == group:
                selected = True

        if not selected:
            # @base is a special group... It has a parameter.
            if not group == "base":
                log.debug(_("Appending group @%s") % group)
                groupList.append(ksobj._Group(group))
            elif ksobj._get("packages","addBase"):
                log.debug(_("Appending group @%s") % group)
                groupList.append(ksobj._Group(group))

    return groupList

def select_default_groups(groupList, yumobj, ksobj):
    for group in yumobj.comps.groups:
        if hasattr(group,"default"):
            if bool(group.default):
                ksobj.cfg.log.debug(_("Selecting %s as a default group") % group.groupid, level=9)
                groupList.append(ksobj._Group(group.groupid))

    return yum.misc.unique(groupList)

def pkglist_from_ksdata_livecdtools(
                                        log, cfg,
                                        pbar=None,
                                        groupList=[],
                                        packageList=[],
                                        excludedList=[],
                                        ignore_list=[]):
    """
        FIXME:

        This function replicates livecd-tools' behaviour as much as possible;
        - use yum.selectGroup() to select groups, instead of iterating over
          group members seeing which onces we want to select.
        - use yum matches to search for packages instead of searching for a
          match ourselves.
        - select the yum matches through yum.install(pattern=pkg) rather then
          selecting our manually found match through yum.tsInfo.addInstall(po)

        @parameters:
        log: a logger instance, preferably a revisor.logger.Logger() instance
        cfg: a revisor.cfg.ConfigStore instance, or something else that has
                the configuration parameter attributes used here.
        pbar: a progress bar
        groupList: a pykickstart handler object's groupList
        packageList: a pykickstart handler object's packageList
        excludedList: a pykickstart handler object's excludedList
    """

    total = float(len(groupList) * 3 +
                len(packageList) * 2 +
                len(excludedList))

    if total < 1.0:
        total = 1.0

    current = 0.0

    warnings = []

    if not ( cfg.kickstart_exact_nevra or cfg.kickstart_exact ):
        groupList = select_groups(log=log, ksobj=cfg.ksobj, groupList=groupList, groups=["core", "base"])

    if cfg.ksobj._get("packages","default"):
        groupList = select_default_groups(groupList=groupList,yumobj=cfg.yumobj,ksobj=cfg.ksobj)

    for ksgroup in groupList:
        current += 3.0
        if hasattr(ksgroup,"name"):
            group_name = ksgroup.name
        else:
            group_name = ksgroup

        log.debug(_("Found group: %s") % group_name, level=8)
        # Get group object from comps
        # This might fail if not all repository data is available
        try:
            grp = cfg.yumobj.comps.return_group(group_name)
        except yum.Errors.RepoError, e:
            log.error(_("Repository metadata cannot be found: %s: %s") % ("yum.Errors.RepoError", e), recoverable=False)

        if not grp:
            warnings.append(_("Group not found: %s") % group_name)
            continue

        package_types = ['mandatory', 'default']
        if hasattr(grp, "include"):
            if grp.include == pykickstart.parser.GROUP_REQUIRED:
                package_types.remove('default')
            elif include == pykickstart.parser.GROUP_ALL:
                package_types.append('optional')

        txmbrs = cfg.yumobj.selectGroup(grp.name, group_package_types=package_types)
        for txmbr in txmbrs:
            log.debug(_("Adding %s-%s:%s-%s.%s") % (txmbr.po.name, txmbr.po.epoch, txmbr.po.version, txmbr.po.release, txmbr.po.arch), level=9)

        pbar.set_fraction(current/total)

    ##
    ## Add packages in ksdata to transaction
    ##
    pkglist = []
    matchdict = {}
    for pkg in packageList:
        pkglist.append(pkg)

    ##
    ## Add pkglist to install
    ##
    # Make the search list unique
    pkglist = yum.misc.unique(pkglist)

    # Now resolve them before we go under
    pkglist = revisor.misc.resolve_pkgs(cfg.yumobj, pkglist, log=log)

    total = float(len(pkglist))

    for pkg in pkglist:
        current += 1.0
        txmbrs = cfg.yumobj.install(pattern=pkg)
        pbar.set_fraction(current/total)
        for txmbr in txmbrs:
            log.debug(_("Adding %s-%s:%s-%s.%s") % (txmbr.po.name, txmbr.po.epoch, txmbr.po.version, txmbr.po.release, txmbr.po.arch), level=9)


    ##
    ## Exclude packages from ksdata
    ##
    if not cfg.kickstart_uses_pkgsack_exclude:
        for pkg in revisor.misc.resolve_pkgs(cfg.yumobj, excludedList, log=log):
            current += 1.0
            try:
                pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                for po in pkgs:
                    log.debug(_("From Excludes: Removing %s-%s:%s-%s.%s from transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=8)
                    cfg.yumobj.tsInfo.remove(po.pkgtup)
            except yum.Errors.PackageSackError, e:
                log.debug(_("Apparently trying to exclude a package that is not available in the repositories loaded, or hasn't been added to the transaction: %s") % e.value, level=4)
            except:
                pass
            pbar.set_fraction(current/total)

    if len(warnings) > 0:
        log.warning(_("\nThe following errors occured when selecting groups and packages from kickstart:\n\n- %s\n\nYou can continue with these minor errors but obviously the results may not be what you expected.") % '\n- '.join(warnings))

    cfg.yumobj.tsInfo.makelists()

    cfg.ts_length_pre_depsolve = len(cfg.yumobj.tsInfo.getMembers())

    log.debug(_("This is what was selected to be installed:"), level=7)
    installpkgs = []
    for po in cfg.yumobj.tsInfo.installed:
        installpkgs.append(po.pkgtup)
        log.debug("--> %s" % str(po.pkgtup), level=7)

def pkglist_from_ksdata_normal(
                                log, cfg,
                                pbar=None,
                                groupList=[],
                                packageList=[],
                                excludedList=[],
                                ignore_list=[]):
    """
        This function adds packages to the yum transaction set the regular way
        Pass it a list of names of packages that we should ignore the
        architecture off. An example is libbeagle, kernel, pm-utils
    """

    total = float(len(groupList) * 3 +
                len(packageList) * 2 +
                len(excludedList))

    if total < 1.0:
        total = 1.0

    current = 0.0

    warnings = []

    if not ( cfg.kickstart_exact_nevra or cfg.kickstart_exact):
        groupList = select_groups(log=log, ksobj=cfg.ksobj, groupList=groupList, groups=["core", "base"])

    if cfg.ksobj._get("packages","default"):
        groupList = select_default_groups(groupList=groupList,yumobj=cfg.yumobj,ksobj=cfg.ksobj)

    ##
    ## Add packages from Groups in ksdata
    ##
    for ksgroup in groupList:
        current += 3.0
        if hasattr(ksgroup,"name"):
            group_name = ksgroup.name
        else:
            group_name = ksgroup

        log.debug(_("Found group: %s") % group_name, level=8)

        # Get group object from comps
        # This might fail if not all repository data is available
        try:
            grp = cfg.yumobj.comps.return_group(group_name)
        except yum.Errors.RepoError, e:
            log.error(_("Repository metadata cannot be found: %s: %s") % ("yum.Errors.RepoError", e), recoverable=False)

        if not grp:
            warnings.append(_("Group not found: %s") % group_name)
            continue

        # Select the group
        # What this selects is dependent on cfg.yumobj.conf.group_package_types
        # The default is to select default and mandatory packages, so if a group has
        # --nodefaults, don't select via yum, please
        #txmbrs_used = cfg.yumobj.selectGroup(grp.name)

        # Add all required packages
        if hasattr(ksgroup,"include"):
            if ksgroup.include >= constants.GROUP_REQUIRED:
                log.debug(_("Selecting required packages for group %s") % grp.name, level=8)
                for pkg in grp.mandatory_packages.keys():
                    if pkg in excludedList:
                        continue
                    log.debug(_("Including %s") % pkg, level=8)
                    # Get the package objects
                    try:
                        pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                        if len(pkgs) > 1 and not pkg in ignore_list:
                            pkgs = cfg.yumobj.bestPackagesFromList(pkgs)

                        # Add to transaction
                        for po in pkgs:
                            cfg.yumobj.tsInfo.addInstall(po)
                            log.debug(_("From Groups (required): Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                    except yum.Errors.PackageSackError, e:
                        if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE and not group_name == "core":
                            warnings.append(e.value)

            # Add all default packages
            if ksgroup.include >= constants.GROUP_DEFAULT:
                log.debug(_("Selecting default packages for group %s") % grp.name, level=8)
                for pkg in grp.default_packages.keys():
                    if pkg in excludedList:
                        continue
                    log.debug(_("Including %s") % pkg, level=9)
                    # Get the package objects
                    try:
                        pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                        if len(pkgs) > 1 and not pkg in ignore_list:
                            pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
                        # Add to transaction
                        for po in pkgs:
                            cfg.yumobj.tsInfo.addInstall(po)
                            log.debug(_("From Groups (default): Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                    except yum.Errors.PackageSackError, e:
                        if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE and not group_name == "core":
                            warnings.append(e.value)

            # Add all optional packages
            if ksgroup.include >= constants.GROUP_ALL:
                log.debug(_("Selecting optional packages for group %s") % grp.name, level=7)
                # All optional packages included, get the package names
                for pkg in grp.optional_packages.keys():
                    if pkg in excludedList:
                        continue
                    log.debug(_("Including %s") % pkg, level=8)
                    # Get the package objects
                    try:
                        pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                        if len(pkgs) > 1 and not pkg in ignore_list:
                            pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
                        # Add to transaction
                        for po in pkgs:
                            cfg.yumobj.tsInfo.addInstall(po)
                            log.debug(_("From Groups (optional): Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                    except yum.Errors.PackageSackError, e:
                        if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE and not group_name == "core":
                            warnings.append(e.value)
            pbar.set_fraction(current/total)
        else:
            log.debug(_("No include parameter for group %s, using defaults") % group_name, level=8)
            for pkg in grp.default_packages.keys() + grp.mandatory_packages.keys():
                if pkg in excludedList:
                    continue
                log.debug(_("Including %s") % pkg, level=8)
                # Get the package objects
                try:
                    pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                    if len(pkgs) > 1 and not pkg in ignore_list:
                        pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
                    # Add to transaction
                    for po in pkgs:
                        cfg.yumobj.tsInfo.addInstall(po)
                        log.debug(_("From Groups (optional): Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                except yum.Errors.PackageSackError, e:
                    if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE and not group_name == "core":
                        warnings.append(e.value)

    ##
    ## Pull the conditional packages in
    ##
        for condreq, cond in grp.conditional_packages.iteritems():
            log.debug(_("Testing condition: %s / %s") % (condreq, cond), level=9)
            pkgs = cfg.yumobj.pkgSack.searchNevra(name=condreq)
            if len(pkgs) > 1:
                pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
            if cfg.yumobj.tsInfo.conditionals.has_key(cond):
                cfg.yumobj.tsInfo.conditionals[cond].extend(pkgs)
            else:
                cfg.yumobj.tsInfo.conditionals[cond] = pkgs

    ##
    ## Add packages in ksdata to transaction
    ##
    for pkg in packageList:
        search = False
        current += 2.0
        log.debug(_("From package list, including: %s") % pkg, level=8)

        if pkg in excludedList:
            log.debug(_("Package %s is in excludeList, continuing") % pkg, level=9)
            continue

        try:
            pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
            if len(pkgs) > 1 and not pkg in ignore_list:
                pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
            elif len(pkgs) == 0:
                log.debug(_("No packages found!"), level=9)
                search = True

            for po in pkgs:
                cfg.yumobj.tsInfo.addInstall(po)
                log.debug(_("From Packages: Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)

        except yum.Errors.PackageSackError, e:
            search = True

        # Let's see if there's some regexp, and if there is, let's search
        if search:
            log.debug(_("Could not find package '%s', searching...") % pkg, level=9)
            if "*" in pkg:
                try:
                    pkglist = cfg.yumobj.pkgSack.simplePkgList()
                    matches = []
                    # anything we couldn't find a match for
                    # could mean it's not there, could mean it's a wildcard
                    if re.match('.*[\*,\[,\],\{,\},\?].*', pkg):
                        restring = fnmatch.translate(pkg)
                        regex = re.compile(restring, flags=re.I) # case insensitive
                        for item in pkglist:
                            if regex.match(item[0]):
                                matches.append(item[0])
                                log.debug(_("Found packages matching '%s': %s") % (pkg,item[0]), level=9)
                    for pkg in matches:
                        pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                        if len(pkgs) > 1:
                            pkgs = cfg.yumobj.bestPackagesFromList(pkgs)

                        for po in pkgs:
                            if not po.name in ignore_list:
                                cfg.yumobj.tsInfo.addInstall(po)
                                log.debug(_("From Packages: Adding %s-%s:%s-%s.%s to transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=9)
                            else:
                                log.debug(_("From Packages: Not adding %s now because it is in the ignore list") % po.name, level=9)

                except yum.Errors.PackageSackError, e:
                    if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE:
                        warnings.append(e.value)
            # Here's where we try and see if this is a rpm -qa list
            elif re.match('.*-.*-.*', pkg):
                (name, epoch, ver, rel, arch) = revisor.misc.return_pkg_tuple(pkg)

                pkgs = cfg.yumobj.pkgSack.searchNevra(name=name, epoch=epoch, ver=ver, rel=rel, arch=arch)
                if len(pkgs) > 1:
                    warnings.append(_("More then one package found for %s-%s-%s.%s - going to add them all to the transaction") % (name,ver,rel,arch))
                elif len(pkgs) < 1:
                    warnings.append(_("Could not find package %s-%s-%s.%s") % (name,ver,rel,arch))
                for po in pkgs:
                    cfg.yumobj.tsInfo.addInstall(po)
                    log.debug(_("From Packages (exact string %s-%s-%s.%s), selecting %s-%s-%s.%s") % (name,ver,rel,arch,po.name,po.version,po.release,po.arch), level=9)

            else:
                try:
                    if cfg.ksobj._get("packages","handleMissing") != constants.KS_MISSING_IGNORE:
                        warnings.append(e.value)
                except UnboundLocalError:
                    pass

        pbar.set_fraction(current/total)

    ##
    ## Exclude packages from ksdata
    ##
    if not cfg.kickstart_uses_pkgsack_exclude:
        for pkg in revisor.misc.resolve_pkgs(cfg.yumobj, excludedList, log=log):
            current += 1.0
            try:
                pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                for po in pkgs:
                    log.debug(_("From Excludes: Removing %s-%s:%s-%s.%s from transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=8)
                    cfg.yumobj.tsInfo.remove(po.pkgtup)
            except yum.Errors.PackageSackError, e:
                log.debug(_("Apparently trying to exclude a package that is not available in the repositories loaded, or hasn't been added to the transaction: %s") % e.value, level=4)
            except:
                pass
            pbar.set_fraction(current/total)

    if len(warnings) > 0:
        log.warning(_("\nThe following errors occured when selecting groups and packages from kickstart:\n\n- %s\n\nYou can continue with these minor errors but obviously the results may not be what you expected.") % '\n- '.join(warnings))

    #cfg.yumobj.tsInfo.makelists()

    cfg.ts_length_pre_depsolve = len(cfg.yumobj.tsInfo.getMembers())

    log.debug(_("This is what was selected to be installed:"), level=7)
    installpkgs = []
    for po in cfg.yumobj.tsInfo.installed:
        installpkgs.append(po.pkgtup)
        log.debug("--> %s" % str(po.pkgtup), level=7)

def pkglist_from_ksdata_respin(
                                log, cfg,
                                pbar=None,
                                groupList=[],
                                packageList=[],
                                excludedList=[],
                                ignore_list=[]):
    """
        Takes valid kshandler.packages.groupList, kshandler.packages.packageList
        and kshandler.packages.excludedList, and builds a nice and simple list
        that we can add our required packages to, and then start depsolving
    """

    pkglist = []
    matchdict = {}

    total = 1.0
    current = 0.0

    if not ( cfg.kickstart_exact_nevra or cfg.kickstart_exact):
        groupList = select_groups(log=log, ksobj=cfg.ksobj, groupList=groupList, groups=["core", "base"])

    if cfg.ksobj._get("packages","default"):
        groupList = select_default_groups(groupList=groupList,yumobj=cfg.yumobj,ksobj=cfg.ksobj)

    ##
    ## Add packages from Groups in ksdata
    ##
    for ksgroup in groupList:
        if not cfg.yumobj.comps.has_group(ksgroup.name):
            log.warning(_("No such group %s") % ksgroup.name )
            continue
        else:
            log.debug(_("Found group: %s") % ksgroup.name, level=8)

        # Get group object from comps
        grp = cfg.yumobj.comps.return_group(ksgroup.name)
        try:
            txmbrs_used = cfg.yumobj.selectGroup(grp.name)
        except:
            pass

        if ksgroup.include >= constants.GROUP_REQUIRED:
            pkglist.extend(grp.mandatory_packages.keys())
        if ksgroup.include >= constants.GROUP_DEFAULT:
            pkglist.extend(grp.default_packages.keys())
        if ksgroup.include >= constants.GROUP_ALL:
            pkglist.extend(grp.optional_packages.keys())

        ##
        ## Pull the conditional packages in
        ##
        for condreq, cond in grp.conditional_packages.iteritems():
            log.debug(_("Testing condition: %s / %s") % (condreq, cond), level=8)
            pkgs = cfg.yumobj.pkgSack.searchNevra(name=condreq)
            if len(pkgs) > 1:
                pkgs = cfg.yumobj.bestPackagesFromList(pkgs)
            if cfg.yumobj.tsInfo.conditionals.has_key(cond):
                cfg.yumobj.tsInfo.conditionals[cond].extend(pkgs)
            else:
                cfg.yumobj.tsInfo.conditionals[cond] = pkgs

    ##
    ## Add packages in ksdata to transaction
    ##
    for pkg in packageList:
        pkglist.append(pkg)

    ##
    ## Add pkglist to install
    ##
    # Make the search list unique
    pkglist = yum.misc.unique(pkglist)

    total = float(len(pkglist))

    # Search repos for things in our searchlist, supports globs
    (exactmatched, matched, unmatched) = yum.packages.parsePackages(cfg.yumobj.pkgSack.returnPackages(), pkglist, casematch=1)
    matches = exactmatched + matched

    # Populate a dict of package objects to their names
    for match in matches:
        matchdict[match.name] = match

    # Get the newest results from the search
    mysack = yum.packageSack.ListPackageSack(matches)
    for match in mysack.returnNewestByNameArch():
        current += 1.0
        cfg.yumobj.tsInfo.addInstall(match)
        pbar.set_fraction(current/total)
        log.debug(_("Adding %s-%s:%s-%s.%s") % (match.name, match.epoch, match.version, match.release, match.arch), level=9)

    ##
    ## Exclude packages from ksdata
    ##
    if not cfg.kickstart_uses_pkgsack_exclude:
        for pkg in revisor.misc.resolve_pkgs(cfg.yumobj, excludedList, log=log):
            current += 1.0
            try:
                pkgs = cfg.yumobj.pkgSack.returnNewestByName(pkg)
                for po in pkgs:
                    log.debug(_("From Excludes: Removing %s-%s:%s-%s.%s from transaction") % (po.name, po.epoch, po.version, po.release, po.arch), level=8)
                    cfg.yumobj.tsInfo.remove(po.pkgtup)
            except yum.Errors.PackageSackError, e:
                log.debug(_("Apparently trying to exclude a package that is not available in the repositories loaded, or hasn't been added to the transaction: %s") % e.value, level=4)
            except:
                pass
            pbar.set_fraction(current/total)

    cfg.ts_length_pre_depsolve = len(cfg.yumobj.tsInfo.getMembers())
