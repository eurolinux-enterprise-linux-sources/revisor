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

import shutil

from copy import copy
from optparse import OptionParser
from ConfigParser import SafeConfigParser

from traceback import print_exc

import revisor
import revisor.base
import revisor.cfg
import revisor.plugins
import revisor.misc as misc
from revisor.constants import *

# Translation
from revisor.translate import _, N_

import SimpleXMLRPCServer
import xmlrpclib
import os

# Extend revisor.base.RevisorBase and __init__() it?
# Or, consider doing that for RevisorServerSession
class RevisorServer(object):
    """ Revisor module for Server/Client communications. This is the Server side."""

    def __init__(self):
        # FIXME: Initialize logging
        pass

    def do_xmlrpc(self, cfg):
        """ Get our xmlrpc server running. """
        xinterface = RevisorXMLRPCInterface(cfg)
        server = RevisorXMLRPCServer(('', int(cfg.server_port)))
        server.register_introspection_functions()
        cfg.log.info("XMLRPC Server running on port %s" % cfg.server_port)
        server.register_instance(xinterface)
        while True:
            try:
                server.serve_forever()
            except IOError:
                # interrupted? try to serve again
                time.sleep(0.5)

    def run(self, base):
        """ Start the server."""
        # FIXME: Find a better way to leave foreground
        if base.cfg.fork_mode:
            pid = os.fork()
            self.do_xmlrpc(base.cfg)
        else:
            try:
                self.do_xmlrpc(base.cfg)
            except KeyboardInterrupt:
                base.log.info("Shutting down...")

    def add_options(self, parser):
        """Adds a Server Options group to the OptionParser instance you give it (parser),
        and adds the options for this module to that group"""

        modserver_group = parser.add_option_group("Server Options")
        modserver_group.add_option( "--server",
                                    dest    = "server_mode",
                                    action  = "store_true",
                                    default = False,
                                    help    = _("Use the server mode for XML-RPC"))
        modserver_group.add_option( "--server-port",
                                    dest = "server_port",
                                    action = "store",
                                    default = "9321",
                                    help = _("Port to start Server on."),
                                    metavar = "[server-port]")
        modserver_group.add_option( "--fork",
                                    dest = "fork_mode",
                                    action = "store",
                                    default = False,
                                    help = _("Start the XML-RPC server and fork."),
                                    metavar = "[boolean]")

    def set_defaults(self, defaults):
        # These defaults come from CLI Options already
        #defaults.server_port = "9321"
        #defaults.fork_mode = False
        pass

    def check_options(self, cfg, cli_options):
        # Cheater! Found a cheater!
        if cli_options.server_mode:
            cfg.server_mode = True
            cfg.gui_mode = False
            cfg.cli_mode = False
        pass

def default_error_handler(e):
    print_exc()

#ah the joys of writing your own decorators
def error_handler(handler=default_error_handler):
    def handle(f):
        def fun(*args, **keys):
            try:
                return f(*args, **keys)
            except Exception, e:
                handler(e)
                raise e
        return fun
    return handle


class RevisorXMLRPCInterface(object):
    """ Functionality to expose to the XML-RPC interface. """

    def __init__(self, cfg=None):
        if cfg == None:
            # FIXME: Initialize ConfigStore or return Error
            pass
        else:
            self.cfg = cfg

        self.sessions = dict()
        self.next_session = 0

    @error_handler()
    def server_start(self):
        new_session = Session(self.next_session)
        self.sessions[self.next_session] = new_session
        self.next_session += 1
        return new_session.id

    @error_handler()
    def server_clear_sessions(self):
        self.sessions = dict()
        return 1

    @error_handler()
    def session_list_sessions(self, sid):
        return self.sessions.keys()

    @error_handler()
    def session_delete_session(self, sid):
        del self.sessions[sid]
        return 1

    @error_handler()
    def session_set_model(self, sid, model):
        self.sessions[sid].revisor.model = model
        return 1

    @error_handler()
    def session_set_configuration(self, sid, config="/etc/revisor/revisor.conf"):
        self.sessions[sid].revisor.config = config
        return 1

    @error_handler()
    def session_set_kickstart(self, sid, fn):
        self.sessions[sid].revisor.kickstart_file = fn
        return 1

    @error_handler()
    def session_start_compose(self, sid):
        self.sessions[sid].start_compose(sid)
        return 1

class Session(object):
    def __init__(self, id):
        self.id = id
        print "Session initted"
        self.revisor = DuckRevisor()

    def start_compose(self, id):
        if id == self.id:
            self.revisor.start_compose()

class RevisorXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):
    """ The actual XML-RPC Server object"""
    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, args)

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
