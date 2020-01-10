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

import revisor.image
import imgcreate
import os, sys
import subprocess
import libvirt
import virtinst

# Translation
from revisor.translate import _, N_

class RevisorVirt:
    def __init__(self):
        pass

    def check_options(self, cfg, cli_options):
        """Check the options in cli_options"""
        self.cfg = cfg

        pass

    def check_destination_directory(self):
        """Check if the destination directory exists. If it does, set self.complain_destination_directory"""
        self.complain_destination_directory = False

        if os.access(os.path.join(self.cfg.destination_directory,"xen"), os.R_OK):
            if self.cfg.media_virtual_xen:
                self.complain_destination_directory = True
        if os.access(os.path.join(self.cfg.destination_directory,"kvm"), os.R_OK):
            if self.cfg.media_virtual_kvm:
                self.complain_destination_directory = True

    def delete_destination_directory(self):
        """Delete and re-create the destination directory"""
        if os.access(os.path.join(self.cfg.destination_directory,"xen"), os.R_OK):
            if self.cfg.media_virtual_xen:
                shutil.rmtree(os.path.join(self.cfg.destination_directory,"xen"))
        if os.access(os.path.join(self.cfg.destination_directory,"kvm"), os.R_OK):
            if self.cfg.media_virtual_kvm:
                shutil.rmtree(os.path.join(self.cfg.destination_directory,"kvm"))

        if not os.access(os.path.join(self.cfg.destination_directory,"xen"), os.R_OK) and self.cfg.media_virtual_xen:
            while not os.access(os.path.join(self.cfg.destination_directory,"xen"), os.R_OK):
                try:
                    os.makedirs(os.path.join(self.cfg.destination_directory,"xen"))
                except:
                    self.log.error(_("Cannot access %s, please check the permissions so we can try again." % os.path.join(self.cfg.destination_directory,"xen")))

        if not os.access(os.path.join(self.cfg.destination_directory,"kvm"), os.R_OK) and self.cfg.media_virtual_kvm:
            while not os.access(os.path.join(self.cfg.destination_directory,"kvm"), os.R_OK):
                try:
                    os.makedirs(os.path.join(self.cfg.destination_directory,"kvm"))
                except:
                    self.log.error(_("Cannot access %s, please check the permissions so we can try again." % os.path.join(self.cfg.destination_directory,"kvm")))

    def set_defaults(self, defaults):
        defaults.media_virtualization = False
        defaults.media_virtual = False
        defaults.media_virtual_xen = False
        defaults.media_virtual_kvm = False
        defaults.media_virtual_vmware_appliance = False
        defaults.media_virtual_vmware_guest = False

    def add_options(self, parser):
        """Adds a Virtualization Media Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""
        virt_group = parser.add_option_group(_("Virtualization Media Options"))

        ## Xen
        virt_group.add_option(  "--virt-xen",
                                dest    = "virt_xen",
                                action  = "store",
                                default = "",
                                help    = _("Build Xen virtual machine. (not implemented yet)"),
                                metavar = "[guest name]")

        virt_group.add_option(  "--virt-xen-size",
                                dest    = "virt_xen_size",
                                action  = "store",
                                default = "3000",
                                help    = _("Xen virtual machine drive size, in MB. (Default: 3000MB) (not implemented yet)"),
                                metavar = "[drive size in MB]")

        ## KVM
        virt_group.add_option(  "--virt-kvm",
                                dest    = "virt_kvm",
                                action  = "store",
                                default = "",
                                help    = _("Build KVM virtual machine. (not implemented yet)"),
                                metavar = "[guest name]")

        virt_group.add_option(  "--virt-kvm-size",
                                dest    = "virt_kvm_size",
                                action  = "store",
                                default = "3000",
                                help    = _("KVM virtual machine drive size, in MB. (Default: 3000MB) (not implemented yet)"),
                                metavar = "[drive size in MB]")

        ## Global
        virt_group.add_option(  "--virt-fstype",
                                dest    = "virt_fstype",
                                action  = "store",
                                default = "ext3",
                                help    = _("Virtual machine file system type. (Default: ext3) (not implemented yet)"),
                                metavar = "[filesystem type]")

        virt_group.add_option(  "--virt-sparse",
                                dest    = "virt_sparse",
                                action  = "store_true",
                                default = False,
                                help    = _("Make virtual machine drive a sparse filesystem. (not implemented yet)"))

        virt_group.add_option(  "--virt-stateless",
                                dest    = "virt_stateless",
                                action  = "store_true",
                                default = False,
                                help    = _("Make virtual machine stateless (changes do not persist.) (not implemented yet)"))

        virt_group.add_option(  "--virt-appliance",
                                dest    = "virt_appliance",
                                action  = "store_true",
                                default = False,
                                help    = _("Build virtual machine as an appliance using a simple raw drive image and yum. (Doesn't require virt. tech. to be running locally.) (not implemented yet)"))

    def provision_virtual_drive(self, partlayout=None):
        """ Setup a virtual drive to setup a virtual machine inside. Returns the drive object."""

        fslabel = "revisor"
        virtual_type = ""

        if not self.cfg.virt_xen == "":
            virtual_type = "xen"
            lofile = os.path.join(self.cfg.destination_directory, 'virt-xen', '%s.img' % self.cfg.virt_xen)
            mountdir = os.path.join(self.cfg.working_directory, 'virt-xen-%s' % self.cfg.virt_xen)
            fslabel = self.cfg.virt_xen
            size = self.cfg.virt_xen_size
        elif not self.cfg.virt_kvm == "":
            virtual_type = "kvm"
            lofile = os.path.join(self.cfg.destination_directory, 'virt-kvm', '%s.img' % self.cfg.virt_kvm)
            mountdir = os.path.join(self.cfg.working_directory, 'virt-kvm-%s' % self.cfg.virt_kvm)
            fslabel = self.cfg.virt_kvm
            size = self.cfg.virt_kvm_size
        else:
            print "Oh noes!"
            sys.exit(1)

        virt_gear_drive = revisor.modvirt.RevisorLoopbackMount(virtual_type, lofile, mountdir, size, fslabel, self.cfg.virt_fstype, self.cfg)
        virt_gear_drive.partlayout = partlayout
        return virt_gear_drive

    def provision_virtual_machine(self, virtual_drive=None):
        """ Setup and build a virtual machine. """
        size = 0
        if not self.cfg.virt_xen == "":
            size = self.cfg.virt_xen_size
        elif not self.cfg.virt_kvm == "":
            size = self.cfg.virt_kvm_size

        if self.cfg.virt_appliance:
            # Use a raw disk and yum, with some other magic, to build the guest image.

            #FIXME: Actually build the part data dict
            partdata = None
            #partdata = self.cfg.ksobj._set("something","somethingelse",value)

            #FIXME: If size is not 0, make sure our partition layout will fit in the requested size or bail

            if not virtual_drive:
                virtual_drive = self.provision_virtual_drive(partdata)
                virtual_drive.setup()

            virtual_drive.mount_drive(offset=32256)
            #virtual_drive.mount_drive()
            virtual_drive.prime_drive()
            install_root = virtual_drive.mountdir
            print install_root
        else:
            # Use the virtual technology to run an auto installing ISO image and build the virtual guest.
            virtual_type = ""
            name = ""
            install_memory = 386
            vcpus = 1
            if not self.cfg.virt_xen == "":
                virtual_type = "xen"
                name = self.cfg.virt_xen
            elif not self.cfg.virt_kvm == "":
                virtual_type = "kvm"
                name = self.cfg.virt_kvm

            # Get a virtual drive to install onto
            virtual_drive = self.provision_virtual_drive()
            virtual_disk = virtual_drive.get_disk()

            # Get the ISO image to install from
            iso_image = ""
            for image in self.cfg.built_iso_images:
                if image["type"] == "dvd": # Maybe we need to create a special ISO image for this task?
                    iso_image = image["location"]

            virtual_machine = None
            #FIXME: Setup a better server connection then just the default
            server = revisor.modvirt.virtinst.util.default_connection()
            conn = revisor.modvirt.libvirt.open(server)

            # FIXME: We should really test some of the following:
            # modvirt.virtinst.util. [...]
            # is_pae_capable()
            # is_hvm_capable()
            # is_kqemu_capable()
            # is_kvm_capable()
            # is_blktap_capable()

            if virtual_type is "xen":
                # Setup the virtual machine
                # FIXME: (#235) try:
                virtual_machine = revisor.modvirt.RevisorParaVirtual(type=virtual_type, connection=conn)
                # except:
            elif virtual_type is "kvm":
                # Setup the virtual machine
                # FIXME: (#235) try:
                virtual_machine = revisor.modvirt.RevisorFullVirtual(type=virtual_type, connection=conn)
                # except:

            if not virtual_machine:
                self.log.error(_("Unable to create virtual machine instance."), recoverable=False)

            virtual_machine.set_log(self.log)
            virtual_machine.disks.append(virtual_disk)
            virtual_machine.iso = iso_image
            virtual_machine.set_name(name)
            virtual_machine.set_memory(install_memory)
            virtual_machine.set_vcpus(vcpus)

            ## FIXME: We might want to connect the user to the install session if we are in GUI mode? Offer info about vnc if in CLI mode?
            # Progress bars are going to be a PITA for this.
            virtual_machine.set_graphics("vnc") # So we can connect while testing and see what is going wrong/right
            ##

            virtual_machine.start_virtual_machine_installer()


class RevisorLoopbackMount(imgcreate.fs.LoopbackMount):
    def __init__(self, type, lofile, mountdir, size, fslabel, fstype, cfg):
        imgcreate.fs.LoopbackMount.__init__(self, lofile, mountdir, fstype)
        self.type = type
        self.size = int(size)
        self.swap_size = 256
        self.fslabel = fslabel
        self.lofile = lofile
        self.mountdir = mountdir
        self.fstype = fstype
        self.cfg = cfg
        self.bindmounts = []

    def createSparseDrive(self, file, size):
        """ Create a sparse virtual drive. Feed me bytes. """
        dir = os.path.dirname(file)
        if not os.path.isdir(dir):
            os.makedirs(dir)

        self.cylinders = size / 516096
        fd = os.open(file, os.O_WRONLY | os.O_CREAT)
        os.lseek(fd, size, 0)
        os.write(fd, '\x00')
        os.close(fd)

    def createDrive(self, file, size):
        """ Create a virtual drive with a zero fill. Feed me bytes. """
        dir = os.path.dirname(file)
        if not os.path.isdir(dir):
            os.makedirs(dir)

        fd = os.open(file, os.O_WRONLY | os.O_CREAT)
        self.cylinders = size / 516096
        buf = '\x00' * 516096
        for i in range(0, self.cylinders):
            os.write(fd, buf)
        os.close(fd)

    def formatExt3Filesystem(self, drive):
        """ Format our new drive as ext3. """

        rc = subprocess.call(["/sbin/mkfs.ext3", "-F", "-L", self.fslabel,
                              "-m", "1", drive])
        if rc != 0:
            raise MountError(_("Error creating ext3 filesystem"))

        # FIXME: Figure out if we need to do tuning. The following is suitable for live media.
        #rc = subprocess.call(["/sbin/tune2fs", "-c0", "-i0", "-Odir_index",
        #                      "-ouser_xattr,acl", self.lofile])

    def simple_partition(self, device, drive_size_sectors, swap_size_mb, cylinders):
        """ Setup a simple partition layout for use with our virtual drive. """
        # This requires we know how large the drive is (drive_size_sectors) in sectors and how much of that drive
        # we want to use as swap space (swap_size_mb) in MB

        drive_size_sectors = drive_size_sectors - 63 * 16 # Account for a needed cylinder buffer
        swap_sectors = long(swap_size_mb) * 1024 * 2 # How many sectors we want for swap
        partition_sectors = drive_size_sectors - swap_sectors
        partdatawithswap = """unit: sectors

%(device)sp1 : start= 63, size= %(main_size)s, Id=83, bootable
%(device)sp2 : start=  %(swap_start)s, size= %(swap_size)s, Id=82
%(device)sp3 : start=  0, size= 0, Id= 0
%(device)sp4 : start=  0, size= 0, Id= 0
"""

        partdata = """unit: sectors

%(device)sp1 : start= 63, size= %(main_size)s, Id=83, bootable
%(device)sp2 : start=  0, size= 0, Id= 0
%(device)sp3 : start=  0, size= 0, Id= 0
%(device)sp4 : start=  0, size= 0, Id= 0
"""
        # Compile our part data with the needed sector information
        partdatawithswap = partdatawithswap % {"device" : device, "main_size" : partition_sectors, "swap_start" : partition_sectors + 63, "swap_size" : swap_sectors}
        partdata = partdata % {"device" : device, "main_size" : drive_size_sectors}

        # FIXME: It seems a little safer to write this out to a file, but we should do something better.
        sfdiskdatalocation = "/tmp/revisor-sfdisk-data.cfg"
        if self.cfg.virt_xen:
            sfdiskdatalocation = "/tmp/%s-sfdisk-data.cfg" % self.cfg.virt_xen
        elif self.cfg.virt_kvm:
            sfdiskdatalocation = "/tmp/%s-sfdisk-data.cfg" % self.cfg.virt_kvm

        sfdiskdata = open(sfdiskdatalocation, "w")
        sfdiskdata.write(partdata)
        sfdiskdata.close()
        # FIXME: subprocess doesn't like < ... maybe need inshell=True?
        command = "/sbin/sfdisk --force -H16 -S63 -C%s %s < %s" % (cylinders, device, sfdiskdatalocation)
        os.system(command)

    def prime_drive(self):
        """ Prime a virtual drive with some base file system structure and bind mount needed file systems. """
        if not self.mounted:
            #FIXME: Do something better.
            print "Oh noes!"
            sys.exit(1)

        # Create a basic directory structure
        if not os.access("%s/etc" % self.mountdir, os.R_OK): os.makedirs(self.mountdir + "/etc")
        if not os.access("%s/boot/grub" % self.mountdir, os.R_OK): os.makedirs(self.mountdir + "/boot/grub")
        if not os.access("%s/var/log" % self.mountdir, os.R_OK): os.makedirs(self.mountdir + "/var/log")
        if not os.access("%s/var/cache/yum" % self.mountdir, os.R_OK): os.makedirs(self.mountdir + "/var/cache/yum")

        # Bind mount useful special filesystems
        for (f, dest) in [("/sys", None), ("/proc", None), ("/dev", None), ("/dev/pts", None), ("/selinux", None)]:
            self.bindmounts.append(pilgrim.BindChrootMount(f, self.mountdir, dest))

        for b in self.bindmounts:
            b.mount()

        # Write our fstab
        # FIXME: This will need to be fancier for a custom partition layout
        self.write_fstab(self.mountdir)
        self.setup_grub()

    def setup_grub(self, dev=None):
        """ Setup grub on given device, including a fake entry so we can use grubby. """
        # FIXME: Do more then just call grub-install. We might even want to actually use the grub shell.

        # Build a device map that grub is willing to eat
        devicemap = open(self.mountdir + "/boot/grub/device.map", "w")
        devicemap.write("(hd0)     %s" % self.loopdev)
        devicemap.close()

        # Install grub
        rc = subprocess.call(["grub-install", "--root-directory=%s" % self.mountdir, self.loopdev])

        # Give us a fake config
        grubconf = open(self.mountdir + "/boot/grub/grub.conf", "w")
        grubconf.write("default=0\n")
        grubconf.write("timeout=5\n")
        grubconf.write("splashimage=(hd0)/grub/splash.xpm.gz\n")
        grubconf.write("hiddenmenu\n")
        grubconf.write("title Revisor\n")
        grubconf.write("\troot (hd0)\n")
        if dev:
            grubconf.write("\tkernel /vmlinuz ro root=%s rhgb quiet\n" % dev)
        else:
            grubconf.write("\tkernel /vmlinuz ro root=/dev/sda rhgb quiet\n")
        grubconf.write("\tinitrd /initrd\n")
        grubconf.close()

        # Build a device map that works to boot the guest
        devicemap = open(self.mountdir + "/boot/grub/device.map", "w")
        if dev:
            devicemap.write("(hd0)     %s" % self.loopdev)
        else:
            devicemap.write("(hd0)     /dev/sda")
        devicemap.close()


    def write_fstab(self, root, dev=None):
        """ Write out a basic fstab assuming / is sda, for now. """
        #FIXME: For user specified entries, we need to be able to take a list and for: fstab.write() the items
        fstab = open(root + "/etc/fstab", "w")

        if dev:
            fstab.write("%s               /                       ext3    defaults        0 0\n" % dev)
        else:
            fstab.write("/dev/sda               /                       ext3    defaults        0 0\n")

        fstab.write("devpts                  /dev/pts                devpts  gid=5,mode=620  0 0\n")
        fstab.write("tmpfs                   /dev/shm                tmpfs   defaults        0 0\n")
        fstab.write("proc                    /proc                   proc    defaults        0 0\n")
        fstab.write("sysfs                   /sys                    sysfs   defaults        0 0\n")
        fstab.close()

    def setup(self):
        """ Get everything setup for use. """

        # With VirtualDisk we can do aio, qcow and vmdk images
        size = self.size / float(1024) # Need to pass GB
        size_bytes = long(size * 1024 * 1024 * 1024)
        size_sectors = size_bytes / 512
        virt_drive = virtinst.VirtualDisk(self.lofile, size, type='file', sparse=self.cfg.virt_sparse)
        virt_drive.bindmounts = []

        if virt_drive._type == virtinst.VirtualDisk.TYPE_FILE:
            if virt_drive.sparse:
                self.createSparseDrive(virt_drive.path, size_bytes)
            else:
                self.createDrive(virt_drive.path, size_bytes)

        # FIXME: Setting up grub on a partitioned virtual disk has some challenges.

        # Partition drive
        self.loopsetup()
        if not self.partlayout:
            self.simple_partition(self.loopdev, size_sectors, self.swap_size, self.cylinders)
        else:
            print "Oh noes!"
            sys.exit(1)
        self.lounsetup()

        # FIXME: for item in self.partlayout: format as needed

        # Mount, preserving the first 63 sectors, and format our new drive
        self.loopsetup(offset=32256)

        if self.cfg.virt_fstype == "ext3":
            self.formatExt3Filesystem(self.loopdev)
        else:
            #FIXME: Add gears for other FS types
            print "Oh Noes!"
            sys.exit(1)

    def get_disk(self):
        """ Get a VirtualDisk with all our object's settings. """

        # FIXME: Add some magic to know what type of drive we want.
        size = self.size / float(1024) # Need to pass GB
        size_bytes = long(size * 1024 * 1024 * 1024)
        virt_disk = virtinst.VirtualDisk(self.lofile, size, type='file', sparse=self.cfg.virt_sparse)

        if virt_disk._type == virtinst.VirtualDisk.TYPE_FILE:
            if virt_disk.sparse:
                self.createSparseDrive(virt_disk.path, size_bytes)
            else:
                self.createDrive(virt_disk.path, size_bytes)

        return virt_disk

    def mount_drive(self, offset=0):
        """ Mount our drive for use. """

        if offset:
            if self.mounted:
                return

            if not os.path.isdir(self.mountdir):
                os.makedirs(self.mountdir)
                self.rmdir = True

            args = [ "/bin/mount", self.loopdev, self.mountdir ]
            if self.fstype:
                args.extend(["-t", self.fstype])

            rc = subprocess.call(args)
            if rc != 0:
                raise MountError(_("Failed to mount '%s' to '%s'") % (self.loopdev, self.mountdir))

            self.mounted = True

        else:
            self.mount()

class RevisorParaVirtual(virtinst.ParaVirtGuest):
    """ Our interface with virtinstaller to build para virt guests. """

    def set_log(self, log):
        """ Let us use our logging functions. """
        self.log = log

    def start_virtual_machine_installer(self):
        """ Start a target virtual machine with the fresh ISO image booting to run the install. """

        if os.access(self.iso, os.R_OK):
           self.log.info(_("Starting the virtual guest provision..."))
           self.set_install_location(self.iso)
           #self.validate_parms()
           self.start_install()
           sys.exit(1)
        else:
           print "Could not find ISO image..."
           sys.exit(1)

class RevisorFullVirtual(virtinst.FullVirtGuest):
    """ Our interface with virtinstaller to build full virt guests. """

    def set_log(self, log):
        """ Let us use our logging functions. """
        self.log = log

    # FIXME: Need to test with virtinst.util.is_hvm_capable()

    def start_virtual_machine_installer(self):
        """ Start a target virtual machine with the fresh ISO image booting to run the install. """

        if os.access(self.iso, os.R_OK):
           self.log.info(_("Starting the virtual guest provision..."))
           self.set_install_location(self.iso)
           #self.validate_parms()
           self.start_install()
           sys.exit(1)
        else:
           print "Could not find ISO image..."
           sys.exit(1)


