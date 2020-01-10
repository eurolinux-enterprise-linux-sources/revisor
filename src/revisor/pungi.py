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

import glob
import logging
import os
import re
import revisor.misc
import shutil
import subprocess
import sys
import libxml2
from revisor import splittree

# Translation
from revisor.translate import _, N_

class RevisorPungi:
    def __init__(self, base):
        self.base = base
        self.cfg = base.cfg
        self.log = base.log

        self.destdir = os.path.join(self.cfg.working_directory,"revisor-install")
        self.archdir = os.path.join(self.destdir,
                                   self.cfg.version,
                                   self.cfg.model,
                                   self.cfg.architecture)

        self.topdir = os.path.join(self.archdir, 'os')
        self.isodir = os.path.join(self.archdir, 'iso')

        self.workdir = os.path.join(self.destdir,
                                    'work',
                                    self.cfg.model,
                                    self.cfg.architecture)

        self.common_files = []
        self.infofile = os.path.join(self.destdir, self.cfg.version, self.cfg.model, '.composeinfo')

        if not os.path.exists(self.destdir):
            try:
                os.makedirs(self.destdir)
            except OSError, e:
                self.log.error(_("Error: Cannot create destination dir %s") % self.destdir)
        else:
            # Empty it
            try:
                shutil.rmtree(self.destdir)
            except OSError, e:
                self.log.error(_("Error: Cannot remove destination dir %s") % self.destdir)
            # Recreate it
            try:
                os.makedirs(self.destdir)
            except OSError, e:
                self.log.error(_("Error: Cannot recreate destination dir %s") % self.destdir)

    def writeinfo(self, line):
        """Append a line to the infofile in self.infofile (for SNAKE?)"""

        f=open(self.infofile, "a+")
        f.write(line.strip() + "\n")
        f.close()

    def mkrelative(self, subfile):
        """Return the relative path for 'subfile' underneath the version dir."""

        basedir = os.path.join(self.destdir, self.cfg.version, self.cfg.model)
        if subfile.startswith(basedir):
            return subfile.replace(basedir + os.path.sep, '')


    def filterComps(self, comps, new_comps, available_packages):
        '''Filters out comps.xml.
        Only packages available on the installation media will be considered, all other will be deleted.'''

        doc = libxml2.parseFile(comps)

        # remove extra packages
        nodes = doc.walk_breadth_first()
        for node in nodes:
            if (node.type == 'element') and (node.name == 'packagereq') and (node.get_content() not in available_packages):
                node.unlinkNode()

        # remove groups with empty <packagelist> nodes
        removed_groups = []
        pkglistNodes = []
        nodes = doc.walk_breadth_first()
        for node in nodes:
            if (node.type == 'element') and (node.name == 'packagelist'):
                pkglistNodes.append(node)

        for node in pkglistNodes:
            # unlinkNode leaves blanck lines in tags so we use strip()
            if (node.get_content().strip() == ''):
                group = node.parent
            if (group.type == 'element') and (group.name == 'group'):
                   giter = group.walk_depth_first()
                   for gnode in giter:
                       if (gnode.type == 'element') and (gnode.name == 'id'):
                           # mark this group as deleted
                           removed_groups.append(gnode.get_content())
                           break
                   group.unlinkNode()

        # remove group ids that were already deleted because they were empty
        nodes = doc.walk_breadth_first()
        for node in nodes:
            if (node.type == 'element') and (node.name == 'groupid') and (node.get_content() in removed_groups):
                node.unlinkNode()

        # remove categories with empty <grouplist> tags
        grouplistNodes = []
        nodes = doc.walk_breadth_first()
        for node in nodes:
            if (node.type == 'element') and (node.name == 'grouplist'):
                grouplistNodes.append(node)

        for node in grouplistNodes:
            # unlinkNode leaves blanck lines in tags so we use strip()
            if (node.get_content().strip() == ''):
                category = node.parent
            if (category.type == 'element') and (category.name == 'category'):
                category.unlinkNode()

        # all extra data is removed leaving a lot of blank space (node.unlinkNode)
        # remove it to improve human readability
        nodes = doc.walk_breadth_first()
        for node in nodes:
            if (node.type == 'text') and (node.get_content().strip() == ''):
                node.unlinkNode()

        #overwrite existing file and exit
        doc.saveFormatFile(new_comps, True)
        doc.freeDoc()
        return

    def doCreateRepo(self, database=True, basedir=None, callback=None, comps=True, repoview=True):

        if basedir == None:
            basedir = self.topdir

        # Get our comps file
        comps = self.cfg.get_comps()

        # create command to create repodata for the tree
        createrepo = ['/usr/bin/createrepo']
        createrepo.append('-v')

        if database:
            createrepo.append('--database')

        createrepo.append('--groupfile')
        createrepo.append(comps)

        createrepo.append(basedir)

        if comps:
            # FIXME: Watch for https://bugzilla.redhat.com/show_bug.cgi?id=429509
            if hasattr(self.cfg.yumobj.comps,"xml"):
                ourcomps = open(comps, 'w')
                ourcomps.write(self.cfg.yumobj.comps.xml())
                ourcomps.close()

            # Let's clean up the comps file before moving anything around
            # Run the xslt filter over our comps file
            compsfilter = ['/usr/bin/xsltproc', '--novalid']
            compsfilter.append('-o')
            compsfilter.append(comps)
            if os.access('/usr/share/revisor/comps-cleanup.xsl', os.R_OK):
                compsfilter.append('/usr/share/revisor/comps-cleanup.xsl')
            elif os.access('/usr/share/revisor/comps/comps-cleanup.xsl', os.R_OK):
                compsfilter.append('/usr/share/revisor/comps/comps-cleanup.xsl')
            compsfilter.append(comps)

            self.base.run_command(compsfilter)

            if self.cfg.comps_filter:
                self.filterComps(comps, comps, self.cfg.available_packages)

        # run the command
        self.base.run_command(createrepo, rundir=self.topdir, callback=callback)

        if repoview:
            if self.cfg.repoview:
                # setup the repoview call
                repoview = ['/usr/bin/repoview']
                repoview.append('--quiet')

                repoview.append('--state-dir')
                repoview.append(os.path.join(cachedir, 'repoviewcache'))

                if repoviewtitle:
                    repoview.append('--title')
                    repoview.append(repoviewtitle)

                repoview.append(path)

                # run the command
                self.base.run_command(repoview, rundir=self.topdir, callback=callback)

    def doCreateMediarepo(self, split=False):
        """Create the split metadata for the isos"""


        discinfo = open(os.path.join(self.topdir, '.discinfo'), 'r').readlines()
        mediaid = discinfo[0].rstrip('\n')

        compsfile = os.path.join(self.workdir, '%s-%s-comps.xml' % (self.config.get('default', 'name'), self.config.get('default', 'version')))

        if not split:
            pypungi._ensuredir('%s-disc1' % self.topdir, self.logger,
                               clean=True) # rename this for single disc
            path = self.topdir
            basedir=None
        else:
            path = '%s-disc1' % self.topdir
            basedir = path
            split=[]
            for disc in range(1, self.config.getint('default', 'discs') + 1):
                split.append('%s-disc%s' % (self.topdir, disc))

        # set up the process
        self._makeMetadata(path, self.config.get('default', 'cachedir'), compsfile, repoview=False,
                                                 baseurl='media://%s' % mediaid,
                                                 output='%s-disc1' % self.topdir,
                                                 basedir=basedir, split=split, update=False)

        # Write out a repo file for the disc to be used on the installed system
        self.logger.info('Creating media repo file.')
        repofile = open(os.path.join(self.topdir, 'media.repo'), 'w')
        repocontent = """[InstallMedia]
name=%s %s
mediaid=%s
metadata_expire=-1
enabled=0
gpgcheck=0
cost=500
""" % (self.config.get('default', 'name'), self.config.get('default', 'version'), mediaid)

        repofile.write(repocontent)
        repofile.close()

    def doBuildinstall(self, callback=None):
        """Run anaconda-runtime's buildinstall on the tree."""
        buildinstall = []

        if self.cfg.debuglevel == 9:
            buildinstall.extend(['bash', '-x'])

        # setup the buildinstall call
        if os.access("scripts/%s-buildinstall" % self.cfg.version_from, os.R_OK):
            buildinstall.extend([os.path.abspath("scripts/%s-buildinstall" % self.cfg.version_from)])
        elif os.access("/usr/lib/revisor/scripts/%s-buildinstall" % self.cfg.version_from, os.R_OK):
            buildinstall.extend(["/usr/lib/revisor/scripts/%s-buildinstall" % self.cfg.version_from])
        else:
            buildinstall.extend(['/usr/lib/anaconda-runtime/buildinstall'])
        #buildinstall.append('TMPDIR=%s' % self.workdir) # TMPDIR broken in buildinstall

        # FIXME: Determine options from the anaconda-runtime version
        if self.cfg.version_from in [ "F9", "F10", "F11", "F12", "F13", "DEVEL" ]:
            buildinstall.append('--debug')

        if self.cfg.version_from in [ "RHEL5" ]:
            buildinstall.append('--comps')
            buildinstall.append('repodata/comps.xml')

        buildinstall.append('--product')
        buildinstall.append(self.cfg.product_name)

        if not self.cfg.model == "":
            buildinstall.append('--variant')
            buildinstall.append(self.cfg.model)

        buildinstall.append('--version')
        buildinstall.append(self.cfg.version)

        buildinstall.append('--release')
        buildinstall.append('"%s %s"' % (self.cfg.product_name, self.cfg.version))

        # FIXME: Everything < F9 needs --prodpath
        if not self.cfg.version_from in [ "F9", "F10", "F11", "F12", "F13", "DEVEL" ]:
            buildinstall.append('--prodpath')
            buildinstall.append(self.cfg.product_path)

        if self.cfg.install_nogr:
            buildinstall.append('--nogr')

        self.base.plugins.exec_hook('buildinstall_append')

        if hasattr(self.cfg,"buildinstall_append"):
            buildinstall.extend(self.cfg.buildinstall_append)

        if hasattr(self.cfg,'bugurl'):
            buildinstall.append('--bugurl')
            buildinstall.append('%s' % self.cfg.bugurl)

        if self.cfg.version_from in [ "F9" ]:
            (repository_baseurls,repository_mirrorlists) = revisor.misc.get_repourls(self.cfg.yumobj)
            for mlist in repository_mirrorlists:
                buildinstall.extend(['--mirrorlist', '%s' % mlist])
        else:
            buildinstall.append('--yumconf')
            buildinstall.append('%s' % self.cfg.main)

        buildinstall.append(self.topdir)

        if self.cfg.version_from in [ "F9" ]:
            for burl in repository_baseurls:
                buildinstall.append('%s' % burl)

        # run the command
        self.base.run_command(buildinstall, callback=callback)

        self.writeinfo('tree: %s' % self.mkrelative(self.topdir))

    def doGetRelnotes(self, callback=None):
        """Get extra files from packages in the tree to put in the topdir of
           the tree."""

        self.log.debug(_("Getting relnotes..."), level=4)

        docsdir = os.path.join(self.workdir, 'docs')
        os.makedirs(docsdir)

        # Expload the packages we list as relnote packages
        pkgs = os.listdir(os.path.join(self.topdir, self.cfg.product_path))

        self.log.debug(str(pkgs))
        rpm2cpio = ['/usr/bin/rpm2cpio']
        cpio = ['cpio', '-imud']

        for pkg in pkgs:
            for pattern in self.cfg.release_pkgs.split():
                if re.match(pattern, pkg):
                    extraargs = [os.path.join(self.topdir, self.cfg.product_path, pkg)]
                    try:
                        p1 = subprocess.Popen(rpm2cpio + extraargs, cwd=docsdir, stdout=subprocess.PIPE)
                        (out, err) = subprocess.Popen(cpio, cwd=docsdir, stdin=p1.stdout, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True).communicate()
                    except:
                        self.log.error(_("An error occured extracting the release files: %s") % err)

                    self.log.debug(out)

        # Walk the tree for our files
        for dirpath, dirname, filelist in os.walk(docsdir):
            for directory in dirname:
                for pattern in self.cfg.release_files.split():
                    if re.match(pattern,directory) and not os.path.exists(os.path.join(self.topdir, directory)):
                        self.log.debug(_("Copying %s") % directory)
                        shutil.copytree(os.path.join(dirpath, directory), os.path.join(self.topdir, directory))

            for filename in filelist:
                for pattern in self.cfg.release_files.split():
                    if re.match(pattern,filename) and not os.path.exists(os.path.join(self.topdir, filename)):
                        self.log.debug(_("Copying release note file %s") % filename)
                        if os.access(os.path.join(dirpath, filename), os.R_OK):
                            shutil.copy(os.path.join(dirpath, filename), os.path.join(self.topdir, filename))
                        else:
                            self.log.debug(_("File %s not readable") % os.path.join(dirpath, filename), level=2)
                        self.common_files.append(filename)

        self.log.debug(str(self.common_files))

    def doCopyDir(self, copy_dir=None):
        if not copy_dir:
            return

        if not os.access(self.cfg.copy_dir, os.R_OK):
            self.log.error(_("Could not access directory %s, cannot copy extra files onto the media.") % self.cfg.copy_dir)
            return

        try:
            os.makedirs(os.path.join(self.topdir,"files"))
        except:
            self.log.error(_("Could not create files/ directory: %s") % os.path.join(self.topdir,"files"))

        if not self.cfg.copy_dir == "":
            if os.access(self.cfg.copy_dir, os.R_OK):
                # So what is the destination directory?
                src_dir = self.cfg.copy_dir
                dst_dir = "%s/files/%s"

                for root, dirs, files in os.walk(src_dir):
                    real_dst = dst_dir % (self.topdir, root.replace(src_dir,''))
                    if not os.access(real_dst, os.R_OK):
                        self.log.debug(_("Creating %s") % real_dst)
                        os.makedirs(real_dst)

                    for file in files:
                        self.log.debug(_("Copying %s to %s") % (os.path.join(root,file), os.path.join(real_dst,file)))
                        shutil.copyfile(os.path.join(root,file), os.path.join(real_dst,file))

            else:
                self.log.warning(_("copy_dir '%s' not accessible") % self.cfg.copy_dir)

    def doSplittree(self, media_size=0, discdir="unified", callback=None):
        """Use anaconda-runtime's splittree to split the tree into appropriate
        sized chunks."""

        # Hey I get size in bytes but I want MBytes
        timber = splittree.Timber()
        timber.cfg = self.cfg
        timber.log = self.log
        timber.arch = self.cfg.architecture
        timber.disc_size = float(media_size / 1024 / 1024)
        timber.target_size = float(media_size)
        timber.total_discs = int(self.cfg.mediatypes[discdir]["discs"])
        timber.bin_discs = int(self.cfg.mediatypes[discdir]["discs"])
        timber.src_discs = 0
        timber.release_str = '%s %s' % (self.cfg.product_name, self.cfg.version)
        timber.package_order_file = self.cfg.pkgorder_file
        timber.dist_dir = "%s-%s" % (self.topdir,discdir)
        self.log.debug("dist_dir is %s" % timber.dist_dir)
        timber.src_dir = os.path.join(self.destdir, self.cfg.version, self.cfg.model, 'source', 'SRPMS')
        self.log.debug("src_dir is %s" % timber.src_dir)
        timber.product_path = self.cfg.product_path
        timber.common_files = self.common_files
        #timber.reserve_size =

        # Pretend we're not ok, yet
        we_are_ok = False

        while not we_are_ok:
            # But prevent infinite loops
            we_are_ok = True
            timber.createSplitDirs()
            timber.splitRPMS()

            # Now that we've split, examine the size of all disc directories
            # and make sure they fit
            for disc in range(1, timber.total_discs + 1):
                if not we_are_ok: continue

                disc_size = timber.getSize("%s-disc%d" % (timber.dist_dir, disc), blocksize=True)
                #disc_size = timber.getSize("%s-disc%d" % (timber.dist_dir, disc))

                if disc_size > timber.target_size:
                    self.log.debug(_("Disc %s #%d is oversized (%r > %r)") % (self.cfg.mediatypes[discdir]["label"], disc, disc_size, timber.target_size), level=9)

                    # Destroy the old disc directories
                    for i in range(1, timber.total_discs + 1):
                        self.log.debug(_("Removing tree %s") % ("%s-%s-disc%d" % (self.topdir,discdir,i)), level=9)
                        shutil.rmtree("%s-%s-disc%d" % (self.topdir,discdir,i))

                    self.cfg.mediatypes[discdir]["discs"] += 1
                    timber.total_discs = self.cfg.mediatypes[discdir]["discs"]
                    timber.bin_discs = self.cfg.mediatypes[discdir]["discs"]
                    we_are_ok = False
                elif disc_size <= timber.reserve_size:
                    self.log.debug(_("Disc %s #%d is undersized (%r <= %r)") % (self.cfg.mediatypes[discdir]["label"], disc, disc_size, timber.reserve_size), level=9)

                    # Destroy the old disc directories
                    for i in range(1, timber.total_discs + 1):
                        self.log.debug(_("Removing tree %s") % ("%s-%s-disc%d" % (self.topdir,discdir,i)), level=9)
                        shutil.rmtree("%s-%s-disc%d" % (self.topdir,discdir,i))

                    self.cfg.mediatypes[discdir]["discs"] -= 1
                    timber.total_discs = self.cfg.mediatypes[discdir]["discs"]
                    timber.bin_discs = self.cfg.mediatypes[discdir]["discs"]
                    we_are_ok = False
                else:
                    self.log.debug(_("Disc %s #%d is OK in size (%r <= %r)") % (self.cfg.mediatypes[discdir]["label"], disc, disc_size, timber.target_size), level=9)

        if (timber.src_discs != 0):
            timber.splitSRPMS()
        self.log.debug("%s" % (timber.logfile), level=9)

    def doCreateSplitrepo(self, discdir="unified", callback=None):
        """Create the split metadata for the isos"""

        if int(self.cfg.mediatypes[discdir]["discs"]) > 1:
            discinfo = open('%s-%s-disc1/.discinfo' % (self.topdir,discdir), 'r').readlines()
        else:
            discinfo = open(os.path.join(self.topdir, '.discinfo'), 'r').readlines()

        mediaid = discinfo[0].rstrip('\n')

        # set up the process
        createrepo = ['/usr/bin/createrepo']
        createrepo.append('-v')
        createrepo.append('--database')

        createrepo.append('--groupfile')
        createrepo.append(self.cfg.comps)

        createrepo.append('--baseurl')
        createrepo.append('media://%s' % mediaid)

        createrepo.append('--outputdir')
        if int(self.cfg.mediatypes[discdir]["discs"]) == 1:
            if os.access('%s-%s-disc1' % (self.topdir,discdir), os.R_OK):
                shutil.rmtree('%s-%s-disc1' % (self.topdir,discdir))
            os.makedirs('%s-%s-disc1' % (self.topdir,discdir))
        createrepo.append('%s-%s-disc1' % (self.topdir,discdir))

        createrepo.append('--basedir')
        if int(self.cfg.mediatypes[discdir]["discs"]) == 1:
            createrepo.append(self.topdir)
            createrepo.append(self.topdir)
        else:
            createrepo.append('%s-%s-disc1' % (self.topdir,discdir))

        if int(self.cfg.mediatypes[discdir]["discs"]) > 1:
            createrepo.append('--split')

            for disc in range(1, int(self.cfg.mediatypes[discdir]["discs"]) + 1):
                createrepo.append('%s-%s-disc%s' % (self.topdir, discdir, disc))

        # run the command
        self.base.run_command(createrepo, callback=callback)

    def forward_tick_discinfo(self, mt):
        """One ugly hack to prevent anaconda shitting ITSELF concerning .discinfo's ALL"""

        self.log.debug(_("Hacking anaconda's .discinfo because it'll shit itself if it reads it's own output"))

        discinfofile = "%s-%s/%s" % (self.topdir, mt["discdir"], ".discinfo")

        content = open(discinfofile, 'r').readlines()

        shutil.copy(discinfofile,"%s-%s-%s" % (self.topdir, mt["discdir"], "discinfo"))
        try:
            content[content.index('ALL\n')] = ','.join([str(x) for x in range(1, mt["discs"])]) + '\n'
	except:
            # This could mean there is no "ALL\n" in the .discinfo (either F7 or fixed in anaconda-runtime)
            pass

        open(discinfofile, 'w').writelines(content)

    def back_tick_discinfo(self, mt):
        """One ugly hack to prevent anaconda shitting ITSELF concerning .discinfo's ALL"""
        original_discinfofile = "%s-%s-%s" % (self.topdir, mt["discdir"], "discinfo")
        os.unlink("%s-%s/%s" % (self.topdir, mt["discdir"], ".discinfo"))
        shutil.copy(original_discinfofile,"%s-%s/%s" % (self.topdir, mt["discdir"], ".discinfo"))

    def doCreateIso(self, mediatype=None, disc=0,  callback=None, is_source=False):

        mt = self.cfg.mediatypes[mediatype]
        # Based on what we have, create some names and stuff
        isoname = "%s-%s-%s" % (self.cfg.iso_basename, self.cfg.version, self.cfg.architecture)
        if len(mt["label"]) > 1:
            isoname = "%s-%s" % (isoname, mt["label"])
        if mt["discs"] > 1:
            isoname = "%s%d" % (isoname, disc)
        else:
            self.forward_tick_discinfo(mt)

        isoname = "%s.iso" % isoname

        isofile = os.path.join(self.cfg.destination_directory,"iso",isoname)

        extraargs = []
        if disc == 1 or disc == 0:
            if self.cfg.architecture == 'i386' or self.cfg.architecture == 'x86_64':
                extraargs.extend(self.cfg.x86bootargs)
            elif self.cfg.architecture == 'ia64':
                extraargs.extend(self.cfg.ia64bootargs)
            elif self.cfg.architecture == 'ppc':
                extraargs.extend(self.cfg.ppcbootargs)
                extraargs.append(os.path.join('%s' % (self.topdir), "ppc/mac"))

        extraargs.append('-V')
        volume = "%s %s %s" % (self.cfg.iso_label, self.cfg.version, self.cfg.architecture)
        if mt["label"] > 1:
            volume = "%s %s" % (volume, mt["label"])
        if mt["discs"] > 1:
            volume = "%s%d" % (volume, disc)

        extraargs.extend(['"%s"' % volume])
        extraargs.extend(['-o', isofile])

        if not self.cfg.include_bootiso:
            extraargs.extend(['-m', '*.iso'])

        if disc == 0:
            extraargs.append(self.topdir)
            num_packages = len(os.listdir(os.path.join(self.topdir, self.cfg.product_path)))
        else:
            extraargs.append("%s-%s-disc%s" % (self.topdir, mt["discdir"], disc))
            num_packages = len(os.listdir(os.path.join('%s-%s-disc%s/' % (self.topdir, mt["discdir"], disc), self.cfg.product_path)))

        self.cfg.built_iso_images.append({'type': mediatype, 'location': isofile, 'packages': num_packages, 'is_source': is_source})

        self.base.run_command(self.cfg.cmd_mkisofs + extraargs, callback=callback)

        if mt["discs"] < 2:
            self.back_tick_discinfo(mt)

    def create_rescue_disk(self, callback=None):
        # Now make rescue images
        if not self.cfg.architecture == 'source' and \
            os.path.exists('/usr/lib/anaconda-runtime/mk-rescueimage.%s' % self.cfg.architecture):
            isoname = '%s-%s-%s-rescuecd.iso' % (self.cfg.iso_basename,
                self.cfg.version, self.cfg.architecture)
            isofile = os.path.join(self.cfg.destination_directory,"iso",isoname)

            # make the rescue tree
            rescue = ['/usr/lib/anaconda-runtime/mk-rescueimage.%s' % self.cfg.architecture]
            rescue.append(self.topdir)
            rescue.append(self.workdir)
            rescue.append(self.cfg.iso_basename)
            rescue.append(self.cfg.product_path)

            # run the command
            self.base.run_command(rescue)

            # write the iso
            extraargs = []

            if self.cfg.architecture == 'i386' or self.cfg.architecture == 'x86_64':
                extraargs.extend(self.cfg.x86bootargs)
            elif self.cfg.architecture == 'ia64':
                extraargs.extend(self.cfg.ia64bootargs)
            elif self.cfg.architecture == 'ppc':
                extraargs.extend(self.cfg.ppcbootargs)
                extraargs.append(os.path.join(self.workdir, "%s-rescueimage" % self.cfg.architecture, "ppc/mac"))

            extraargs.append('-V')
            extraargs.append('"%s %s %s Rescue"' % (self.cfg.product_name,
                    self.cfg.version, self.cfg.architecture))

            extraargs.append('-o')
            extraargs.append(os.path.join(self.cfg.destination_directory,"iso",isofile))

            extraargs.append(os.path.join(self.workdir, "%s-rescueimage" % self.cfg.architecture))

            # run the command
            self.base.run_command(self.cfg.cmd_mkisofs + extraargs, callback=callback)

            # implant md5 for mediacheck on all but source arches
            if not self.cfg.architecture == 'source':
                self.base.run_command(['/usr/lib/anaconda-runtime/implantisomd5', isofile])

            # shove the sha1sum into a file
            if os.access(os.path.join(self.cfg.destination_directory,"iso","SHA1SUM"), os.R_OK):
                sha1file = open(os.path.join(self.cfg.destination_directory,"iso","SHA1SUM"), 'a')
            else:
                sha1file = open(os.path.join(self.cfg.destination_directory,"iso","SHA1SUM"), 'w')

            self.base.run_command(['/usr/bin/sha1sum', '-b', isoname], rundir=os.path.join(self.cfg.destination_directory,"iso"), output=sha1file)
            sha1file.close()

    def cleanup(self):
# FIXME
        # Do some clean up
        dirs = os.listdir(self.archdir)

        for directory in dirs:
            if directory.startswith('os-disc') or directory.startswith('SRPM-disc'):
                shutil.move(os.path.join(self.archdir, directory), os.path.join(self.workdir, directory))

    def ALL_workaround(self):
        """ Workaround the anaconda ALL "bug" """
        discinfofile = os.path.join(self.topdir, ".discinfo")
        content = open(discinfofile, 'r').readlines()
        #shutil.move(discinfofile, os.path.join(self.topdir, "discinfo.old"))
        try:
            content[content.index('ALL\n')] = '1\n'
        except:
            pass

        open(discinfofile, 'w').writelines(content)
