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
import fnmatch
import logging
import os
import re
import revisor
import rpmUtils.arch
import shutil
import socket
import subprocess
import sys
import urlgrabber
import urlparse
import yum

from revisor.translate import _, N_

global resolved_deps

def check_uid():
    """Check if the user has enough permissions to perform this task"""
    if os.geteuid() != 0:
        print >> sys.stderr, _("This tool has to run with root privileges. Aborting")
        sys.exit(1)

def check_selinux(log=None):
    """Check if the composing host has SELinux in enforcing (which will cause the build to fail)"""

    if not os.path.exists("/selinux/enforce"):
        log.warning(_("SELinux on this host is disabled. Composed media will not have SELinux, and as a result the system you install from the composed media will not have SELinux either."))

def get_file(url, working_directory="/var/tmp"):
    """Gets a file from url and returns the file name (full path)"""

    # Check if it isn't a file already
    if os.path.isfile(url): return url

    # Otherwise it might be an actual url
    file_basename = os.path.basename(urlparse.urlparse(url).path)
    file_name = os.path.join(working_directory, file_basename)

    if not check_file(file_name, destroy=True):
        # File does not exist or wasn't valid. Download the file.
        download_file(url, file_name)
    else:
        # There should be no else to this one
        pass

    return file_name

def download_file(url, file_name, title=None):
    urlgrabber.urlgrab(url, file_name, copy_local=1)

def download_packages(polist, log, cfg, pbar, yumobj=None):
    """
        Downloads packages.

        Using a list of Package Objects, determines what packages have already
        been downloaded and downloads the other packages.
    """

    if yumobj == None:
        if hasattr(cfg,"yumobj"):
            yumobj = cfg.yumobj
        else:
            log.error(_("cfg parameter to revisor.misc.download_packages() " + \
                        "expected to be a Revisor ConfigStore with a YUM " + \
                        "Object, or a YUM Object to be passed separately"),
                        recoverable=False
                     )

    dlCb = revisor.progress.dlcb(pbar, polist, log=log, cfg=cfg)
    yumobj.repos.setProgressBar(dlCb)

    # Packages already downloaded
    real_dlpkgs = []
    for po in polist:
        if os.path.exists(po.localPkg()) and os.path.getsize(po.localPkg()) == int(po.returnSimple('packagesize')):
            log.debug(_("Using local copy of %s-%s-%s.%s at %s") % (po.name, po.version, po.release, po.arch, po.localPkg()), level=9)
            dlCb._do_end(1)
        else:
            real_dlpkgs.append(po)

    try:
        probs = yumobj.downloadPkgs(real_dlpkgs, dlCb)
    except yum.Errors.RepoError, errmsg:
        log.error(errmsg)
    except IndexError:
        log.error(_("Unable to find a suitable mirror."))

    yumobj.repos.setProgressBar(None)

    if len(probs.keys()) > 0:
        errstr = []
        for key in probs.keys():
            errors = yum.misc.unique(probs[key])
            for error in errors:
                errstr.append("%s: %s" %(key, error))

        details_str = "\n".join(errstr)
        log.error(_("Errors were encountered while downloading packages: %s") % details_str, recoverable=cfg.gui_mode)

def check_file(file_name, checksum=None, destroy=False):
    """
    Checks if a file exists. Basically returns True if the file exists, unless the
    checksum doesn't check out or destroy has been set to True.

    If the file exists:
        Checksum:
            If specified, run the checksum and return:
                - True if the checksum checks out.
                - False if it doesn't and destroy the file.
            If not specified:
                - Continue
        Destroy:
            If True:
                - Destroy the file and return False
            else:
                - Return True
    else:
        - return False

    """
    if os.access(file_name, os.R_OK):
        if not checksum == None:
            if file_checksum(file_name, checksum):
                return True
            else:
                return False
        elif destroy:
            os.remove(file_name)
            return False
        else:
            return True
    else:
        return False

def resolve_pkgs(yumobj, package_list, log=None):
    """
        Given a list of 'packages', resolves these 'packages' into package names
        so that later they can be selected. A good example is the suggested
        package 'system-logos', which just so happens to be 'fedora-logos', or
        'generic-logos', or 'redhat-logos', or 'centos-logos'. We don't know,
        and neither do you
    """

    if log == None:
        log = revisor.logger.Logger()

    final_package_list = []
    warnings = []

    for pkg in package_list:
        if hasattr(yumobj.pkgSack,"contains"):
            has_pkg = yumobj.pkgSack.contains(pkg)
        else:
            try:
                pkgs = yumobj.pkgSack.returnNewestByName(pkg)
                if len(pkgs) > 0:
                    has_pkg = True
                else:
                    has_pkg = False
            except yum.Errors.PackageSackError, e:
                has_pkg = False

        if has_pkg:
            final_package_list.append(pkg)
            if not log == None:
                log.debug(_("Resolved %s") % (pkg), level=9)
        else:
            if "*" in pkg:
                try:
                    pkglist = yumobj.pkgSack.simplePkgList()
                    # anything we couldn't find a match for
                    # could mean it's not there, could mean it's a wildcard
                    if re.match('.*[\*,\[,\],\{,\},\?].*', pkg):
                        restring = fnmatch.translate(pkg)
                        regex = re.compile(restring, flags=re.I) # case insensitive
                        for item in pkglist:
                            if regex.match(item[0]):
                                final_package_list.append(item[0])
                                log.debug(_("Found packages matching '%s': %s") % (pkg,item[0]), level=9)

                except yum.Errors.PackageSackError, e:
                    pass

            # Here's where we try and see if this is a rpm -qa list
            elif re.match('.*-.*-.*', pkg):
                (name, epoch, ver, rel, arch) = return_pkg_tuple(pkg)

                pkgs = yumobj.pkgSack.searchNevra(name=name, epoch=epoch, ver=ver, rel=rel, arch=arch)

                if len(pkgs) > 1:
                    warnings.append(_("More then one package found for %s-%s-%s.%s") % (name,ver,rel,arch))
                elif len(pkgs) < 1:
                    warnings.append(_("Could not find package %s-%s-%s.%s") % (name,ver,rel,arch))
                for po in pkgs:
                    final_package_list.append(po.name)
                    log.debug(_("From Packages (exact string %s-%s-%s.%s), selecting %s-%s-%s.%s") % (name,ver,rel,arch,po.name,po.version,po.release,po.arch), level=9)

            else:
                # If the package isn't in, search the provides
                pkgs = yumobj.whatProvides(pkg, None, None).returnPackages()
                if len(pkgs) > 0:
                    final_package_list.append(pkg)
                    if not log == None:
                        log.debug(_("Resolved %s") % (pkg), level=9)
                else:
                    if not log == None:
                        log.debug(_("Looking to resolve package %s to a Provides, but we still can't find it.") % pkg, level=2)

    return final_package_list

def resolve_dependencies_inclusive(yumobj, logger=None, pbar=None, resolved_deps={}, final_pkgobjs={}):
    if logger == None:
        logger = revisor.logger.Logger()

    logger.debug(_("Checking dependencies - allowing conflicts within the package set"), level=5)

    reqs = []

    logger.debug(_("Inclusive dependency resolving starts at %s") % datetime.datetime.now(), level=8)

    for txmbr in yumobj.tsInfo.getMembers():
        reqs.extend(txmbr.po.requires)

    reqs = yum.misc.unique(reqs)

    num_passes = 1

    moretoprocess = True
    while moretoprocess: # Our fun loop
        logger.debug("num_passes: %d" % num_passes)
        moretoprocess = False
        for txmbr in yumobj.tsInfo.getMembers():
            if not final_pkgobjs.has_key(txmbr.po):
                final_pkgobjs[txmbr.po] = None
                (resolved_deps, final_pkgobjs) = get_package_deps(yumobj, txmbr.po, pbar, logger=logger, resolved_deps=resolved_deps, final_pkgobjs=final_pkgobjs)
                moretoprocess = True

        num_passes += 1

    logger.debug(_("Inclusive dependency resolving ends at %s") % datetime.datetime.now(), level=8)

    return (resolved_deps, final_pkgobjs)

def get_source_package_builddeps(yumobj, pbar, arch_list, logger=None, resolved_deps={}, final_pkgobjs={}):
    """
        Gets the buildrequirements for a package object, and selects those.

        This is a loop as added build requirements may add extra packages with extra dependencies.
    """

    if logger == None:
        logger = revisor.logger.Logger(logfile="/dev/null")

    enable_repositories("source", yumobj, logger, arch_list)

    num_passes = 1

    done_pos = {}

    moretoprocess = True
    while moretoprocess:
        logger.debug("num_passes: %d" % num_passes)
        pbar.num_tasks += len(final_pkgobjs.keys())
        moretoprocess = False
        for po in final_pkgobjs.keys()[len(done_pos):]:
            if not done_pos.has_key(po):
                done_pos[po] = None
            else:
                continue

            pbar.next_task()
            try:
                srpmpos = yumobj.pkgSack.searchNevra(name=po.name, epoch=po.epoch, ver=po.version, rel=po.release, arch='src')
                for srpmpo in srpmpos:

                    if not final_pkgobjs.has_key(srpmpo):
                        final_pkgobjs[srpmpo] = None
                        len_start = len(final_pkgobjs.keys())
                        (resolved_deps, final_pkgobjs) = get_package_deps(
                                                                            yumobj,
                                                                            srpmpo,
                                                                            logger=logger,
                                                                            resolved_deps=resolved_deps,
                                                                            final_pkgobjs=final_pkgobjs)
                        pbar.num_tasks += (len(final_pkgobjs.keys()) - len_start)
                        moretoprocess = True
            except IndexError:
                logger.error(_("Cannot find a source rpm for %s" % srpmpo.name), recoverable=False)
        num_passes += 1

    disable_repositories("source", yumobj, logger, arch_list)

    return (resolved_deps, final_pkgobjs)

def get_source_package_binary_rpms(yumobj, po, pbar, logger=None, resolved_deps={}, final_pkgobjs={}):
    """
        Gets all the binary rpms composed from the source package, and selects
        those.

        Uses the yum object (yumobj) and the po (binary rpm po) to determine the
        source rpm and all binary rpms coming from that source rpm.
    """
    pass

def disable_repositories(needle, yumobj, log, arch_list):
    # Reset the existing sacks
    yumobj._pkgSack = None

    for repo in yumobj.repos.listEnabled():
        if repo.id.endswith("-%s" % needle):
            log.debug(_("Disabling %s repository") % repo.id, level=5)
            repo.disable()

    yumobj._getSacks(archlist=arch_list)

def enable_repositories(needle, yumobj, log, arch_list):
    # Disable excludes for a moment
    yumobj.conf.disable_excludes = "all"

    if needle == "source":
        arch_list = arch_list + ['src']

    for repo in yumobj.repos.listEnabled():
        _repo = '%s-%s' % (repo.id,needle)
        if len(yumobj.repos.findRepos(_repo)) < 1:
            log.error(_("No such repository: %s") % _repo)
        for r in yumobj.repos.findRepos(_repo):
            log.debug(_("Enabling %s repository") % r.id, level=5)
            r.enable()
            # Setup the repo
            r.setup(0)

            try:
                yumobj._getSacks(archlist=arch_list,thisrepo=r.id)
            except yum.Errors.RepoError, e:
                log.error(e)
            except RuntimeError, e:
                log.error(e)

def get_package_deps(yumobj, po, pbar=None, logger=None, resolved_deps={}, final_pkgobjs={}):
    """Add the dependencies for a given package to the
       transaction info"""

    if logger == None:
        logger = revisor.logger.Logger()

    logger.debug(_("Checking dependencies for %s.%s") % (po.name, po.arch), level=8)

    if not pbar == None:
        pbar.cur_task += 1.0

    reqs = po.requires
    provs = po.provides

    for req in reqs:
        (r,f,v) = req

        if resolved_deps.has_key(req):
            # This message is here for troubleshooting purposes
            #logger.debug(_("Saving you a little time, dep (%s, %s, %s) already resolved") % (r,f,v), level=9)
            continue

        if r.startswith('rpmlib(') or r.startswith('config('):
            if not pbar == None:
                pbar.cur_task += 1.0
                pbar.set_fraction(pbar.cur_task/pbar.num_tasks)
            continue

        if req in provs:
            if not pbar == None:
                pbar.cur_task += 1.0
                pbar.set_fraction(pbar.cur_task/pbar.num_tasks)
            continue

        deps = yumobj.whatProvides(r, f, v).returnPackages()

        if not deps:
            if not pbar == None:
                pbar.cur_task += 1.0
            logger.warning(_("Unresolvable dependency %s %s %s in %s.%s") % (r, f, v, po.name, po.arch))
            continue

        depsack = yum.packageSack.ListPackageSack(deps)

        for dep in depsack.returnNewestByNameArch():
            yumobj.tsInfo.addInstall(dep)
            logger.debug(_("Added %s-%s:%s-%s.%s for %s-%s:%s-%s.%s (requiring %s %s %s)") % (dep.name, dep.epoch, dep.version, dep.release, dep.arch, po.name, po.epoch, po.version, po.release, po.arch, r, f, v), level=9)
            resolved_deps[(r, f, v)] = None

    return (resolved_deps, final_pkgobjs)

def get_repourls(yumobj):
    """
        From a yum object, extract the repository URLs for repositories
        that are enabled.

        Returns a tuple of lists, baseurls and mirrorlists
    """
    repository_baseurls = []
    repository_mirrorlists = []
    for repo in yumobj.repos.listEnabled():
        mirror_list = False
        if hasattr(repo, "baseurl"):
            if isinstance(repo.baseurl, list):
                this_repo = repo.baseurl[0]
            else:
                this_repo = repo.baseurl

            # Check whether it is a localrepo baseurl
            if this_repo.startswith('http://localrepo'):
                # Check whether localrepo resolves anywhere
                result = None
                try:
                    result = socket.getaddrinfo('localrepo', None)
                except:
                    # Set the result to None
                    result = None
                    pass

                if result == None:
                    # Go with the mirrorlist
                    mirror_list = True

        if mirror_list and hasattr(repo,"mirrorlist"):
            print "Using mirrorlist %s from repo %s" % (repo.mirrorlist,repo.id)
            repository_mirrorlists.append(repo.mirrorlist)
        else:
            repository_baseurls.append(this_repo)

    return (repository_baseurls,repository_mirrorlists)

def return_pkg_tuple(pkg):
    """
        Given a package name (string), resolve the following forms to a package tuple:
        - name-version-release.disttag.arch
        - name-version-release.disttag
        - name-version-release.arch
        - name-version-release

        Returns a (name, epoch, version, release, arch) tuple
    """

    name = None
    epoch = None
    version = None
    release = None
    arch = None

    # We only accept strings
    if not isinstance(pkg, str):
        return

    print "Input: %s" % pkg

    # First of all, the package must match the following regexp:
    # FIXME: Tweak this regexp
    if re.match('.*-.*-.*', pkg):

        # The first thing we need to get is the name and ver.
        # This is relatively easy
        (name, version, reldistarch) = pkg.rsplit('-', 2)

        # version can still hold the epoch, as can name
        try:
            (epoch, version) = version.split(':', 1)
        except ValueError:
            try:
                (epoch, name) = name.split(':', 1)
            except ValueError:
                epoch = None


        # Now, for the reldistarch part,
        try:
            # Try splitting rel.disttag.arch
            (rel, dist, arch) = reldistarch.rsplit('.', 2)
            if rpmUtils.arch.arches.has_key(arch) or arch == "noarch":
                # We have a winner!
                release = "%s.%s" % (rel, dist)
            else:
                # Apparently there's a dot in the release :/
                release = reldistarch
                arch = None

        except ValueError:
            # Failed, so..., is this rel.arch? or rel.disttag?
            # Let's try and split on .
            # If it errors, we only have the release
            # If it's OK, we either have rel, arch, or rel, disttag

            try:
                (foo, bar) = reldistarch.rsplit('.', 2)
                # Now that we've split, see if bar is an arch or a disttag
                if rpmUtils.arch.arches.has_key(bar) or arch == "noarch":
                    arch = bar
                else:
                    arch = None
                    # If we didn't find a valid architecture, then
                    # bar is part of the release (e.g. disttag)
                    release = "%s.%s" % (foo, bar)

            except ValueError:
                # Apparently our string only holds the release
                release = reldistarch

    return (name, epoch, version, release, arch)

def get_system_release():
    p1 = subprocess.Popen(['rpmquery', '--qf="%{VERSION}\n"', 'fedora-release'], output=subprocess.PIPE)
    release = p1.stdout.readline().trim()
    return release

def get_system_arch():
    p1 = subprocess.Popen(['uname', '-p'], output=subprocess.PIPE)
    arch = p1.stdout.readline().trim()
    return arch

def size_me(val):
    """
        Given a value, convert it to a humanly readible format
        Returns a tuple of (quantity, unit), e.g. (0, "KB")
    """
    ret_val = int(val)
    units = [ "B", "kB", "MB", "GB", "TB" ]
    while ret_val > 1024:
        units.pop(0)
        ret_val = ret_val / 1024

    return (ret_val,units[0])

def link_pkgs(pos, destdir, copy_local=False, pbar=None, log=None):
    if not os.path.exists(destdir):
        if log: log.debug(_("Creating destination directory: %s" % (destdir)))
        os.makedirs(destdir)
    else:
        if log: log.debug(_("Removing destination directory: %s" % (destdir)))
        shutil.rmtree(destdir, ignore_errors=True)
        if log: log.debug(_("Creating destination directory: %s" % (destdir)))
        os.makedirs(destdir)

    i = 0
    total = float(len(pos))

    # Just so that we know. If the hardlink fails once, why try it again?
    # FIXME: Do something really smart with this
    hardlink_failed = False

    for po in pos:
        try:
            if log: log.debug(_("Linking %s => %s") % (po.localPkg(), destdir + "/" + os.path.basename(po.localPkg())), level=9)
            os.link(po.localPkg(), destdir + "/" + os.path.basename(po.localPkg()))
        except OSError, e:
            if log: log.debug(_("Package hard link failed: %s: %s") % (e, destdir + "/" + os.path.basename(po.localPkg())), level=9)
            if e.errno == 17:
                continue
            elif e.errno == 18:
                if copy_local:
                    if log: log.debug(_("Copying: %s to %s") % (po.localPkg(), destdir + "/" + os.path.basename(po.localPkg())), level=9)
                    shutil.copy2(po.localPkg(), destdir + "/" + os.path.basename(po.localPkg()))
                else:
                    if log: log.debug(_("Symlinking: %s to %s") % (po.localPkg(), destdir + "/" + os.path.basename(po.localPkg())), level=9)
                    try:
                        os.symlink(po.localPkg(), destdir + "/" + os.path.basename(po.localPkg()))
                        if log: log.debug(_("Package symlink succeeded"))
                    except OSError, e:
                        if log: log.debug(_("Package link failed, trying copy: %s: %s") % (e, os.path.basename(po.localPkg())), level=9)
                        try:
                            shutil.copy2(po.localPkg(), destdir + "/" + os.path.basename(po.localPkg()))
                        except:
                            pass
            else:
                try:
                    if log: log.debug(_("Package link failed, trying copy: %s: %s") % (e, os.path.basename(po.localPkg())), level=9)
                    shutil.copy2(po.localPkg(), destdir + "/" + os.path.basename(po.localPkg()))
                except:
                    pass

        i += 1.0
        if pbar: pbar.set_fraction(i/total)

