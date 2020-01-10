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

import yum
from yum.constants import *
from yum.packages import comparePoEVR

import revisor

from revisor.errors import *
from revisor.constants import *

# Translation
from revisor.translate import _, N_
from revisor.translate import getDefaultLangs

import logging
import yum.Errors
import time

PO_COLUMN = 0
PO_SELECTED_COLUMN = 1
PO_PIX_COLUMN = 2
PO_DISPLAYSTR_COLUMN = 3
PO_PKGTYPE_COLUMN = 4

strs = {}
def _xmltrans(base, thedict):
    if strs.has_key(base):
        return strs[base]

    langs = getDefaultLangs()
    for l in langs:
        if thedict.has_key(l):
            strs[base] = thedict[l]
            return strs[base]
    strs[base] = base
    return base

def _ui_comps_sort(one, two):
    if one.display_order > two.display_order:
        return 1
    elif one.display_order < two.display_order:
        return -1
    elif _xmltrans(one.name, one.translated_name) > \
         _xmltrans(two.name, two.translated_name):
        return 1
    elif _xmltrans(one.name, one.translated_name) < \
         _xmltrans(two.name, two.translated_name):
        return -1
    return 0

# Master GTK Interface update routine
def _runGtkMain(*args):
    while gtk.events_pending():
        gtk.main_iteration()

class PackageSelection:
    def __init__(self, gui):
        self.gui = gui
        self.base = gui.base
        self.log = gui.log
        self.cfg = gui.cfg
        self.frame_xml = gui.frame_xml

        self.package_selector_dialog_widget = self.frame_xml.get_widget("package_selector_dialog")
        self.package_selector_dialog_widget.set_transient_for(self.gui.main_window)
        self.main_notebook = self.frame_xml.get_widget("notebook_package_selection")

        gui.add_buttons()

        self.connect_button_signals()

        self.pkgFilter = None
        self.sortedStore = None

        self.header_image = gui.base_screen_xml.get_widget("header_image")
        self.header_image.set_from_file(PIXMAPS_FILES + "header_packages.png")

        if not self.cfg.i_did_all_this:
            if not self.base.setup_yum():
                # It's already doing a notice... We're gonna wanna return to configuration
                self.cfg.i_did_all_this = False
                self.cfg.yumobj = yum.YumBase()
                self.cfg.repos = {}
                self.gui.displayRevisorConfiguration()
            else:
                self.cfg.i_did_all_this = True

        if self.cfg.i_did_all_this:
            self.button_vbox = self.frame_xml.get_widget("button_vbox")
            self.group_selector_popup_menu = self.frame_xml.get_widget("group_selector_popup_menu")

            self.create_stores()
            self.button_vbox.show()
            self.restore_options()
            self.populate_categories()
            try: pbar.destroy()
            except: pass

    def connect_button_signals(self):
        sigs = { "on_button_back_clicked": self.button_back_clicked,
                 "on_button_forward_clicked": self.button_forward_clicked,
                 "on_button_cancel_clicked": self.gui.button_cancel_clicked }
        self.gui.base_buttons_xml.signal_autoconnect(sigs)

        sigs = { "on_notebook_package_selection_switch_page": self.switch_notebook_page,
                 "on_details_button_clicked": self.package_selector_dialog,
                 "on_list_button_select_all_clicked": self.list_button_select_all_clicked,
                 "on_package_selector_close_button_clicked": self.package_selector_close,
                 "on_group_selector_button_press": self.group_selector_button_press,
                 "on_group_selector_popup_menu": self.group_selector_popmenu,
                 "on_gs_popup_select_all_activate": self.group_selector_select_all,
                 "on_gs_popup_select_activate": self.select_group,
                 "on_gs_popup_deselect_all_activate": self.group_selector_deselect_all,
                 "on_gs_popup_deselect_activate": self.deselect_group }
        self.frame_xml.signal_autoconnect(sigs)

        self.main_notebook.pageMap = { 0: self.category_label_activate,
                         1: self.list_label_activate,
                         2: self.search_label_activate }

    def switch_notebook_page(self, notebook, pointer, page):
        if self.main_notebook.pageMap.has_key(page):
            self.main_notebook.pageMap[page]()

    def list_label_activate(self, *args):
        self.pkgliststore.clear()
        self.populate_package_list()

    def list_button_select_all_clicked(self, button):
        self.log.debug(_("Selecting all packages"))
        self.pkgliststore.clear()
        self.populate_package_list(doinstall=True)

    def create_pkgliststore(self):
        self.pkgliststore = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                          gobject.TYPE_BOOLEAN,
                                          gobject.TYPE_STRING,
                                          gobject.TYPE_INT)

        tree = self.frame_xml.get_widget("package_list")
        tree.set_model(self.pkgliststore)

        column = gtk.TreeViewColumn(None, None)
        cbr = gtk.CellRendererToggle()
        column.pack_start(cbr, False)
        column.add_attribute(cbr, 'active', 1)
        cbr.connect("toggled", self.package_toggled, self.pkgliststore)
        tree.append_column(column)

        column = gtk.TreeViewColumn(None, None)
        txtr = gtk.CellRendererText()
        column.pack_start(txtr, False)
        column.add_attribute(txtr, 'markup', 2)
        tree.append_column(column)

#        tree.set_search_equal_func(self.__search_pkgs)

        selection = tree.get_selection()
        selection.connect('changed', self.package_selected)

#        self.pkgliststore.set_sort_column_id(3, gtk.SORT_ASCENDING)

    def create_search_stores(self):
        self.searchstore = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                          gobject.TYPE_BOOLEAN,
                                          gobject.TYPE_OBJECT,
                                          gobject.TYPE_STRING,
                                          gobject.TYPE_INT)


        tree = self.frame_xml.get_widget("search_list")
        tree.set_model(self.searchstore)

        column = gtk.TreeViewColumn(None, None)
        pixr = gtk.CellRendererPixbuf()
        column.pack_start(pixr, False)
        column.add_attribute(pixr, 'pixbuf', PO_PIX_COLUMN)
        tree.append_column(column)

        column = gtk.TreeViewColumn(None, None)
        cbr = gtk.CellRendererToggle()
        column.pack_start(cbr, False)
        column.add_attribute(cbr, 'active', 1)
        cbr.connect("toggled", self.package_toggled, self.searchstore)
        tree.append_column(column)

        column = gtk.TreeViewColumn(None, None)
        txtr = gtk.CellRendererText()
        column.pack_start(txtr, False)
        column.add_attribute(txtr, 'markup', 3)
        tree.append_column(column)

#        tree.set_search_equal_func(self.__search_pkgs)

        selection = tree.get_selection()
        selection.connect('changed', self.package_selected)
        self.searchstore.set_sort_column_id(3, gtk.SORT_ASCENDING)

    def search_label_activate(self, *args):
        w = self.frame_xml.get_widget("search_label")

        e = self.frame_xml.get_widget("search_entry")
        e.connect("activate", self.search_button_clicked)
        b = self.frame_xml.get_widget("search_button")
        b.connect("clicked", self.search_button_clicked)

    def package_toggled(self, widget, path, store):
        i = self._convert_path_to_real_iter(path, store)
        po = store.get_value(i, PO_COLUMN)
        cb = store.get_value(i, 1)
        if cb and po.repoid == "installed":
            self.cfg.yumobj.remove(po)
            self.remove_pkg_from_ks(po.name, po.arch)
#            store.set_value(i, PO_PIX_COLUMN, removepb)
        elif cb:
            self.cfg.yumobj.tsInfo.remove(po.pkgtup)
            self.remove_pkg_from_ks(po.name, po.arch)
#            store.set_value(i, PO_PIX_COLUMN, None)
        elif po.repoid == "installed":
            self.cfg.yumobj.tsInfo.remove(po.pkgtup)
            self.remove_pkg_from_ks(po.name, po.arch)
#            store.set_value(i, PO_PIX_COLUMN, installedpb)
        else:
            self.cfg.yumobj.install(po)
            self.add_pkg_to_ks(po.name, po.arch)
#            store.set_value(i, PO_PIX_COLUMN, installpb)
        store.set_value(i, 1, not cb)

    def package_selected(self, widget):
        pass

    def search_button_clicked(self, widget):
        self.searchstore.clear()
        search_value = self.frame_xml.get_widget("search_entry").get_text()
        hits = {}
        if len(search_value) > 0:
            for pkgtup in self.cfg.yumobj.pkgSack.simplePkgList():
                if search_value.lower() in pkgtup[0].lower():
                    (name,arch,epoch,ver,rel) = pkgtup
                    pos = self.get_package_objects(name=name,epoch=epoch,ver=ver,rel=rel,arch=arch)
                    if self.cfg.advanced_configuration:
                        for po in pos:
                            if not hits.has_key(pkgtup):
                                hits[pkgtup] = 1
                                self.searchstore.append([po, self.isPackageInstalled(name=po.name,epoch=po.epoch,version=po.ver,release=po.rel,arch=po.arch), None, self.listEntryString(po), 0])
                    else:
                        if not hits.has_key(pos[0].name):
                            pkgs = self.cfg.yumobj.pkgSack.returnNewestByName(name=pos[0].name)
                            if pkgs > 1:
                                pkgs = self.cfg.yumobj.bestPackagesFromList(pkgs)
                            for po in pkgs:
                                hits[pos[0].name] = 1
                                self.searchstore.append([po, self.isPackageInstalled(name=po.name,epoch=po.epoch,version=po.ver,release=po.rel,arch=po.arch), None, self.listEntryString(po), 0])

    def category_label_activate(self, *args):
        self.doRefresh()
        pass

    def show_group_selector_popup(self, button, time):
#        print >> sys.stdout, "Show group selector popup triggers..."
        menu = self.group_selector_popup_menu
        menu.popup(None, None, None, button, time)
        menu.show_all()

    def group_selector_button_press(self, widget, event):
#        print >> sys.stdout, "Button Pressed"
        if event.button == 3:
#            print >> sys.stdout, "Is button 3"
            x = int(event.x)
            y = int(event.y)
            pthinfo = widget.get_path_at_pos(x, y)
            if pthinfo is not None:
#                print >> sys.stdout, "Did click inside our window"
                sel = widget.get_selection()
                if sel.count_selected_rows() == 1:
                    path, col, cellx, celly = pthinfo
                    widget.grab_focus()
                    widget.set_cursor(path, col, 0)
                self.show_group_selector_popup(event.button, event.time)
            return 1

    def group_selector_popmenu(self, widget):
#        print >> sys.stdout, "group selector popupmenu triggers..."
        sel = widget.get_selection()
        if sel.count_selected_rows() > 0:
            self.show_group_selector_popup(0, 0)

    def group_selector_select_all(self, *args):
        """Select all optional packages for a given group entry"""

        selection = self.frame_xml.get_widget("group_selector").get_selection()
        if selection.count_selected_rows() == 0:
            return
        (model, paths) = selection.get_selected_rows()

        self.button_vbox.window.set_cursor(gdk.Cursor(gdk.WATCH))

        for p in paths:
            i = model.get_iter(p)
            grp = model.get_value(i, 2)

            # ensure the group is selected
            self.cfg.yumobj.selectGroup(grp.groupid)
            model.set_value(i, 0, True)

            # Ensure our ksobj knows
            groupList = self.cfg.ksobj._get("packages","groupList")

            grp_selected = False

            for group in groupList:
                if group.name == grp.groupid:
                    grp_selected = True
                    group.include = revisor.kickstart.constants.GROUP_ALL
            if not grp_selected:
                groupList.append(self.cfg.ksobj._Group(name=grp.groupid, include=revisor.kickstart.constants.GROUP_ALL))
                self.cfg.ksobj._set("packages","groupList",groupList)

            for pkg in grp.default_packages.keys() + grp.optional_packages.keys():
                if self.isPackageInstalled(pkg):
                    continue
                elif self.simpleDBInstalled(name=pkg):
                    txmbrs = self.cfg.yumobj.tsInfo.matchNaevr(name=pkg)
                    for tx in txmbrs:
                        if tx.output_state == TS_ERASE:
                            self.cfg.yumobj.tsInfo.remove(tx.pkgtup)
                else:
                    self.select_package(grp, pkg)

        if len(paths) == 1:
            self.set_group_description(grp)
        self.button_vbox.window.set_cursor(None)

    def group_selector_deselect_all(self, *args):
        """Deselect all default and optional packages from a given group, leaving only the mandatory packages"""

        selection = self.frame_xml.get_widget("group_selector").get_selection()
        if selection.count_selected_rows() == 0:
            return
        (model, paths) = selection.get_selected_rows()

        for p in paths:
            i = model.get_iter(p)
            grp = model.get_value(i, 2)

            # Ensure our ksobj knows
            groupList = self.cfg.ksobj._get("packages","groupList")

            # Was the group already selected...?
            grp_selected = False
            for group in groupList:
                if group.name == grp.groupid:
                    grp_selected = True
                    group.include = revisor.kickstart.constants.GROUP_REQUIRED

            if not grp_selected:
                groupList.append(self.cfg.ksobj._Group(name=grp.groupid, include=revisor.kickstart.constants.GROUP_REQUIRED))
                self.cfg.ksobj._set("packages","groupList",groupList)

            for pkg in grp.default_packages.keys() + grp.optional_packages.keys():
                if not self.isPackageInstalled(pkg):
                    continue
                elif self.simpleDBInstalled(name=pkg):
                    self.remove(name=pkg)
                else:
                    self.deselect_package(grp, pkg)
        if len(paths) == 1:
            self.set_group_description(grp)

    def group_selector_change_focus(self, selection):
        if selection.count_selected_rows() != 1:
            # if we have more groups (or no group) selected, then
            # we can't show a description or allow selecting optional
            self.set_group_description(None)
            return
        (model, paths) = selection.get_selected_rows()
        grp = model.get_value(model.get_iter(paths[0]), 2)
        self.set_group_description(grp)

    def deselect_package(self, group, pkg):
        grpid = group.groupid
        try:
            pkgs = self.cfg.yumobj.pkgSack.returnNewestByName(pkg)
        except mdErrors.PackageSackError:
            self.log.warning(_("No such package %s from group %s") % (pkg, self.group.groupid))
        if pkgs:
            pkgs = self.cfg.yumobj.bestPackagesFromList(pkgs)
        for po in pkgs:
            txmbrs = self.cfg.yumobj.tsInfo.getMembers(pkgtup=po.pkgtup)
            for txmbr in txmbrs:
                try:
                    txmbr.groups.remove(grpid)
                except ValueError:
                    self.log.debug(_("Package %s was not marked in group %s") % (po, grpid))
                if len(txmbr.groups) == 0:
                    self.cfg.yumobj.tsInfo.remove(po.pkgtup)

    def select_package(self, group, pkg):
        grpid = group.groupid
        try:
            txmbrs = self.cfg.yumobj.install(name=pkg)
        except yum.Errors.InstallError, e:
            self.log.warning(_("No package named %s available to be installed: %s") % (pkg, e))
        else:
            map(lambda x: x.groups.append(grpid), txmbrs)

    def button_back_clicked(self, button):
        # Reset repos list just to be sure
        self.cfg.i_did_all_this = False
        self.cfg.yumobj = yum.YumBase()
        self.cfg.repos = {}
        self.gui.back()

    def restore_options(self):
        # Do something with kickstart data provided, if any!!
        if self.cfg.kickstart_file and self.cfg.kickstart_manifest:
            msg_id = self.gui.statusbar.push(0,_("Adding in packages from Kickstart Data, please wait"))
            _runGtkMain()
            if self.cfg.media_installation:
                ignore_list = self.cfg.get_package_list(['installation'],['allarch'],['all',self.cfg.architecture],['all',self.cfg.version_from])
            if self.cfg.media_live:
                ignore_list = self.cfg.get_package_list(['live'],['allarch'],['all',self.cfg.architecture],['all',self.cfg.version_from])

            groupList = self.cfg.ksobj._get("packages","groupList")
            packageList = self.cfg.ksobj._get("packages","packageList")
            excludedList = self.cfg.ksobj._get("packages","excludedList")
            self.base.pkglist_from_ksdata(groupList=groupList, packageList=packageList, excludedList=excludedList, ignore_list=ignore_list)
            self.gui.statusbar.remove(0,msg_id)
            self.doRefresh()

    def check_options(self):
        if len(self.cfg.yumobj.tsInfo.getMembers()) > 0:
            self.cfg.ts_length_pre_depsolve = len(self.cfg.yumobj.tsInfo.getMembers())
            try:
                self.base.check_dependencies()
                return True
            except Exception, e:
                self.log.debug(_("Errors encountered:\n\n%s: %s") % (e.__class__, e))
                return False
        else:
            return True

    def button_forward_clicked(self, button):
        if not self.check_options():
            self.log.debug(_("Cannot pass check_options"))
            pass
        else:
            # FIXME: Add in a hook here for rebrand dialog (module modrebrand)

            if (self.cfg.media_live_optical or self.cfg.media_live_thumb) and not self.cfg.kickstart_options_customize:
                    self.log.debug(_("Doing Live Media but not customizing kickstart options"))

            self.gui.next()

    def isGroupInstalled(self, grp):
        if grp.selected:
            return True
        elif grp.installed and not grp.toremove:
            return True
        return False

    def simpleDBInstalled(self, name):
        # FIXME: doing this directly instead of using self.rpmdb.installed()
        # speeds things up by 400%
        mi = self.cfg.yumobj.ts.ts.dbMatch('name', name)
        if mi.count() > 0:
            return True
        return False

    def isPackageInstalled(self, name=None, epoch=None, version=None, release=None, arch=None, po=None):
        if po is not None:
            (name, epoch, version, release, arch) = po.returnNevraTuple()

        installed = False

        lst = self.cfg.yumobj.tsInfo.matchNaevr(name=name, epoch=epoch, ver=version, rel=release, arch=arch)

        for txmbr in lst:
            if txmbr.output_state in TS_INSTALL_STATES:
#                print >> sys.stdout, str(txmbr.name) + " is installed??"
                return True

        if installed and len(lst) > 0:
            # if we get here, then it was installed, but it's in the tsInfo
            # for an erase or obsoleted --> not going to be installed at end
            return False
        return installed

    def create_stores(self):
        self.create_category_store()
        self.create_group_store()
        self.create_package_store()
        self.create_pkgliststore()
        self.create_search_stores()
        b = gtk.TextBuffer()
        self.frame_xml.get_widget("group_description").set_buffer(b)

    def create_category_store(self):
        # display string, category object
        self.catstore = gtk.TreeStore(gobject.TYPE_STRING,
                                      gobject.TYPE_PYOBJECT)
        tree = self.frame_xml.get_widget("category_selector")
        tree.set_model(self.catstore)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Text', renderer, markup=0)
        column.set_clickable(False)
        tree.append_column(column)
        tree.columns_autosize()
        tree.set_enable_search(False)

        selection = tree.get_selection()
        selection.connect("changed", self.select_category)

    def create_group_store(self):
        # checkbox, display string, object
        self.groupstore = gtk.TreeStore(gobject.TYPE_BOOLEAN,
                                        gobject.TYPE_STRING,
                                        gobject.TYPE_PYOBJECT,
                                        gobject.TYPE_OBJECT)
        tree = self.frame_xml.get_widget("group_selector")
        tree.set_model(self.groupstore)

        column = gtk.TreeViewColumn(None, None)
        column.set_clickable(True)
        pixr = gtk.CellRendererPixbuf()
        pixr.set_property('stock-size', 1)
        column.pack_start(pixr, False)
        column.add_attribute(pixr, 'pixbuf', 3)
        cbr = gtk.CellRendererToggle()
        column.pack_start(cbr, False)
        column.add_attribute(cbr, 'active', 0)
        cbr.connect ("toggled", self.toggle_group)
        tree.append_column(column)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Text', renderer, markup=1)
        column.set_clickable(False)
        tree.append_column(column)
        tree.columns_autosize()
        tree.set_enable_search(False)
        tree.grab_focus()

        selection = tree.get_selection()
        selection.connect("changed", self.group_selector_change_focus)
        selection.set_mode(gtk.SELECTION_MULTIPLE)

    def create_package_store(self):
        self.packagestore = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                          gobject.TYPE_BOOLEAN,
                                          gobject.TYPE_OBJECT,
                                          gobject.TYPE_STRING,
                                          gobject.TYPE_INT)

        tree = self.frame_xml.get_widget("package_selector")
        tree.set_model(self.packagestore)

        column = gtk.TreeViewColumn(None, None)
        pixr = gtk.CellRendererPixbuf()
        column.pack_start(pixr, False)
        column.add_attribute(pixr, 'pixbuf', PO_PIX_COLUMN)
        tree.append_column(column)

        column = gtk.TreeViewColumn(None, None)
        cbr = gtk.CellRendererToggle()
        column.pack_start(cbr, False)
        column.add_attribute(cbr, 'active', 1)
        cbr.connect("toggled", self.package_toggled, self.packagestore)
        tree.append_column(column)

        column = gtk.TreeViewColumn(None, None)
        txtr = gtk.CellRendererText()
        column.pack_start(txtr, False)
        column.add_attribute(txtr, 'markup', 3)
        tree.append_column(column)

#        tree.set_search_equal_func(self.__search_pkgs)

        selection = tree.get_selection()
        selection.connect('changed', self.package_selected)

        self.packagestore.set_sort_column_id(3, gtk.SORT_ASCENDING)

    def _get_pix(self, fn):
        imgsize = 24
        pix = gtk.gdk.pixbuf_new_from_file(fn)
        if pix.get_height() != imgsize or pix.get_width() != imgsize:
            pix = pix.scale_simple(imgsize, imgsize,
                                   gtk.gdk.INTERP_BILINEAR)
        return pix

    def select_category(self, selection):
        self.groupstore.clear()
        (model, i) = selection.get_selected()
        if not i:
            return
        cat = model.get_value(i, 1)

        # fall back to the category pixbuf
        fbpix = None
        fn = "/usr/share/pixmaps/comps/%s.png" %(cat.categoryid,)
        if os.access(fn, os.R_OK):
            fbpix = self._get_pix(fn)
        self.populate_groups(cat.groups, fbpix)

    def populate_groups(self, groups, defaultpix=None):
        grps = map(lambda x: self.cfg.yumobj.comps.return_group(x),
                   filter(lambda x: self.cfg.yumobj.comps.has_group(x), groups))
        grps.sort(_ui_comps_sort)
        for grp in grps:
            s = "<span size=\"large\" weight=\"bold\">%s</span>" % _xmltrans(grp.name, grp.translated_name)

            fn = "/usr/share/pixmaps/comps/%s.png" % grp.groupid
            if os.access(fn, os.R_OK):
                pix = self._get_pix(fn)
            elif defaultpix:
                pix = defaultpix
            else:
                pix = None
            self.groupstore.append(None,
                                   [self.isGroupInstalled(grp),s,grp,pix])

        tree = self.frame_xml.get_widget("group_selector")
        gobject.idle_add(lambda x: x.scroll_to_point(0, 0), tree)
        self.frame_xml.get_widget("options_label").set_text("")
        self.frame_xml.get_widget("details_button").set_sensitive(False)

        # select the first group
        i = self.groupstore.get_iter_first()
        if i is not None:
            sel = self.frame_xml.get_widget("group_selector").get_selection()
            sel.select_iter(i)

    def select_group(self, selection):
        if selection.count_selected_rows() != 1:
            # if we have more groups (or no group) selected, then
            # we can't show a description or allow selecting optional
            self.set_group_description(None)
            return
        (model, paths) = selection.get_selected_rows()
        grp = model.get_value(model.get_iter(paths[0]), 2)
        self.set_group_description(grp)

    def set_group_description(self, grp):
        b = self.frame_xml.get_widget("group_description").get_buffer()
        b.set_text("")
        if grp is None:
            return

        if grp.description:
            txt = _xmltrans(grp.description, grp.translated_description)
        else:
            txt = _xmltrans(grp.name, grp.translated_name)

        inst = 0
        cnt = 0
        pkgs = grp.default_packages.keys() + grp.optional_packages.keys()
        pkgs_mandatory = len(grp.mandatory_packages.keys())
        for p in pkgs:
            if self.isPackageInstalled(p):
                cnt += 1
                inst += 1
            elif self.cfg.yumobj.pkgSack.searchNevra(name=p):
                cnt += 1
            else:
                log = logging.getLogger("yum.verbose")
                log.debug("no such package %s for %s" %(p, grp.groupid))

        b.set_text(txt)
        if not self.isGroupInstalled(grp):
            self.frame_xml.get_widget("details_button").set_sensitive(False)
            self.frame_xml.get_widget("options_label").set_text("")
        elif cnt == 0:
            self.frame_xml.get_widget("details_button").set_sensitive(False)
            self.frame_xml.get_widget("options_label").set_markup(_("<i>No optional packages (%d mandatory)</i>") %(pkgs_mandatory))
        else:
            self.frame_xml.get_widget("details_button").set_sensitive(True)
            self.frame_xml.get_widget("options_label").set_markup(_("<i>%d of %d optional packages selected (%d mandatory)</i>") %(inst, cnt, pkgs_mandatory))

    def toggle_group(self, widget, path, sel=None, updateText=True):
        if type(path) == type(str):
            i = self.groupstore.get_iter_from_string(path)
        else:
            i = self.groupstore.get_iter(path)
        if sel is None:
            sel = not self.groupstore.get_value(i, 0)

        self.groupstore.set_value(i, 0, sel)
        grp = self.groupstore.get_value(i, 2)

        self.button_vbox.window.set_cursor(gdk.Cursor(gdk.WATCH))

        if sel:
            self.cfg.yumobj.selectGroup(grp.groupid)
            groupList = self.cfg.ksobj._get("packages","groupList")
            groupList.append(self.cfg.ksobj._Group(name=grp.groupid, include=revisor.kickstart.constants.GROUP_DEFAULT))
            self.cfg.ksobj._set("packages","groupList",groupList)

        else:
            self.cfg.yumobj.deselectGroup(grp.groupid)
            # FIXME: this doesn't mark installed packages for removal.
            # we probably want that behavior with s-c-p, but not anaconda

            new_groupList = []
            for group in self.cfg.ksobj._get("packages","groupList"):
                if not grp.groupid == group.name:
                    new_groupList.append(group)
            self.cfg.ksobj._set("packages","groupList",new_groupList)

        if updateText:
            self.set_group_description(grp)

        self.button_vbox.window.set_cursor(None)

    def populate_categories(self):
        self.catstore.clear()
        cats = self.cfg.yumobj.comps.categories
        cats.sort(_ui_comps_sort)
        for cat in cats:
            s = "<span size=\"large\" weight=\"bold\">%s</span>" % _xmltrans(cat.name, cat.translated_name)
            self.catstore.append(None, [s, cat])

        # select the first category
        i = self.catstore.get_iter_first()
        if i is not None:
            sel = self.frame_xml.get_widget("category_selector").get_selection()
            sel.select_iter(i)

    def _setupCatchallCategory(self):
        # FIXME: this is a bad hack, but catch groups which aren't in
        # a category yet are supposed to be user-visible somehow.
        # conceivably should be handled by yum
        grps = {}
        for g in self.cfg.yumobj.comps.groups:
            if g.user_visible:
                grps[g.groupid] = g

        for cat in self.cfg.yumobj.comps.categories:
            for g in cat.groups:
                if grps.has_key(g):
                    del grps[g]

        if len(grps.keys()) == 0:
            return
        c = yum.comps.Category()
        c.name = _("Uncategorized")
        c._groups = grps
        c.categoryid = "uncategorized"

        self.cfg.yumobj.comps._categories[c.categoryid] = c

    def doRefresh(self):
        if len(self.cfg.yumobj.comps.categories) == 0:
            self.frame_xml.get_widget("category_selector").hide()
            self.populate_groups(map(lambda x: x.groupid, self.cfg.yumobj.comps.groups))
        else:
            self._setupCatchallCategory()
            self.populate_categories()

    def get_selected_group(self):
        """Return the selected group.
        NOTE: this only ever returns one group."""
        selection = self.frame_xml.get_widget("group_selector").get_selection()
        (model, paths) = selection.get_selected_rows()
        for p in paths:
            return model.get_value(model.get_iter(p), 2)
        return None

    def package_selector_dialog(self, gobject):
        group = self.get_selected_group()
        if group is None:
            return

        self.package_selector_dialog_widget.set_title(_("Packages in %s") %
                               _xmltrans(group.name, group.translated_name))
        self.package_selector_dialog_widget.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.package_selector_dialog_widget.set_size_request(600, 400)
        self.populate_package_selector(group)
        self.package_selector_dialog_widget.show()
        self.set_group_description(group)

    def package_selector_close(self, *args):
        self.package_selector_dialog_widget.hide()

    def populate_package_selector(self,group):
        self.packagestore.clear()
        pkgs = group.default_packages.keys() + \
               group.optional_packages.keys()
        for pkg in pkgs:
            if self.cfg.advanced_configuration:
                for po in self.cfg.yumobj.pkgSack.searchNevra(name=pkg):
                    if not po:
                        continue
                    self.packagestore.append([po, self.isPackageInstalled(name=po.name,epoch=po.epoch,version=po.ver,release=po.rel,arch=po.arch), None, self.listEntryString(po), 0])
            else:
                po = self.get_package_object(pkg)
                if not po:
                    continue
                self.packagestore.append([po, self.isPackageInstalled(name=pkg), None, self.listEntryString(po), 0])

        gobject.idle_add(lambda x: x.scroll_to_point(0, 0), self.frame_xml.get_widget("package_selector"))

    def populate_package_list(self, doinstall=False):
        # 6720 packages (fc6 core, updates and extras, no advanced config): 7 minutes, 19 seconds

        global last
        last = None
        def cmppo(po1, po2):
            # XXX: a bit ugly, but keeps things a little more responsive
            global last
            if time.time() - last > 0.05:
                last = time.time()
                _runGtkMain()

            if po1.name.lower() < po2.name.lower():
                return -1
            elif po1.name.lower() > po2.name.lower():
                return 1
            return comparePoEVR(po1, po2)

        self.packagestore.clear()
    	pbar = self.base.progress_bar(_("Building Packages List"), parent=self.gui, callback=True)

        if self.cfg.advanced_configuration:
            pkgs = self.cfg.yumobj.pkgSack.returnPackages()
        else:
            pkgs = self.cfg.yumobj.pkgSack.returnNewestByNameArch()

        num = 0
        tot = float(len(pkgs))
        self.log.debug(_("%s packages") % str(tot))
        last = time.time()
        pkgs.sort(cmppo)
        _runGtkMain()

        pkgList = []

        for pkg in pkgs:
            num += 1
#            pos = self.cfg.yumobj.pkgSack.searchNevra(name=pkg.name)
#            for po in pos:
#                self.pkgliststore.append([po, self.isPackageInstalled(name=po.name,version=po.version,epoch=po.epoch,release=po.release,arch=po.arch), None, self.listEntryString(po), 0])
            if doinstall:
                self.cfg.yumobj.install(pkg)
                pkgList.append(pkg.name)

            self.pkgliststore.append([pkg, self.isPackageInstalled(name=pkg.name,epoch=pkg.epoch,version=pkg.ver,release=pkg.rel,arch=pkg.arch), self.listEntryString(pkg), 0])

            if (num/tot) > pbar.get_fraction() + 0.01:
                pbar.set_fraction(num / tot)
                _runGtkMain()

        self.cfg.ksobj._set("packages","packageList",yum.misc.unique(pkgList))

        pbar.destroy()
        _runGtkMain()

    def get_package_object(self, name=None, epoch=None, ver=None, rel=None, arch=None):
        pos = self.cfg.yumobj.pkgSack.searchNevra(name=name, epoch=epoch, ver=ver, rel=rel, arch=arch)
        if len(pos) > 0:
            return pos[0]
        return None

    def get_package_objects(self, name=None, epoch=None, ver=None, rel=None, arch=None):
        pos = self.cfg.yumobj.pkgSack.searchNevra(name=name, epoch=epoch, ver=ver, rel=rel, arch=arch)
        self.log.debug(_("For %s-%s:%s-%s.%s, we find %d matches") % (name,epoch,ver,rel,arch,len(pos)), level=9)
        if len(pos) > 0:
            return pos
        return []

    def select_group(self, *args):
        selection = self.frame_xml.get_widget("group_selector").get_selection()
        if selection.count_selected_rows() == 0:
            return

        (model, paths) = selection.get_selected_rows()
        for p in paths:
            self.toggle_group(model, p, True, False)

    def deselect_group(self, *args):
        selection = self.frame_xml.get_widget("group_selector").get_selection()
        if selection.count_selected_rows() == 0:
            return

        (model, paths) = selection.get_selected_rows()
        for p in paths:
            self.toggle_group(model, p, False, False)

    def __search_pkgs(self, model, col, key, i):
        val = model.get_value(i, 2).returnSimple('name')
        if val.lower().startswith(key.lower()):
            return False
        return True

    def listEntryString(self, po):
        desc = po.returnSimple('summary') or ''
        desc = desc.rstrip()
        if desc:
            desc = gobject.markup_escape_text(desc)
            desc = ' - %s' % (desc)
        desc = "<b>%s-%s:%s-%s.%s</b>%s <small><i>(from %s)</i></small>" %(po.name, po.epoch, po.version, po.release, po.arch, desc, po.repoid)
        return desc

    def _convert_path_to_real_iter(self, path, store):
        if self.pkgFilter is not None:
            path = self.pkgFilter.convert_path_to_child_path(path)
        if self.sortedStore is not None:
            path = self.sortedStore.convert_path_to_child_path(path)
        i = store.get_iter(path)
        return i

    def remove_pkg_from_ks(self, name, arch):
        """Removes a package from the PackageList in ks, or excludes it"""
        packageList = self.cfg.ksobj._get("packages","packageList")
        new_packageList = []

        for pkg in packageList:
            if not pkg == name:
                new_packageList.append(pkg)

        self.cfg.ksobj._set("packages","packageList",new_packageList)

        pkg_excluded = False
        excludedList = self.cfg.ksobj._get("packages","excludedList")

        for pkg in excludedList:
            if pkg == name:
                pkg_excluded = True

        if not pkg_excluded:
            excludedList.append(name)

        self.cfg.ksobj._set("packages","excludedList", excludedList)

    def add_pkg_to_ks(self, name, arch):
        """Adds a package to the packageList, removes it from the excludedList"""
        excludedList = self.cfg.ksobj._get("packages","excludedList")
        new_excludedList = []

        for pkg in excludedList:
            if not pkg == name:
                new_excludedList.append(pkg)

        self.cfg.ksobj._set("packages","excludedList",new_excludedList)

        pkg_selected = False
        packageList = self.cfg.ksobj._get("packages","packageList")

        for pkg in packageList:
            if pkg == name:
                pkg_selected = True

        if not pkg_selected:
            packageList.append(name)

        self.cfg.ksobj._set("packages","packageList", packageList)
