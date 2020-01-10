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

import logging
import os
import revisor
import sys
import pdb

# Translation
from revisor.translate import _, N_

class RevisorPlugins:
    """Detects, loads and interfaces with plugins for Revisor"""
    def __init__(self, init=False):
        """Specifies a list of plugins to test for, and triggers running those tests"""
        self.plugins =  {
                            'modcobbler': False,
                            'modcomposer': False,
                            'moddelta': False,
                            'modgui': False,
                            'modhub': False,
                            'modisolinux': False,
                            'modjigdo': False,
                            'modmock': False,
                            'modrebrand': False,
                            'modreuseinstaller': False,
                            'modvirt': False,
                            'modserver': False
                        }

        self.check_plugins(init=init)

    def load_plugins(self, plugins=[], init=False):
        """Loads plugins specified by a list of plugins or loads them all"""
        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if self.plugins[plugin]:
                try:
                    exec("self.%s = revisor.%s.Revisor%s()" % (plugin,plugin,plugin.replace("mod","").capitalize()))
                except Exception, e:
                    if not init: print >> sys.stderr, _("Plugin %s failed to load (%s: %s)") % (plugin, e.__class__, e)

    def check_plugins(self, init=False):
        """Checks all plugins in self.plugins and sets the values to
        True (loadable) or False (not enabled, not installed or not loadable)"""
        for plugin in self.plugins:
            try:
                exec("import revisor.%s" % plugin)
                self.plugins[plugin] = True
                self.load_plugins(plugins=[plugin], init=init)
            except ImportError, e:
                if not init: print >> sys.stderr, _("ImportError for plugin %s: %s") % (plugin,e)
                self.plugins[plugin] = False
            except RuntimeError, e:
                if not init: print >> sys.stderr, _("RuntimeError for plugin %s: %s") % (plugin,e)
                self.plugins[plugin] = False
            except Exception, e:
                if not init: print >> sys.stderr, _("Plugin %s failed to load (%s: %s)") % (plugin, e.__class__, e)

    def set_defaults(self, defaults, plugins=[]):
        """Test for a function set_defaults() in all available and loaded plugins and execute plugin.set_defaults()"""
        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),"set_defaults"):
                try:
                    getattr(self,plugin).set_defaults(defaults)
                except TypeError, e:
                    print >> sys.stderr, _("Cannot set defaults for plugin %s: %s") % (plugin,e)
                except RuntimeError, e:
                    print >> sys.stderr, _("Cannot set defaults for plugin %s: %s") % (plugin,e)
                except:
                    print >> sys.stderr, _("Cannot set defaults for plugin %s: Unknown Error") % (plugin)

            else:
                print >> sys.stderr, _("Not setting defaults for plugin %s: No function 'set_defaults()'") % plugin

    def set_runtime(self, runtime, plugins=[]):
        """Set runtime variables from plugins, like 'i_did_all_this'"""
        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),"set_runtime"):
                try:
                    getattr(self,plugin).set_runtime(runtime)
                except RuntimeError, e:
                    print >> sys.stderr, _("Cannot set runtime for plugin %s: %s") % (plugin,e)
            else:
                print >> sys.stderr, _("Not setting runtime for plugin %s: No function 'set_runtime()'") % plugin

    def add_options(self, parser, plugins=[]):
        """Add options specified in a plugin to parser. Takes a list of plugin names or does them all"""
        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),"add_options"):
                try:
                    exec("self.%s.add_options(parser)" % plugin)
                except RuntimeError, e:
                    print >> sys.stderr, _("Cannot add options for plugin %s: %s") % (plugin,e)
            else:
                print >> sys.stderr, _("Not adding options for plugin %s: No function 'add_options()'") % plugin

    def check_options(self, cfg, plugins=[]):
        """Executes plugin.check_plugins() for all enabled plugins or the list of plugin names specified."""

        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),"check_options"):
                try:
                    exec("self.%s.check_options(cfg, cfg.cli_options)" % plugin)
                except AttributeError, e:
                    print >> sys.stderr, _("Cannot check options for plugin %s: %s") % (plugin,e)
            else:
                print >> sys.stderr, _("Not checking options for plugin %s: No function 'check_options()'") % plugin

    def plugin_check_setting(self, func, option, val, plugins=[]):
        """Checks one setting specified by 'option' against the 'val' it is passed by all plugins or by the list of plugins specified"""

        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),"%s_%s" % (func,option)):
                exec("retval = getattr(self,plugin).%s_%s(val)" % (func,option))
                return retval

        return False

    def exec_hook(self, hook, plugins=[]):
        """Execute a hook"""

        if len(plugins) < 1:
            plugins = self.plugins.keys()

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),hook):
                try:
                    exec("self.%s.%s()" % (plugin,hook))
                except AttributeError, e:
                    print >> sys.stderr, _("Cannot execute hook %s for plugin %s: %s") % (hook,plugin,e)

    def return_true_boolean_from_plugins(self, bool, plugins=[]):
        """Given the name of a boolean, walks all specified plugins, or all available plugins, and returns True if a plugin has it set to true"""
        if len(plugins) < 1:
            plugins = self.plugins.keys()

        retval = False

        for plugin in plugins:
            if not self.plugins[plugin]:
                continue
            if not hasattr(self,plugin):
                continue

            if hasattr(getattr(self,plugin),bool):
                try:
                    exec("boolval = self.%s.%s" % (plugin,bool))
                except AttributeError, e:
                    pass
            else:
                boolval = None

            if boolval: retval = True

        return retval
