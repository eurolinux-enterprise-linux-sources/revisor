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

import sys
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk

import revisor.progress

# Import constants
from revisor.constants import *

# Translation
from revisor.translate import _, N_

# Master GTK Interface update routine
def _runGtkMain(*args):
    while gtk.events_pending():
        gtk.main_iteration()

class BuildMedia:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        gui.add_buttons()

        gui.base_buttons_xml.get_widget("button_back").set_sensitive(False)
        gui.base_buttons_xml.get_widget("button_forward").set_sensitive(False)

        self.connect_button_signals()

        self.tasktable = self.frame_xml.get_widget("tasktable")
        self.part_progress = self.frame_xml.get_widget("part_progress")
        self.total_progress = self.frame_xml.get_widget("total_progress")
        self.set_task_list()
        self.show_task_list()

    def start(self):
        self.show_task_list()
        if not self.cfg.i_did_all_this:
            self.base.setup_yum()

        self.base.lift_off()

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_information_clicked": self.button_information_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

    def button_information_clicked(self, button):
        self.gui.button_information_clicked(button, "build-media")

    def button_back_clicked(self, button):
        pass

    def button_forward_clicked(self, button):
        pass

    def set_task_list(self):
        """Build a list/dict of tasks to complete."""
        self.tasks = []

        if not self.cfg.i_did_all_this:
            self.cfg.tasks.extend([
                               {'task':_('Retrieve Software Information'),'status':_('Pending...')}
                             ])

        if self.cfg.media_live or self.cfg.media_installation:
            if self.cfg.kickstart_manifest and not self.cfg.i_did_all_this:
                self.cfg.tasks.extend([
                                        {'task':_('Select Packages from Kickstart'),'status':_('Pending...')}
                                     ])

        self.cfg.tasks.extend([
                                {'task':_('Resolve Dependencies'),'status':_('Pending...')},
                                {'task':_('Populating Statistics'),'status':_('Pending...')},
                                {'task':_('Downloading Packages'),'status':_('Pending...')}
                             ])

        if self.cfg.getsource:
            self.cfg.tasks.extend([
                                    {'task':_('Downloading Source Packages'),'status':_('Pending...')}
                                 ])

        if self.cfg.media_installation:
            self.cfg.tasks.extend([
                                    {'task':_('Linking in Binary Packages'),'status':_('Pending...')}
                            ])
            if self.cfg.getsource:
                self.cfg.tasks.extend([
                                    {'task':_('Linking in Source Packages'),'status':_('Pending...')}
                            ])
            self.cfg.tasks.extend([
                                    {'task':_('Create Repository Information'),'status':_('Pending...')},
                                    {'task':_('Build isolinux and Installer'),'status':_('Pending...')},
                                    {'task':_('Linking in Release Notes'),'status':_('Pending...')}
                             ])

        if self.cfg.media_installation_cd:
            self.cfg.tasks.extend([
                               {'task':_('Creating CD ISO Images'),'status':_('Pending...')}
                             ])

        if self.cfg.media_installation_dvd:
            self.cfg.tasks.extend([
                               {'task':_('Creating DVD ISO Images'),'status':_('Pending...')}
                             ])

        #FIXME We will need to fix this
        #if len(self.cfg.delta_old_image) > 0:
        #    self.cfg.tasks.extend([
        #                       {'task':_('Creating Delta ISO Image'),'status':_('Pending...')}
        #                     ])

        # FIXME: This seems to just not work.
        if self.cfg.media_live and self.cfg.media_installation:
            self.cfg.tasks.extend([
                               {'task':_('Resolve Dependencies for Installation'),'status':_('Pending...')},
                               {'task':_('Downloading Extra Packages'),'status':_('Pending...')}
                               ])

        if self.cfg.getsource:
            self.cfg.tasks.extend([
                                    {'task':_('Downloading Source Packages'),'status':_('Pending...')}
                                 ])

        if self.cfg.media_live:
            self.cfg.tasks.extend([
                               {'task':_('Creating ext3 Filesystem'),'status':_('Pending...')},
                               {'task':_('Installing packages'),'status':_('Pending...')},
                               {'task':_('Configure System'),'status':_('Pending...')},
                               {'task':_('Configure Networking'),'status':_('Pending...')},
                               {'task':_('Create RAM Filesystem'),'status':_('Pending...')},
                               {'task':_('Relabel System'),'status':_('Pending...')},
                               {'task':_('Configure Bootloader'),'status':_('Pending...')}
                             ])
            if self.cfg.advanced_configuration:
                self.cfg.tasks.extend([{'task':_('Launch shell'),'status':_('Pending...')}])

            self.cfg.tasks.extend([
                               {'task':_('Unmounting filesystems'),'status':_('Pending...')}
                                ])

            if self.cfg.getbinary:
                self.cfg.tasks.extend([
                                   {'task':_('Linking in Binary Packages'),'status':_('Pending...')}
                                    ])

            if self.cfg.getsource:
                self.cfg.tasks.extend([
                                   {'task':_('Linking in Source Packages'),'status':_('Pending...')}
                                    ])

            if not self.cfg.lm_skip_fs_compression:
                self.cfg.tasks.extend([
                               {'task':_('Compressing Image'),'status':_('Pending...')}
                               ])
            self.cfg.tasks.extend([
                               {'task':_('Creating ISO Image'),'status':_('Pending...')}
                             ])

            # FIXME: This is going to be depreciated with RAW image generation?
            # We should maybe keep something like this, but launch it from the finish screen?
            if self.cfg.media_live_thumb:
                self.cfg.tasks.extend([
                                   {'task':_('Dumping ISO Image to USB Media'),'status':_('Pending...')}
                                  ])

            self.cfg.tasks.extend([
                               {'task':_('Cleaning up Build Environment'),'status':_('Pending...')}
                              ])

        self.taskstore = gtk.TreeStore(gobject.TYPE_STRING,
                                        gobject.TYPE_PYOBJECT)

        tree = self.frame_xml.get_widget("task_treeview")
        tree.set_model(self.taskstore)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Task List', renderer, markup=0)
        column.set_clickable(False)
        tree.append_column(column)

        tree.columns_autosize()
        tree.set_enable_search(False)

    def extend_task_list(self):
        self.cfg.tasks = []

        if not self.cfg.i_did_all_this:
            self.cfg.tasks.extend([
                               {'task':_('Retrieve Software Information'),'status':_('Done')}
                             ])

        if self.cfg.media_live or self.cfg.media_installation:
            if not self.cfg.kickstart_manifest:
                self.cfg.tasks.extend([
                                        {'task':_('Resolve Dependencies'),'status':_('Done')}
                                     ])
            else:
                self.cfg.tasks.extend([
                                        {'task':_('Select Packages from Kickstart'),'status':_('Done')}
                                     ])

        self.cfg.tasks.extend([
                           {'task':_('Populating Statistics'),'status':_('Done')},
                           {'task':_('Downloading Packages'),'status':_('Done')}
                         ])

        if self.cfg.getsource:
            self.cfg.tasks.extend([
                                    {'task':_('Downloading Source Packages'),'status':_('Done')}
                                 ])

        if self.cfg.media_installation:
            self.cfg.tasks.extend([
                               {'task':_('Linking in Packages'),'status':_('Done')},
                               {'task':_('Create Repository Information'),'status':_('Done')},
                               {'task':_('Build isolinux and Installer'),'status':_('Done')},
                               {'task':_('Linking in Release Notes'),'status':_('Done')}
                             ])

        if self.cfg.do_packageorder:
            self.cfg.tasks.extend([
                               {'task':_('Ordering Packages'),'status':_('Pending...')}
                             ])

        for num in self.cfg.mediatypes["index"].keys():
            mediatype = self.cfg.mediatypes["index"][num]
            if self.cfg.mediatypes[mediatype]["discs"] > 1 and self.cfg.mediatypes[mediatype]["compose"]:
                self.cfg.tasks.extend([
                                        {'task':_('Splitting Packages for %s Media') % self.cfg.mediatypes[mediatype]["label"],'status':_('Pending...')},
                                        {'task':_('Splitting Repository Information for %s Media') % self.cfg.mediatypes[mediatype]["label"],'status':_('Pending...')}
                                    ])
                for disc in range(1, self.cfg.mediatypes[mediatype]["discs"] + 1):
                    self.cfg.tasks.extend([
                                            {'task':_('Creating %s ISO Image #%d') % (self.cfg.mediatypes[mediatype]["label"],disc),'status':_('Pending...')}
                                        ])
            elif self.cfg.mediatypes[mediatype]["compose"]:
                self.cfg.tasks.extend([
                                        {'task':_('Creating %s ISO Image') % (self.cfg.mediatypes[mediatype]["label"]),'status':_('Pending...')}
                                    ])

        if self.cfg.media_live_optical or self.cfg.media_live_thumb:
            self.cfg.tasks.extend([
                               {'task':_('Resolve Dependencies for Installation'),'status':_('Pending...')},
                               {'task':_('Downloading Extra Packages'),'status':_('Pending...')},
                               {'task':_('Creating ext3 Filesystem'),'status':_('Pending...')},
                               {'task':_('Installing packages'),'status':_('Pending...')},
                               {'task':_('Configure System'),'status':_('Pending...')},
                               {'task':_('Configure Networking'),'status':_('Pending...')},
                               {'task':_('Create RAM Filesystem'),'status':_('Pending...')},
                               {'task':_('Relabel System'),'status':_('Pending...')},
                               {'task':_('Configure Bootloader'),'status':_('Pending...')}
                             ])
            if self.cfg.advanced_configuration:
                self.cfg.tasks.extend([{'task':_('Launching shell'),'status':_('Pending...')}])

            self.cfg.tasks.extend([
                                {'task':_('Unmounting filesystems'),'status':_('Pending...')}
                                ])
            if not self.cfg.lm_skip_fs_compression:
                self.cfg.tasks.extend([
                                  {'task':_('Compressing Image'),'status':_('Pending...')}
                                ])
            self.cfg.tasks.extend([
                                  {'task':_('Creating Live ISO Image'),'status':_('Pending...')}
                            ])
            if self.cfg.media_live_thumb:
                self.cfg.tasks.extend([
                                  {'task':_('Dumping ISO Image to USB Media'),'status':_('Pending...')}
                                 ])

            self.cfg.tasks.extend([
                              {'task':_('Cleaning up Build Environment'),'status':_('Pending...')}
                             ])

    def show_task_list(self):
        self.taskstore.clear()

        tree = self.frame_xml.get_widget("task_treeview")
        i = 0
        for item in self.cfg.tasks:
            if i == 0 and item["status"] == _("Pending..."):
                item["status"] = _("Running...")

            self.taskstore.append(None, [item["task"] + " - " + item["status"], None])
            if item["status"] == _("Running..."):
                try: self.frame_xml.get_widget("task_treeview").scroll_to_cell(i)
                except: pass
            i += 1
