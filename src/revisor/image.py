# -*- coding: utf-8 -*-
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
import rpm
import rpmUtils
import sys

import imgcreate

from imgcreate.errors import CreatorError

import revisor.progress, revisor.misc

import yum.Errors

# Translation
from revisor.translate import _, N_

class RevisorImageCreator:
    def __init__(self, base, architecture):
        if architecture in ("i386", "i586", "i686", "x86_64"):
            self.imagecreator = x86LiveImageCreator(base)
        elif architecture in ("ppc",):
            self.imagecreator = ppcLiveImageCreator(base)
        elif architecture in ("ppc64",):
            self.imagecreator = ppc64LiveImageCreator(base)
        else:
            raise CreatorError("Architecture not supported!")

class ImageCreator(imgcreate.creator.ImageCreator):
    def __init__(self, cfg):
        self.cfg = cfg

        # FIXME: Need to override the kickstart object LiveCD-Tools uses, while maybe
        # all we should be doing is tell LiveCD-Tools what kickstart object it is we want to use.
        self.ks = self.cfg.ksobj.parser
        # /FIXME

        # FIXME: Why????????
        isoname = "%s-%s-Live-%s" % (self.cfg.iso_basename, self.cfg.version, self.cfg.architecture)
        # /FIXME

        self.name = isoname

        self.tmpdir = os.path.join(self.cfg.working_directory, "revisor-rundir")

        self.__builddir = None
        self.__bindmounts = []

        self.__sanity_check()

    def install(self, pbar=None):
        """install packages into target file system"""

        self.cfg.check_package_selection()

        self.runInstall(pbar=pbar)

        self.cfg.yumobj.closeRpmDB()

        self.cfg.yumobj.close()
        if os.access(self.cfg.yumobj.conf.installroot + "/etc/yum.conf", os.R_OK):
            os.unlink(self.cfg.yumobj.conf.installroot + "/etc/yum.conf")

        return True

    def transactionErrors(self, errs):
        # Cleanup
        self.cfg.yumobj.closeRpmDB()
        self.cfg.yumobj.close()
        if os.access(self.cfg.yumobj.conf.installroot + "/etc/yum.conf", os.R_OK):
            os.unlink(self.cfg.yumobj.conf.installroot + "/etc/yum.conf")

        try:
            self.log.error(_(   "Error encountered during installation of " + \
                                "the software you selected:\r\n\r\n" + \
                                "--> %s") % '\r\n--> '.join([message for (message, details,) in errs.value]), recoverable=False)
        except AttributeError:
            self.log.debug(_("An additional error in the error. The value of errs is: %s") % errs, level=9)
            self.log.error(_(   "An error occurred during the installation " + \
                                "of the software you selected, and an " + \
                                "additional error occurred trying to " + \
                                "describe what went wrong exactly."), recoverable=False)

    def runInstall(self, pbar=None):

        self.log.debug(_("Running package installation"))

        (res, resmsg) = self.cfg.yumobj.buildTransaction()
        if res != 2:
            msg = _("Unable to build transaction")
            for m in resmsg:
                msg = "%s %s" % (msg,m)
            self.log.error(msg, recoverable=False)
        else:
            self.log.debug(_("Successfully built transaction: ret %s, msg %s") % (res, ' '.join(resmsg)))

        if not pbar: pbar = self.base.progress_bar(_("Installing Software"))

        if self.cfg.gui_mode:
            tsprog = revisor.progress.TransactionProgressGUI(pbar, log=self.log)
        else:
            tsprog = revisor.progress.TransactionProgressCLI(pbar, log=self.log)

        del self.cfg.yumobj.ts
        self.cfg.yumobj.initActionTs() # make a new, blank ts to populate
        self.cfg.yumobj.populateTs(keepold=0)
        self.cfg.yumobj.ts.check() # required for ordering
        self.cfg.yumobj.ts.order() # order

        tsprog.tsInfo = self.cfg.yumobj.tsInfo

        try:
            tserrors = self.cfg.yumobj.runTransaction(tsprog)

        except yum.Errors.YumBaseError, err:
            self.log.debug("yum.Errors.YumBaseError: %s" % err, level=9)
            pbar.destroy()
            self.transactionErrors(err)

        except Exception, err:
            self.log.debug("Exception %s: %s" % (err.__class__,err), level=9)
            pbar.destroy()
            self.transactionErrors(err)

        pbar.destroy()

    def __sanity_check(self):
        """No sanity checks for L337 applications"""
        if ( self.cfg.ksobj._get("selinux","selinux") == revisor.kickstart.constants.SELINUX_ENFORCING ) or \
            ( self.cfg.ksobj._get("selinux","selinux") == revisor.kickstart.constants.SELINUX_PERMISSIVE ):
            if not os.path.exists("/selinux/enforce"):
                self.log.error(_("SELinux requested but not enabled on host"), recoverable=self.cfg.gui_mode)
        return

    def __get_instroot(self):
        return os.path.join(self.cfg.working_directory, "revisor")
    _instroot = property(__get_instroot)

    def __get_outdir(self):
        return os.path.join(self.cfg.working_directory, "revisor-livecd")
    _outdir = property(__get_outdir)

    def _mkdtemp(self, prefix="tmp-"):
        return self.__ensure_dir(prefix)

    def _mkstemp(self, prefix="tmp-"):
        return self.__ensure_dir(prefix)

    def _mktemp(self, prefix="tmp-"):
        return self.__ensure_dir(prefix)

    def __ensure_dir(self, prefix):
        """Ensure a directory is created, and empty"""
        directory = os.path.join(self.cfg.working_directory, "revisor-rundir", prefix)
        try:
            shutil.rmtree(directory)
        except:
            pass

        os.makedirs(directory)
        return directory

    def __ensure_builddir(self):
        if not self.__builddir is None:
            return

        try:
            self.__ensure_dir(self.tmpdir)
        except:
            pass

        self.__builddir = self.tmpdir

class LoopImageCreator(ImageCreator,imgcreate.creator.LoopImageCreator):
    def __init__(self, cfg=None):
        ImageCreator.__init__(self, cfg)

        image_size = self.cfg.payload_livemedia

        if imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024) > image_size:
            image_size = imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024)
            image_size_real_used = "%s %s" % revisor.misc.size_me(image_size)
            image_size_real_notused = "%s %s" % revisor.misc.size_me(self.cfg.payload_livemedia)
            self.log.debug(_("Setting self.cfg.payload_livemedia to %s (from 'part /' command in kickstart, instead of %s)") % (image_size_real_used,image_size_real_notused) , level=9)
        elif not self.cfg.mode_respin:
            image_size_real_used = "%s %s" % revisor.misc.size_me(image_size)
            image_size_real_notused = "%s %s" % revisor.misc.size_me(imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024))
            self.log.debug(_("Setting self.cfg.payload_livemedia to %s (from total installed size of RPMs, instead of %s)") % (image_size_real_used,image_size_real_notused), level=9)
        else:
            image_size = imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024)
            image_size_real_used = "%s %s" % revisor.misc.size_me(image_size)
            image_size_real_notused = "%s %s" % revisor.misc.size_me(self.cfg.payload_livemedia)
            self.log.debug(_("Setting self.cfg.payload_livemedia to %s (from 'part /' command in kickstart, as per the respin mode)") % (image_size_real_used), level=9)
            image_size = imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024)

        #if imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024) > image_size:
            #image_size = imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024)
            #image_size_real_used = "%s %s" % revisor.misc.size_me(image_size)
            #image_size_real_notused = "%s %s" % revisor.misc.size_me(self.cfg.payload_livemedia)
            #self.log.debug(_("Setting self.cfg.payload_livemedia to %s (from 'part /' command in kickstart, instead of %s)") % (image_size_real_used,image_size_real_notused) , level=9)
        #else:
            #image_size_real_used = "%s %s" % revisor.misc.size_me(image_size)
            #image_size_real_notused = "%s %s" % revisor.misc.size_me(imgcreate.kickstart.get_image_size(self.ks, 4096L*1024*1024))
            #self.log.debug(_("Setting self.cfg.payload_livemedia to %s (from total installed size of RPMs, instead of %s)") % (image_size_real_used,image_size_real_notused), level=9)

        self.__image_size = image_size

        self.__fstype = imgcreate.kickstart.get_image_fstype(self.ks, "ext3")

        self.log.debug(_("Filesystem type set to: %s") %(self.__fstype), level=7)

        self.__fslabel = self.cfg.lm_fs_label
        self.__minsize_KB = 0
        self.__blocksize = 4096

        self.__instloop = None
        self.__imgdir = None

        if not cfg:
            print "We expect to get a ConfigStore"
            sys.exit(1)

class LiveImageCreatorBase(imgcreate.live.LiveImageCreatorBase,LoopImageCreator):
    """
    This class is inherited and extended by architecture specific LiveImageCreator classes.
    As it inherits imgcreate.live.LiveImageCreatorBase, we have those functions available,
    but they may need to be overriden by our local functions.
    """
    def __init__(self, cfg):
        """
            In order of appearance:
            - ConfigStore
        """
        LoopImageCreator.__init__(self, cfg)

        self.skip_compression = self.cfg.lm_skip_fs_compression

        self.skip_minimize = self.cfg.lm_ignore_deleted

        try:
            self._timeout = int(self.cfg.ksobj._get("bootloader","timeout"))
        except TypeError, e:
            self._timeout = int(self.cfg.lm_bootloader_timeout)

# Original
#        self._default_kernel = kickstart.get_default_kernel(self.ks, "kernel")

        # FIXME: How does this take into account self.cfg.lm_preferred_kernel?
        self._default_kernel = self.cfg.ksobj._get("bootloader", "default") or "kernel"

        self.__isodir = None

        self.__modules = ["=ata", "sym53c8xx", "aic7xxx", "=usb", "=firewire", "=mmc", "=pcmcia"]
        self.__modules.extend(imgcreate.kickstart.get_modules(self.cfg.ksobj))

        self._isofstype = "iso9660"

class x86LiveImageCreator(LiveImageCreatorBase,imgcreate.live.x86LiveImageCreator):
    def __init__(self, base=None):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log
        LiveImageCreatorBase.__init__(self, base.cfg)

class ppcLiveImageCreator(LiveImageCreatorBase):
    def __init__(self, base=None):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log
        LiveImageCreatorBase.__init__(self, base.cfg)

class ppc64LiveImageCreator(ppcLiveImageCreator):
    def __init__(self, base=None):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log
        ppcLiveImageCreator.__init__(self, base.cfg)

# The LiveImageCreator object
arch = rpmUtils.arch.getBaseArch()
if arch in ("i386", "i586", "i686", "x86_64"):
    LiveImageCreator = x86LiveImageCreator
elif arch in ("ppc",):
    LiveImageCreator = ppcLiveImageCreator
elif arch in ("ppc64",):
    LiveImageCreator = ppc64LiveImageCreator
else:
    raise CreatorError("Architecture not supported!")
