# Translation
from revisor.translate import _, N_

import revisor
import revisor.base
import revisor.cfg
from revisor.client import *

import SimpleXMLRPCServer
import xmlrpclib
import os
import thread
import time

# Composing Module
class RevisorComposer():
    """ Composer Mode """

    def __init__(self):
        self.composer_occupied = 0
        self.composer_id = 0
        self.job_id = 0
        pass

    def run(self, base):
        self.base = base
        try:
            self.composer_id = self.composer_logon()
            print "Logged in. Composer id:", self.composer_id
        except Exception, e:
            base.log.info("Login failed. Shutting down...")
            raise e
        try:
            self.do_xmlrpc(base)
        except Exception, e:
            self.composer_logoff()
            base.log.info("Shutting down...")
            raise e
        self.composer_logoff()
            
    def do_job(self):
        self.get_kickstart_file()
        self.job_id += 1
        self.start_compose(self.job_id)        
        return 1
        
    def composer_logon(self):
        self.base.log.info("Logging on...")
        try:
            print "1"
            hub = Connection("http://localhost:9321")
            print "2"
            self.composer_id = hub.con.composer_logon("localhost", 9322)
            print "3"
        except Exception, e:
            raise e
        print "4"
        return self.composer_id
        
    def composer_logoff(self):
        print "Logging off..."
        try:
            hub = Connection("http://localhost:9321")
            hub.con.composer_logoff(self.composer_id)
            #hub.close()
        except Exception, e:
            raise e
        return self.composer_id
        
    def get_kickstart_file(self):
        print "Getting kickstart file."
        try:
            hub = Connection("http://localhost:9321")
            self.kickstart_file = hub.con.get_kickstart_file(self.composer_id)
            #hub.close()
        except Exception, e:
            raise e
        return self.kickstart_file
        
    def start_compose(self, job_id, kickstart_file):
        try:
            thread.start_new_thread(thread_start_compose,(self, job_id, kickstart_file))
        except KeyboardInterrupt:
            #base.log.info("Shutting Down...")
            pass
        return job_id

    def do_xmlrpc(self, base):
        print "Composer XML-RPC Server Started..."
        xinterface = RevisorXMLRPCInterface(self, base.cfg)
        server = RevisorXMLRPCServer(('', int(base.cfg.composer_port)))
        server.register_introspection_functions()
        base.cfg.log.info("Composer XMLRPC Server running on port %s..." % base.cfg.composer_port)
        server.register_instance(xinterface)
        while True:
            try:
                server.serve_forever()
            except IOError:
                # interrupted? try to serve again
                time.sleep(0.5)

    def add_options(self, parser):
        modcomposer_group = parser.add_option_group("Composer Options")
        modcomposer_group.add_option( "--composer",
                                dest    = "composer_mode",
                                action  = "store_true",
                                default = False,
                                help    = _("Use the Composer mode for distributed composing. Use as a client for modhub"))
        modcomposer_group.add_option( "--composer-port",
                                dest = "composer_port",
                                action = "store",
                                default = "9322",
                                help = _("Port to start Composer mode on."),
                                metavar = "[composer-port]")
        modcomposer_group.add_option( "--master-ip",
                                dest    = "master_ip",
                                action  = "store",
                                default = "localhost",
                                help    = _("IP Address of where the Revisor Hub is running."),
                                metavar = "[master-ip]")
        modcomposer_group.add_option( "--master-port",
                                dest = "master_port",
                                action = "store",
                                default = "9321",
                                help = _("Port of where the Revisor Hub is running."),
                                metavar = "[master-port]")

    def check_options(self, cfg, cli_options):
        # Cheater! Found a cheater!
        if cli_options.composer_mode:
            cfg.server_mode = False
            cfg.composer_mode = True
            cfg.hub_mode = False
            cfg.gui_mode = False
            cfg.cli_mode = False

    def set_defaults(self, defaults):
        #defaults.db_server = x.x.x.x
        #defaults.db_type = mysql #for later development
        #defaults.setport = "3306"
        #defaults.username = "blaat"
        #defaults.password = "pass"
        #defaults.dbname = "revisor-hubdb"
        #defaults.configfile = "blaat"
        pass
        
 #Threads
def thread_start_compose(composer, job_id, kickstart_file):
    try:
        revisor = DuckRevisor()
        revisor.kickstart_file = kickstart_file
        print "Starting Compose..."
        revisor.start_compose()
    except Exception, e:
        #base.log.info("Spin creation process interrupted...")
        raise e
    composer.composer_occupied = 0
    print "Composer", composer.composer_id, "sleeping..."
    return job_id
 

# The actual XMLRPC Object Server
class RevisorXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """ The actual XML-RPC Server object"""
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, args)


# XMLRPC Methods: Accessable by the Hub
class RevisorXMLRPCInterface(object):
    """ Functionality to expose to the XML-RPC interface. """

    def __init__(self, composer, cfg=None):
        try:
            if cfg:
                self.cfg = cfg
            else:
                # FIXME: Initialize ConfigStore or return Error
                pass
        except NameError:
            pass
        self.composer = composer
        
    def are_you_awake(self):
        return self.composer.composer_occupied
        
    def wake_composer(self, job_id, kickstart_file):
        print "Composer", self.composer.composer_id, "has awakened!"
        self.composer.composer_occupied = 1
        self.composer.start_compose(job_id, kickstart_file)
        return 1
        
    def progress_update(self):
        return "99.934%"
        

class DuckRevisor(revisor.Revisor):
    """This class can quack like a Revisor - it is really just a stripped down version"""

    def __init__(self):
        """
            self.args == Arguments passed on the CLI
            self.cli_options == Parser results (again, CLI)
            self.parser == The actual Parser (from OptionParser)
            self.plugins == Our Plugins from Revisor
        """

        revisor.Revisor.__init__(self)

        self.base = revisor.base.RevisorBase(self)

        # Cheater! We have a cheater!
        self.base.cfg.cli_mode = True
        self.base.cfg.gui_mode = False
        self.base.cfg.server_mode = False

    def start_compose(self):
        # Bwuhahaha
        self.base.cfg.load_model(config=self.base.cfg.check_config("/etc/revisor/revisor.conf"),model=self.model)

        self.base.cfg.media_installation_dvd = 1

        # Set answer_yes to 1
        self.base.cfg.answer_yes = 1

        self.base.cfg.load_kickstart(self.kickstart_file)

        self.base.cfg.check_options()

        # Let's check for the existance of the directories we are going to work with:
        # Since there may be mounts in there, if it fails we *need* to cancel
        self.base.cfg.check_working_directory()

        # Let's check for the existance of the directories in which our products go:
        self.base.cfg.check_destination_directory()

        self.base.setup_yum()

        # FIXME: The following needs to happen here;
        # 1) Check if the versions for related packages have been
        #    used before to compose the installer images.
        #    Since the compose of the installer images takes a
        #    relatively long time, and a lot of processing.
        #    If, somewhere in cache on the filesystem or something, the
        #    results of a previous compose are available, use
        #    cfg.reuse /path/to/installtree
        #

        self.base.lift_off()

        #self.cli_options = copy(host.cli_options)
        #self.cli_options.server_mode = False
        #self.cli_options.gui_mode = False
        #self.cli_options.cli_mode = False
        #self.cli_options.headless_mode = True

        #self.plugins = host.plugins

        # Create me a RevisorBase instance
#        self.base = revisor.base.RevisorBase(self)

        # Then run it.
        # Do so after base.__init__() has completed or it'll fail
        # Run from a function that lives here, because we can catch exceptions here,
        # throw error codes, sys.exit(1) or just start all over again (if only just to
        # unmount stuff).
#        self.run()
