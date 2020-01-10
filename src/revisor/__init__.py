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
"""
Revisor init file
"""
__license__ = "GPLv2+"
__author__ = 'Fedora Unity'
__status__ = 'beta'
__version__ = '2.2-1'

from optparse import OptionParser
from ConfigParser import SafeConfigParser

import revisor
import revisor.base
import revisor.cfg
import revisor.plugins
import revisor.misc as misc
from revisor.constants import *

import traceback
import shutil

from revisor.translate import _, N_

class Revisor:
    """Whatever gets you going"""
    def __init__(self, initbase=True):
        """
            self.args == Arguments passed on the CLI
            self.cli_options == Parser results (again, CLI)
            self.parser == The actual Parser (from OptionParser)
            self.plugins == Our Plugins from Revisor
        """
        self.args = None
        self.cli_options = None
        self.parser = None
        self.plugins = None

        # Create and parse the options
        self.parse_options()

        # Check if this is being run as root
        if initbase:
            misc.check_uid()

        # See if we're being told to not do anything but like
        # to list something and then exit
        self.answer_questions()

        # Create me a RevisorBase instance
        if initbase:
            self.base = revisor.base.RevisorBase(self)

    def parse_options(self, load_plugins=True):
        """
            Create the OptionParser for the options passed to us from runtime
            Command Line Interface.
        """

        epilog = "Revisor is a Fedora Unity product. For more information" + \
                 "about Revisor, visit http://fedorahosted.org/revisor"

        # Enterprise Linux 5 does not have an "epilog" parameter to OptionParser
        try:
            self.parser = OptionParser(epilog=epilog)
        except:
            self.parser = OptionParser()

        ##
        ## Runtime Options
        ##
        runtime_group = self.parser.add_option_group(_("Runtime Options"))
        runtime_group.add_option(   "--cli",
                                    dest    = "cli_mode",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Use the CLI rather then GUI"))

        runtime_group.add_option(   "--gui",
                                    dest    = "gui_mode",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Force Revisor to use the " + \
                                                "GUI. Does not fallback to " + \
                                                "CLI and thus shows GUI " + \
                                                "related errors"))

        runtime_group.add_option(   "--list-models",
                                    dest    = "list_models",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("List available models"))

        runtime_group.add_option(   "--devel",
                                    dest    = "mode_devel",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Development mode. Skips some tasks that take time."))

        runtime_group.add_option(   "--report-sizes",
                                    dest    = "report_sizes",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Report the sizes of all RPMs selected in a list"))

        runtime_group.add_option(   "--kickstart-exact-nevra",
                                    dest    = "kickstart_exact_nevra",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Force Revisor to interpret the package manifest as complete package nevra (name, epoch, version, release and architecture). Implies --kickstart-exact"))

        runtime_group.add_option(   "--kickstart-exact",
                                    dest    = "kickstart_exact",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Tells Revisor to ignore @core and @base (or %packages --nobase) and only add what is in the package manifest"))

        runtime_group.add_option(   "--clean-up", "--cleanup",
                                    dest    = "clean_up",
                                    action  = "store",
                                    type    = 'int',
                                    default = 1,
                                    help    = _("Should Revisor not clean up at all (0), clean up it's temporary build data (1), or everything -this includes the yum cache (2)"))

        runtime_group.add_option(   "--usb-size",
                                    dest    = "usb_size",
                                    action  = "store",
                                    type    = 'string',
                                    default = "4G",
                                    help    = _("Size of the USB Thumb Drive. Default to 4G."))

        ##
        ## Logging Options
        ##
        runtime_group.add_option(   "-d", "--debug",
                                    dest    = "debuglevel",
                                    default = 0,
                                    type    = 'int',
                                    help    = _("Set debugging level (0 by default)"))

        runtime_group.add_option(   "--logfile",
                                    dest    = "logfile",
                                    default = "/var/log/revisor.log",
                                    help    = _("Use a different logfile"))

        ##
        ## Redundant Options
        ##
        runtime_group.add_option(   "-y", "--yes",
                                    dest    = "answer_yes",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Answer all questions as 'yes'"))

        ##
        ## Configuration Options
        ##
        config_group = self.parser.add_option_group(_("Configuration Options"))
        config_group.add_option(    "--kickstart",
                                    dest    = "kickstart_file",
                                    action  = "store",
                                    default = "",
# Might be disabled for testing purposes
#                                    default = os.path.join(BASE_CONFD_DIR,"fedora-7-gold.cfg"),
                                    help    = _("Use kickstart file"),
                                    metavar = "[kickstart file]")

        config_group.add_option(    "--kickstart-save",
                                    dest    = "kickstart_save",
                                    action  ="store",
                                    default = "",
                                    help    = _("Save options to given file (as a kickstart)"),
                                    metavar = "[file name]")

        config_group.add_option(    "-c", "--config",
                                    dest    = "config",
                                    action  = "store",
                                    default = os.path.join(BASE_CONF_DIR,"revisor.conf"),
                                    help    = _("Revisor configuration file to use"),
                                    metavar = "[config file]")

        config_group.add_option(    "--source",
                                    dest    = "getsource",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Get the sources to go with the binaries"))

        config_group.add_option(    "--destination-directory",
                                    dest    = "destination_directory",
                                    action  = "store",
                                    default = "/srv/revisor/",
                                    help    = _("Destination directory for products"),
                                    metavar = "[directory]")

        config_group.add_option(    "--working-directory",
                                    dest    = "working_directory",
                                    action  = "store",
                                    default = "/var/tmp/",
                                    help    = _("Working directory"),
                                    metavar = "[directory]")

        config_group.add_option(    "--model",
                                    dest    = "model",
                                    action  = "store",
                                    default = "",
                                    help    = _("Model to use for composing"),
                                    metavar = "[model]")

        config_group.add_option(    "--respin",
                                    dest    = "mode_respin",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Mode to use for composing updated spins"))

        config_group.add_option(    "--copy-local",
                                    dest    = "copy_local",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Sometimes, it's better to copy local data rather then (sym)linking it. If you have enough space..."))

        config_group.add_option(    "--copy-dir",
                                    dest    = "copy_dir",
                                    action  = "store",
                                    default = "",
                                    help    = _("Directory to copy onto the media"))

        ##
        ## Installation Media Options
        ##
        install_group = self.parser.add_option_group(_("Installation Media Options"))
        install_group.add_option(   "--install-cd",
                                    dest    = "media_installation_cd",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media CDs (Capacity per disc: 685MB)"))

        install_group.add_option(   "--install-dvd",
                                    dest    = "media_installation_dvd",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media DVDs (Capacity per disc: 4.3GB)"))

        install_group.add_option(   "--install-dvd-dl",
                                    dest    = "media_installation_dvd_duallayer",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media Dual-Layered DVDs (Capacity per disc: 8.5GB)"))

        install_group.add_option(   "--install-bluray",
                                    dest    = "media_installation_bluray",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media Blu-Ray Discs (Capacity per disc: 25GB)"))

        install_group.add_option(   "--install-bluray-dl",
                                    dest    = "media_installation_bluray_duallayer",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media Duallayer Blu-Ray Discs (Capacity per disc: 50GB)"))

        install_group.add_option(   "--install-usb",
                                    dest    = "media_installation_usb",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Installation Media that goes onto a USB thumbdrive"))

        install_group.add_option(   "--install-unified",
                                    dest    = "media_installation_unified",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Unified ISO from install tree"))

        # This doesn't work because anaconda doesn't allow expanded tree installations from hard drive
        #install_group.add_option(   "--install-usb",
                                    #dest    = "media_installation_usb",
                                    #action  = "store_true",
                                    #default = False,
                                    #help    = _("Build install image for use on USB thumb drives (Remember to specify the size of the USB Thumb Drive with --usb-size)"))

        install_group.add_option(   "--install-tree",
                                    dest    = "media_installation_tree",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create the Installation Tree."))

        install_group.add_option(   "--install-mode-full",
                                    dest    = "installation_mode_full",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create a Full Installation Tree. Includes all binary (sub-)packages created from source packages."))

        install_group.add_option(   "--install-mode-ss",
                                    dest    = "installation_mode_ss",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create a Self-Sustaining Installation Tree. Includes all build requirements for included source packages."))

        install_group.add_option(   "--install-nogr",
                                    dest    = "install_nogr",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Media without graphical installer."))

        install_group.add_option(   "--kickstart-include",
                                    dest    = "kickstart_include",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Include kickstart file on media or in the tree"))

        install_group.add_option(   "--kickstart-default",
                                    dest    = "kickstart_default",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("In the bootloader menu (isolinux.cfg), set kickstart to boot by default (works with --kickstart-include)"))

        install_group.add_option(   "--filter-comps",
                                    dest    = "comps_filter",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Filter anything from comps that is not in the package set"))

        install_group.add_option(   "--revisor-comps",
                                    dest    = "revisor_comps",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Use Revisor's comps file instead of those from the repositories"))

        install_group.add_option(   "--comps",
                                    dest    = "comps",
                                    action  = "store",
                                    default = "/usr/share/revisor/comps-f7.xml",
                                    help    = _("Comps file to include on the installation media"))

        install_group.add_option(   "--updates-img",
                                    dest    = "updates_img",
                                    action  = "store",
                                    default = "",
                                    help    = _("Include specified updates.img on installation media."),
                                    metavar = "[updates image]")

        install_group.add_option(   "--product-name",
                                    dest    = "product_name",
                                    action  = "store",
                                    default = "Fedora",
                                    help    = _("Product Name"))

        install_group.add_option(   "--product-path",
                                    dest    = "product_path",
                                    action  = "store",
                                    default = "Fedora",
                                    help    = _("Product Path (e.g. Fedora/ or Packages/ -but without the appending slash)"))

        install_group.add_option(   "--iso-label",
                                    dest    = "iso_label",
                                    action  = "store",
                                    default = "Fedora",
                                    help    = _("ISO Label Base. Note that other things are appended but that the length can be 32 chars maximum."))

        install_group.add_option(   "--iso-basename",
                                    dest    = "iso_basename",
                                    action  = "store",
                                    default = "Fedora",
                                    help    = _("The base name for the ISOs"))

        install_group.add_option(   "--product-version",
                                    dest    = "version",
                                    action  = "store",
                                    default = "8",
                                    help    = _("Product Version"))

        install_group.add_option(   "--product-version-from",
                                    dest    = "version_from",
                                    action  = "store",
                                    default = "F8",
                                    help    = _("Base Product Version - relevant to required packages and pykickstart compatibility"))

        ##
        ## Utility Media Options
        ##
        utility_group = self.parser.add_option_group(_("Utility Media Options"))
        utility_group.add_option(   "--utility-rescue",
                                    dest    = "media_utility_rescue",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Rescue Media"))

        ##
        ## Live Media Options
        ##
        live_group = self.parser.add_option_group(_("Live Media Options"))
        live_group.add_option(      "--live-optical",
                                    dest    = "media_live_optical",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Live Media CD/DVD"))

        live_group.add_option(      "--live-usb-thumb",
                                    dest    = "media_live_thumb",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Live Media Thumb Drive Image (will be depreciated)"))

        live_group.add_option(      "--live-usb-hd",
                                    dest    = "media_live_hd",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Live Media Hard Disk Image (will be depreciated)"))

        live_group.add_option(      "--live-raw",
                                    dest    = "media_live_raw",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Create Live Media Raw Hard Disk Image"))

        live_group.add_option(      "--live-shell",
                                    dest    = "lm_chroot_shell",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Interactively work in the live image before building the ISO image."))

        live_group.add_option(      "--skip-compression",
                                    dest    = "lm_skip_fs_compression",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Skip file system compression."))

        live_group.add_option(      "--skip-prelink",
                                    dest    = "lm_skip_prelink",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Skip prelinking the contents of the filesystem."))

        live_group.add_option(      "--ignore-deleted",
                                    dest    = "lm_ignore_deleted",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Ignore filesystem overhead. Useless blocks will not be removed from the filesystem."))

        live_group.add_option(      "--preferred-kernel",
                                    dest    = "lm_preferred_kernel",
                                    action  = "store",
                                    default = "normal",
                                    help    = _("Set the preferred kernel. One of normal, PAE, xen or debug."))

        ##
        ## Get options from plugins
        ##
        if load_plugins:
            self.plugins = revisor.plugins.RevisorPlugins(init=True)
            self.plugins.add_options(self.parser)

        # Parse Options
        (self.cli_options, self.args) = self.parser.parse_args()

    def answer_questions(self):
        """A function that is executed prematurely (nothing has initialized yet) and
        should only be used for quick actions, such as listing the models configured
        in the configuration file."""

        if self.cli_options.list_models:
            config = SafeConfigParser()
            if self.cli_options.config:
                config_file = self.cli_options.config
            else:
                config_file = os.path.join(BASE_CONF_DIR, "revisor.conf")

            if not os.access(config_file, os.R_OK):
                print >> sys.stderr, "No such configuration file %s" % config_file

            try:
                config.read(config_file)
            except:
                print >> sys.stderr, "Could not parse configuration file %s" % config_file

            models = config.sections()
            models.sort()
            print "Models:"
            for model in models:
                if not model == "revisor":
                    if config.has_section(model):
                        if config.has_option(model,"main"):
                            if os.path.isfile(config.get(model,"main")):
                                if config.has_option(model,"description"):
                                    print " %s - %s" % (model, config.get(model,"description"))
                                else:
                                    print _(" %s - No Description") % model
                            else:
                                print >> sys.stderr, _("The configured model %s does not have a valid file as 'main' configuration option.") % model
                        else:
                            print >> sys.stderr, _("The configured model %s does not have the mandatory 'main' configuration directive.") % model
            sys.exit(0)

        if hasattr(self.cli_options, "cobbler_list"):
            if self.cli_options.cobbler_list:
                if self.cli_options.cobbler_server != "127.0.0.1":
                    self.plugins.modcobbler.listOptions(server=self.cli_options.cobbler_server, display=True)
                elif (self.cli_options.cobbler_server != "127.0.0.1") and self.cli_options.cobbler_port:
                    self.plugins.modcobbler.listOptions(server=self.cli_options.cobbler_server, port=cli_options.cobbler_port, display=True)
                else:
                    self.plugins.modcobbler.listOptions(display=True)
                sys.exit(0)

        # FIXME: Please check if there's any questions from modules to answer

    def run(self):
        """Run Forest, RUN!"""

        exitcode = 0

        try:
            self.base.run()
        except SystemExit, e:
            exitcode = e
        except KeyboardInterrupt:
            exitcode = 1
            self.base.log.info(_("Interrupted by user"))
        except AttributeError, e:
            exitcode = 1
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://fedorahosted.org/revisor")
#        except TypeError, e:
#            self.log.error(_("Type Error: %s") % e)
        except:
            exitcode = 2
            traceback.print_exc()
            print >> sys.stderr, _("Traceback occurred, please report a bug at http://fedorahosted.org/revisor")
        finally:
            if self.base.cfg.clean_up == 0:
                # Leave everything as it is
                pass
            if self.base.cfg.clean_up > 0:
                # Remove our directories in the working directory
                for dir in [ "revisor-pungi", "revisor", "revisor-rundir" ]:
                    if os.access(os.path.join(self.base.cfg.working_directory, dir), os.R_OK):
                        shutil.rmtree(os.path.join(self.base.cfg.working_directory, dir), ignore_errors=True)

            if self.base.cfg.clean_up > 1:
                # Remove everything
                for dir in ["revisor-yumcache"]:
                    if os.access(os.path.join(self.base.cfg.working_directory, dir), os.R_OK):
                        shutil.rmtree(os.path.join(self.base.cfg.working_directory, dir), ignore_errors=True)

        sys.exit(exitcode)
