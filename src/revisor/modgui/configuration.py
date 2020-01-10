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
import sys
import gtk
import gtk.glade
import gobject
import gtk.gdk as gdk
import yum

from ConfigParser import SafeConfigParser, RawConfigParser

# Import constants
from revisor.constants import *

# Translation
from revisor.translate import _, N_

class RevisorConfiguration:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.select_model = self.frame_xml.get_widget("revisor_config_select_model")
        self.add_repo = self.frame_xml.get_widget("button_add_repo")
        self.add_repo_dialog = self.frame_xml.get_widget("add_repo_dialog")
        self.repo_ok_button = self.frame_xml.get_widget("repo_ok_button")
        self.repo_cancel_button = self.frame_xml.get_widget("repo_cancel_button")

        self.repo_name = self.frame_xml.get_widget("name")
        self.repo_description = self.frame_xml.get_widget("description")
        self.repo_baseurl = self.frame_xml.get_widget("baseurl")
        self.repo_mirrorlist = self.frame_xml.get_widget("mirrorlist")
        self.repo_exclude = self.frame_xml.get_widget("exclude")
        self.repo_includepkgs = self.frame_xml.get_widget("includepkgs")
        self.repo_gpgcheck = self.frame_xml.get_widget("gpgcheck")
        self.repo_gpgkey = self.frame_xml.get_widget("gpgkey")
        self.repo_protect = self.frame_xml.get_widget("protect")
        self.repo_save = self.frame_xml.get_widget("save")

        gui.add_buttons()

        self.connect_button_signals()

        self.restore_options()

        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(PIXMAPS_FILES + "header_yum.png")

    # widgets:
    # repo_treeview - repository selection box (treeview)
    # config_select_model - model selection
    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }

        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_button_revisor_config_apply_model_clicked": self.config_apply_model,
                 "on_button_revisor_config_refresh_clicked": self.config_refresh_clicked,
                 "on_button_add_repo_clicked": self.button_add_repo_clicked }

        self.frame_xml.signal_autoconnect(sigs)

    def button_add_repo_clicked(self, button):
        self.add_repo_dialog.show_all()
        self.repo_protect.set_sensitive(False)
        self.handler = self.repo_ok_button.connect("clicked", self.addRepository)
        self.handler = self.repo_cancel_button.connect("clicked", self.button_add_repo_cancel_clicked)

    def button_add_repo_cancel_clicked(self, *args):
        # Empty all fields, too
        self.reset_repo_dialog()
        self.add_repo_dialog.hide()

    def reset_repo_dialog(self):
        self.repo_name.set_text("")
        self.repo_description.set_text("")
        self.repo_baseurl.set_text("")
        self.repo_mirrorlist.set_text("")
        self.repo_exclude.set_text("")
        self.repo_includepkgs.set_text("")
        self.repo_gpgcheck.set_active(False)
        self.repo_gpgkey.set_text("")
        self.repo_protect.set_active(False)
        self.repo_save.set_active(False)

    def addRepository(self, *args):
        name = self.repo_name.get_text()
        description = self.repo_description.get_text()
        baseurl = self.repo_baseurl.get_text()
        mirrorlist = self.repo_mirrorlist.get_text()
        exclude = self.repo_exclude.get_text()
        includepkgs = self.repo_includepkgs.get_text()
        gpgcheck = self.repo_gpgcheck.get_active()
        gpgkey = self.repo_gpgkey.get_text()
        protect = self.repo_protect.get_active()
        save = self.repo_save.get_active()

        if baseurl == "" and mirrorlist == "":
            self.log.error(_("You have not specified a Base URL or Mirror List"))
            return
        if gpgcheck and (gpgkey == "" or not os.access(gpgkey, os.R_OK)):
            self.log.error(_("GPG Check enabled but no valid GPG Key file found"))
            return

        # Do something with the plugin settings and the loaded plugins

        # Add the repository to the yum configuration
        repoObj = yum.yumRepo.YumRepository(name)
        repoObj.setAttribute('name', description)

        if not baseurl == "":
            try:
                repoObj.setAttribute('baseurl', baseurl)
            except ValueError, e:
                self.log.error(_("ValueError in baseurl: %s") % e)

        if not mirrorlist == "":
            try:
                repoObj.setAttribute('mirrorlist', mirrorlist)
            except ValueError, e:
                self.log.error(_("ValueError in mirrorlist: %s") % e)

        repoObj.setAttribute('exclude', exclude)
        repoObj.setAttribute('includepkgs', includepkgs)
        #repoObj.setAttribute('protect', protect)
        repoObj.setAttribute('gpgcheck', gpgcheck)
        repoObj.setAttribute('gpgkey', gpgkey)
        repoObj.setAttribute('enabled', 1)
        self.cfg.added_repos.append(repoObj)

        # To the store, too
        try:
            self.repo_treeview.remove_column(self.repo_column_select)
            self.repo_treeview.remove_column(self.repo_column_name)
            self.repo_treeview.remove_column(self.repo_column_desc)
        except:
            pass

        self.load_repositories()
        # If save is set, add to the yum configuration file and remove from the added_repos[]
        if save:
            config = RawConfigParser()
            config.read(self.cfg.main_conf)
            config.add_section(name)
            config.set(name,"name",description)
            config.set(name,"baseurl",baseurl)
            config.set(name,"mirrorlist",mirrorlist)
            config.set(name,"exclude",exclude)
            config.set(name,"includepkgs",includepkgs)
            config.set(name,"gpgcheck",gpgcheck)
            config.set(name,"gpgkey",gpgkey)
            config.set(name,"protect",str(protect))

            fp = open(self.cfg.main,"w")
            config.write(fp)
            fp.close()

        self.reset_repo_dialog()
        self.add_repo_dialog.hide()

    def config_refresh_clicked(self, button):
        self.config_refresh()

    def config_refresh(self):

        widget_rc = self.frame_xml.get_widget("revisor_config")
        widget_cbox_parent = self.frame_xml.get_widget("revisor_config_table")

        self.cfg.config = widget_rc.get_text()
        models = self.config_sections(self.cfg.config)

        if models:
            self.load_models(widget_rc.get_text())

            widget_cbox_parent.attach(self.select_model,1,2,1,2,yoptions=gtk.EXPAND,xpadding=5,ypadding=5)
            self.select_model.show()
            self.cfg.config = widget_rc.get_text()

            model_selected = self.select_model.get_active_text()
            self.cfg.load_model()

            self.repo_treeview = self.frame_xml.get_widget("repo_treeview")
            if not model_selected == "" and not model_selected == None:
                if self.config_has_option(self.cfg.config,model_selected,"main"):
                    self.cfg.model = model_selected
                    if self.cfg.check_setting_main(self.revisor_parser.get(model_selected,"main")):
                        self.cfg.main = self.revisor_parser.get(model_selected,"main")

                    try:
                        self.repo_treeview.remove_column(self.repo_column_select)
                        self.repo_treeview.remove_column(self.repo_column_name)
                        self.repo_treeview.remove_column(self.repo_column_desc)
                    except:
                        pass

                    self.load_repositories()
        else:
            self.log.error(_("%s is not a valid Revisor configuration file") % widget_rc.get_text())

    def config_changed(self, widget):

        widget_rc = self.frame_xml.get_widget("revisor_config")
        widget_cbox_parent = self.frame_xml.get_widget("revisor_config_table")

        if os.access(widget_rc.get_text(), os.R_OK) and os.path.isfile(widget_rc.get_text()):
            self.config_refresh()

    def config_apply_model(self, widget):
        model_selected = self.select_model.get_active_text()

        self.repo_treeview = self.frame_xml.get_widget("repo_treeview")
        print model_selected
        if not model_selected == "" and not model_selected == None:
            if self.config_has_option(self.cfg.config,model_selected,"main"):
                self.cfg.model = model_selected
                self.cfg.main_conf = self.revisor_parser.get(model_selected,"main")
                try:
                    self.repo_treeview.remove_column(self.repo_column_select)
                    self.repo_treeview.remove_column(self.repo_column_name)
                    self.repo_treeview.remove_column(self.repo_column_desc)
                except:
                    pass

                self.cfg.load_model()
                self.load_repositories()
            else:
                self.log.error(_("The configured model does not have the mandatory 'main' configuration directive."))
        else:
            self.log.error(_("Invalid model. Please choose a valid model."))

    def button_back_clicked(self, button):
        self.store_options()
        self.gui.back()

    def button_forward_clicked(self, button):
        if not self.check_options():
            pass
        else:
            self.store_options()

            try: os.makedirs(self.cfg.yum_cache_dir)
            except: self.log.error("Unable to create yum cache directory %s" % self.cfg.yum_cache_dir)
            self.gui.next()

    def load_repositories(self):
        repo_parser = SafeConfigParser()
        self.repo_parser = repo_parser
        # FIXME (try except os.access)
        repo_parser.read(self.cfg.main_conf)

        # Weee, this is where we know what the install_root is, and what the cachedir is
        if repo_parser.has_option("main","installroot") and repo_parser.has_option("main","cachedir"):
            self.cfg.yum_cache_dir = os.path.join("%s/%s" % (repo_parser.get("main","installroot"),repo_parser.get("main","cachedir")))
        else:
            self.cfg.yum_cache_dir = "/var/tmp/revisor/yumcache"

        #self.log.debug("Setting yum log file to %s" % self.cfg.yum_cache_dir)

        # widget - repo_treeview
        self.repoStore = gtk.ListStore(gobject.TYPE_BOOLEAN,
                                      gobject.TYPE_STRING,
                                      gobject.TYPE_STRING)

        self.repo_column_select = gtk.TreeViewColumn(None, None)
        cbr = gtk.CellRendererToggle()
        self.repo_column_select.pack_start(cbr, False)
        self.repo_column_select.add_attribute(cbr, 'active', 0)
        cbr.connect("toggled", self._repoToggled)
        self.repo_treeview.append_column(self.repo_column_select)

        self.repo_column_name = gtk.TreeViewColumn(None, None)
        txtr = gtk.CellRendererText()
        self.repo_column_name.pack_start(txtr, False)
        self.repo_column_name.add_attribute(txtr, 'markup', 1)
        self.repo_treeview.append_column(self.repo_column_name)

        self.repo_column_desc = gtk.TreeViewColumn(None, None)
        txtr = gtk.CellRendererText()
        self.repo_column_desc.pack_start(txtr, False)
        self.repo_column_desc.add_attribute(txtr, 'markup', 2)
        self.repo_treeview.append_column(self.repo_column_desc)

        self.repoStore.set_sort_column_id(1, gtk.SORT_ASCENDING)

        for repo in repo_parser._sections:
            if not repo == "main":
                # Remove all disabled repos
                if not self.cfg.repos_enablesource and repo.find("source") >= 0:
                    continue
                if not self.cfg.repos_enabledebuginfo and repo.find("debuginfo") >= 0:
                    continue
                if not self.cfg.repos_enabletesting and repo.find("testing") >= 0:
                    continue
                if not self.cfg.repos_enabledevelopment and repo.find("devel") >= 0:
                    continue

                if self.repo_parser.has_option(repo,"enabled"):
                    if self.repo_parser.get(repo,"enabled") == "1":
                        repo_enabled = True
                    else:
                        repo_enabled = False
                else:
                    repo_enabled = True

                if repo in self.cfg.repos and self.cfg.repos[repo]:
                    repo_enabled = True
                elif repo in self.cfg.repos and not self.cfg.repos[repo]:
                    repo_enabled = False

                self.repoStore.append([repo_enabled,repo,"<i>" + self.repo_parser.get(repo,"name") + "</i>"])
                self.cfg.repos[repo] = repo_enabled

        for repo in self.cfg.added_repos:
            self.repoStore.append([True,repo,"<i>" + repo.name + "</i>"])

        self.repo_treeview.set_model(self.repoStore)

    def _repoToggled(self, widget, path):
        cfg = self.gui.cfg
        i = self.repoStore.get_iter(path)
        repo_toggled = self.repoStore.get_value(i, 1)
        if self.repoStore.get_value(i, 0):
            self.repoStore.set_value(i, 0, False)
            self.cfg.repos[repo_toggled] = False
            status = "disabled"
        else:
            self.repoStore.set_value(i, 0, True)
            self.cfg.repos[repo_toggled] = True
            status = "enabled"

        self.log.debug("%s is now %s" % (repo_toggled, status))

    def check_options(self):
        widget_rc = self.frame_xml.get_widget("revisor_config")
        config = widget_rc.get_text()

        widget_dd = self.frame_xml.get_widget("entry_destination_directory")
        self.cfg.destination_directory = widget_dd.get_text()

        if not os.access(config, os.R_OK):
            self.log.error(_("File %s is not accessible.") % config)
            return False

        file_main_ok = False

        if self.config_has_option(config,self.select_model.get_active_text(),"main"):
            if not os.access(self.revisor_parser.get(self.select_model.get_active_text(),"main"), os.R_OK):
                self.log.error(_("The 'main' option configuration directive has a non-accessible file: ") + self.revisor_parser.get(self.select_model.get_active_text(),"main"))
                return False
            else:
                self.log.debug(_("Configuration file's 'main' directive OK"))
                # Set the configuration file,
                self.cfg.config = config
                self.cfg.model = self.select_model.get_active_text()
                self.cfg.main = self.revisor_parser.get(self.select_model.get_active_text(),"main")

                # And reload the options
                self.cfg.load_model()

                # Let's check for the existance of the directories we are going to work with:
                if not self.cfg.check_working_directory():
                    return False

                # Let's check for the existance of the directories in which our products go:
                self.cfg.check_destination_directory()

                one_repo_set = False
                for repo in self.cfg.repos:
                    if self.cfg.repos[repo]:
                        one_repo_set = True

                base_repo_set = False
                if "core" in self.cfg.repos and self.cfg.repos["core"]:
                    base_repo_set = True
                elif "base" in self.cfg.repos and self.cfg.repos["base"]:
                    base_repo_set = True
                elif "fedora" in self.cfg.repos and self.cfg.repos["fedora"]:
                    base_repo_set = True
                elif "development" in self.cfg.repos and self.cfg.repos["development"]:
                    base_repo_set = True
                elif "fedora-local" in self.cfg.repos and self.cfg.repos["fedora-local"]:
                    base_repo_set = True

                if not one_repo_set or not base_repo_set:
                    self.log.warning(_("You have not selected any of the basic repositories. Please make sure that one of 'fedora', 'core', 'base' or 'development', or an equivalent repository has been configured"))

                return True
        else:
            self.log.error(_("Configuration file '%s', section '%s' does not have the mandatory 'main' option") % (config, self.select_model.get_active_text()))
            return False

    def restore_options(self):
        widget_rc = self.frame_xml.get_widget("revisor_config")

        widget_rc.set_text(self.cfg.config)
        widget_rc.connect('changed', self.config_changed)

        widget_dd = self.gui.frame_xml.get_widget("entry_destination_directory")

        if self.cfg.model:
            self.cfg.destination_directory = self.cfg.destination_directory.replace("/%s" % self.cfg.model,"")

        widget_dd.set_text(self.cfg.destination_directory)

        self.load_models()
        self.cfg.model = self.select_model.get_active_text()

        self.load_selected_model()

    def load_selected_model(self):
        widget_cbox_parent = self.frame_xml.get_widget("revisor_config_table")
        self.repo_treeview = self.frame_xml.get_widget("repo_treeview")

        if not self.cfg.model == "" and not self.cfg.model == None:
            if self.config_has_option(self.cfg.config,self.cfg.model,"main"):
                self.cfg.main_conf = self.revisor_parser.get(self.cfg.model,"main")
                try:
                    self.repo_treeview.remove_column(self.repo_column_select)
                    self.repo_treeview.remove_column(self.repo_column_name)
                    self.repo_treeview.remove_column(self.repo_column_desc)
                except:
                    pass

                self.load_repositories()

        widget_cbox_parent.attach(self.select_model,1,2,1,2,yoptions=gtk.EXPAND,xpadding=5,ypadding=5)
        self.select_model.show()

    def load_models(self, config=None):
        widget_cbox_parent = self.frame_xml.get_widget("revisor_config_table")
        self.select_model.hide()
        self.select_model.destroy()

        if config == None:
            models = self.config_sections(self.cfg.config)
        else:
            models = self.config_sections(config)

        self.select_model = gtk.combo_box_new_text()
        self.select_model.connect('changed', self.config_apply_model)

        i=0
        for model in models:
            self.select_model.append_text(model)
            if model == self.cfg.model:
                self.select_model.set_active(i)
            i += 1

        if not self.select_model.get_active() >= 0:
            self.select_model.set_active(0)

    def store_options(self):
        widget_rc = self.frame_xml.get_widget("revisor_config")
        self.cfg.config = widget_rc.get_text()

        self.cfg.model = self.select_model.get_active_text()

    def config_sections(self, config):
        parser = SafeConfigParser()
        if os.access(config, os.R_OK):
            try:
                parser.read(config)
                self.gui.log.info(_("Reading configuration file %s") % config)
                parser_sections = parser._sections.keys()
                # Omit the [revisor] section
                sections = []
                for section in parser_sections:
                    if not section == "revisor":
                        sections.append(section)

                sections.sort()
                return sections

            except:
                return False
        else:
            self.log.error(_("Could not read configuration file %s") % config)

    def config_has_option(self, config, section, option):
        self.revisor_parser = SafeConfigParser()
        # FIXME (try except os.access)
        self.revisor_parser.read(config)
        if self.revisor_parser.has_option(section,option):
            return True
        else:
            return False

