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

#import logger.Logger

class RevisorHub():
    """ Hub Mode """

    def __init__(self):
        self.count_composers = 0
        self.thread_count = 0
        self.composers = 0
        pass

    def run(self, base):
        self.base = base
        self.thread_count += 2
        try:
            self.base.log.info("Starting Threads...")
            thread.start_new_thread(thread_do_polling,(base.cfg, self))
            thread.start_new_thread(thread_do_xmlrpc,(base.cfg, self))
            while self.thread_count > 1:
                pass
        except Exception, e:
            self.base.log.info("Shutting Down...")
            pass
		
    def db_get_ks(self): #Private function?
        self.base.log.info("* Getting test.ks from Database.")
        return open('revisor/modhub/anaconda-ks.cfg', 'rb')
		
    def db_check_jobs(self):
        # Wake the Composer, send Job_id and kickstart_file
        # check jobs in DB
        self.base.log.info("* Checking Database for Jobs")
        # get KS from DB if any found
        return self.db_get_ks()
		
    def db_add_composer(self, composer_host, composer_port):
        self.count_composers += 1
        self.base.log.info("New composer added.")
        print "* ComposerHost:", composer_host, "ComposerPort:", composer_port
        return self.count_composers
        
    def db_remove_composer(self, composer_id):
        self.count_composers -= 1
        self.base.log.info("Composer removed. ComposerID:")
        return self.count_composers
    
    def do_xmlrpc(self, cfg):
        xinterface = RevisorXMLRPCInterface(self, cfg)
        server = RevisorXMLRPCServer(('', int(cfg.hub_port)))
        server.register_introspection_functions()
        server.register_instance(xinterface)
        while True:
            try:
                server.serve_forever()
            except IOError:
                # interrupted? try to serve again
                time.sleep(0.5)
    
    def do_polling(self, cfg):
        job_id = 0
        while True:
            time.sleep(3)
            # Check DB for new KS file.
            if self.count_composers > 0:
                # Check if a Composer is present. Check if it's not busy
                try:
                    composer = Connection("http://localhost:9322") # Make connection with the chosen Composer
                except Exception, e:
                    raise e
                if not composer.con.are_you_awake():
                    job_id += 1
                    try:
                        self.base.log.info("* Ready Composer found! Getting kickstart file...")
                        binary_ks_file = xmlrpclib.Binary(self.db_check_jobs().read())
                        self.base.log.info("* Waking Composer. Sending File...")
                        composer.con.wake_composer(job_id, binary_ks_file)
                        self.base.log.info("* File sent.")
                    except Exception, e:
                        raise e
                else:
                    self.base.log.info("Can't start Job. No ready Composer found.")
                time.sleep(7)
            else:
                self.base.log.info("Can't start Job. No Composer logged in.")  

    def add_options(self, parser):
        modhub_group = parser.add_option_group("Hub Options")
        modhub_group.add_option( "--hub",
                                dest    = "hub_mode",
                                action  = "store_true",
                                default = False,
                                help    = _("Use the Hub mode for distributed composing."))
        modhub_group.add_option( "--hub-port",
                                dest = "hub_port",
                                action = "store",
                                default = "9321",
                                help = _("Port to start Hub mode on."),

                                metavar = "[hub-port]")

    def check_options(self, cfg, cli_options):
        # Cheater! Found a cheater!
        if cli_options.hub_mode:
            cfg.server_mode = False
            cfg.hub_mode = True
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


# Threads
def thread_do_xmlrpc(cfg, revisorHub):
    revisorHub.base.log.info( "* Hub XML-RPC Thread Started...")
    revisorHub.do_xmlrpc(cfg)

def thread_do_polling(cfg, revisorHub):
    revisorHub.base.log.info("* Hub Polling Thread Started...")
    revisorHub.do_polling(cfg)
    

# The actual XMLRPC Object Server
class RevisorXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """ The actual XML-RPC Server object"""
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, args)


# XMLRPC Methods: Accessable to the Composers
class RevisorXMLRPCInterface(object):
    """ Functionality to expose to the XML-RPC interface. """

    def __init__(self, hub, cfg=None):
        try:
            if cfg:
                self.cfg = cfg
            else:
                # FIXME: Initialize ConfigStore or return Error
                pass
        except NameError:
            pass
        self.hub = hub
        pass
        
    def get_kickstart_file(self, composer_id):
        print "Fetching kickstart file for Composer#", composer_id, "."
        #Test line!
        #ks_file = xmlrpclib.Binary(open('revisor/modhub/test.ks', 'rb').read())
        binary_ks_file = xmlrpclib.Binary(self.hub.db_check_jobs().read())
        return binary_ks_file

    def composer_logon(self, composer_host, composer_port):
        composer_id = self.hub.db_add_composer(composer_host, composer_port)
        print "Composer ID:", composer_id, "logging on..."
        return composer_id

    def composer_logoff(self, composer_id):
        print "Composer ID:", composer_id, "logging off..."
        self.hub.db_remove_composer(composer_id)
        return composer_id
        
    def process_update(self, composer_id, process):
        print "Composer ID", composer_id, "is at", process, "%."
        return 1


# Our Data Classes
class ComposerList:
    def __init__(self, composer_id=None, composer_host=None, composer_port=None):
        self.list = 0
        try:
            if composer_id:
                self.list.append([composer_id, composer_host, composer_port])
            else:
                pass
        except NameError:
            pass
        pass
    
    def __repr__(self):
        for i in self.list:
            print i[0], ",", i[1], ".", i[2], "."  
        
    def __add__(self, composer_id, composer_host, composer_port):
        try:
            if composer_id:
                self.list.append([composer_id, composer_host, composer_port])
            else:
                pass
        except NameError:
            pass
        pass
