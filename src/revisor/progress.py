# -*- coding: utf-8 -*-
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

import math
import rpm
import sys
import urllib2
import time
from yum.constants import *
import urlgrabber, urlgrabber.progress
import logging

# Import constants
from revisor.constants import *
from revisor.errors import *

# Translation
from revisor.translate import _, N_

class ProgressGUI:
    def __init__(self, title="", parent=None, xml=None):
        import gtk
        import gtk.glade
        import gobject
        import gtk.gdk as gdk

        """All we want is a widget. It's new, so it's set to fraction 0.0"""
        self.have_dialog = False
        self.have_pbar = False
        if parent and not len(parent.cfg.tasks) > 0:
            self.have_dialog = True
            self.dialog_xml = gtk.glade.XML(GLADE_FILES + "progress.glade", domain=domain)
            self.dialog = self.dialog_xml.get_widget("ProgressDialog")
            self.dialog_title = self.dialog_xml.get_widget("ProgressTitle")
            self.dialog_bar = self.dialog_xml.get_widget("ProgressBar")
            self.dialog_label = self.dialog_xml.get_widget("ProgressLabel")
            self.dialog.set_modal(True)
            self.dialog.set_transient_for(parent.main_window)
            self.dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
            self.dialog.set_title(title)

            self.dialog_title.set_markup("<span weight=\"bold\" size=\"x-large\">" + title + "</span>")
            self.pbar = self.dialog_bar
            self.label = self.dialog_title
            self.show()

        else:
            self.have_pbar = True
            self.pbar = xml.get_widget("part_progress")
            self.tbar = xml.get_widget("total_progress")
            self.label = xml.get_widget("details_view")

        self.set_markup(title)

        self.check_task_list(parent)

    def check_task_list(self, parent):
        if parent and len(parent.cfg.tasks) > 0 and self.have_pbar:
            done_running = False
            done_done = False
            tasks_done = 0.0
            for task in parent.cfg.tasks:
                if task["status"] == _("Pending...") and not done_running:
                    task["status"] = _("Running...")
                    done_running = True
                    continue
                if task["status"] == _("Running...") and not done_done:
                    task["status"] = _("Done")
                    done_done = True
                    continue
                if task["status"] == _("Done"):
                    tasks_done += 1.0
                if done_running and done_done:
                    break
            # Also update the total_progress bar
            self.tbar.set_fraction(int(tasks_done)/float(len(parent.cfg.tasks)))

#            parent.BuildMedia.show_task_list()
#            parent.BuildMedia.total_progress.set_fraction(tasks_done/len(self.tasks))
#            self._runGtkMain()

    # Master GTK Interface update routine
    def _runGtkMain(*args):
        import gtk
        while gtk.events_pending():
            gtk.main_iteration()

    def show(self):
        if self.have_dialog:
            self.dialog.show()
#            self.dialog.window.set_cursor(gdk.Cursor(gdk.WATCH))
            self._runGtkMain()

    def destroy(self):
        if self.have_dialog:
            self.dialog.destroy()
        self._runGtkMain()

    def set_fraction(self, fract):
        if fract <= 1.0:
            self.pbar.set_fraction(fract)
            self._runGtkMain()

    def get_fraction(self):
        return self.pbar.get_fraction()

    def set_markup(self, txt):
        if self.have_dialog:
            self.label.set_markup("<span weight=\"bold\" size=\"x-large\">" + txt + "</span>")
        elif self.have_pbar and not self.label == None:
            buf = self.label.get_buffer()
            buf.set_text(txt)
            self.label.set_buffer(buf)
        self._runGtkMain()

    def set_pbar_text(self, txt):
        self.pbar.set_text(txt)
        self._runGtkMain()

class ProgressCallbackGUI(ProgressGUI):
    def __init__(self, title="", parent=None, num_tasks=1, xml=None):
        """All we want is a widget, and the number of tasks we expect to complete"""
        ProgressGUI.__init__(self, title=title, parent=parent, xml=xml)

        self.num_tasks = float(num_tasks)
        self.cur_task = 0
        self.this_task = 1

    def progressbar(self, current, total, name=None):
        pct = float(current) / total
        curval = self.get_fraction()
        newval = (pct * 1/self.num_tasks) * self.this_task + (self.cur_task / self.num_tasks)

        if newval > curval + 0.001:
            self.pbar.set_fraction(newval)
            self._runGtkMain()

    def next_task(self, incr=1, next=1):
        self.cur_task += incr
        self.this_task = next
        self.set_pbar_text("")
        self.set_fraction(self.cur_task / self.num_tasks)
        self._runGtkMain()

class TransactionProgressGUI:
    # FIXME: get the gtkmain crap out of this...
    def __init__(self, progress, log=None):
        self.progress = progress

        self.rpmFD = None
        self.total = None
        self.num = 0

        self.log = log

        # stuff so that we can do the logging to the yum logfile
        self.installed_pkg_names = []
        self.tsInfo = None

    # Master GTK Interface update routine
    def _runGtkMain(*args):
        import gtk
        while gtk.events_pending():
            gtk.main_iteration()

    def callback(self, what, amount, total, h, user):
        # this is the amount of the progress bar we use for the preparing step
        PREP = 0.25
        logmsg = ""

        if what == rpm.RPMCALLBACK_TRANS_START:
            if amount == 6:
                self.total = float(total)
                self.progress.set_markup(_("Preparing transaction"))
        elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
            self.progress.set_fraction(amount * PREP / total)
        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.progress.set_fraction(PREP) # arbitrary...
            self.progress.set_markup("")
        elif what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            if h is not None:
                hdr, rpmloc = h
                try:
                    self.rpmFD = os.open(rpmloc, os.O_RDONLY)
                except OSError, e:
                    raise RevisorError, _("Unable to open %s: %s") %(rpmloc, e)
                self.progress.set_markup(_("Installing %s") % (hdr['name']))
                self.log.debug(_("Installing %s") % (hdr['name']))
                self.installed_pkg_names.append(hdr['name'])
                self._runGtkMain()
                return self.rpmFD
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            os.close(self.rpmFD)
            self.progress.set_markup("")
            self.num += 1
            self.progress.set_fraction(self.num / self.total * (1 - PREP) + PREP)
            self.rpmFD = None

            hdr, rpmloc = h
            # logging shenanigans
            if hdr['epoch'] is not None:
                epoch = "%s" %(hdr['epoch'],)
            else:
                epoch = "0"
            (n,a,e,v,r) = hdr['name'], hdr['arch'], epoch, hdr['version'], hdr['release']
            pkg = "%s.%s %s-%s" %(n,a,v,r)
            if self.tsInfo:
                txmbr = self.tsInfo.getMembers(pkgtup=(n,a,e,v,r))[0]
                if txmbr.output_state == TS_UPDATE:
                    logmsg = _("Updated: %s") %(pkg,)
                else:
                    logmsg = _("Installed: %s") %(pkg,)

        elif what == rpm.RPMCALLBACK_INST_PROGRESS:
            cur = self.progress.get_fraction()
            perpkg = 1 / self.total * (1 - PREP)
            if total > 0:
                pct = amount/float(total)
            else:
                pct = 0
            new = self.num / self.total * (1 - PREP) + PREP + (perpkg * pct)
            if new - cur > 0.05:
                self.progress.set_fraction(new)
        elif what == rpm.RPMCALLBACK_UNINST_START:
            self.progress.set_markup(_("Cleanup %s") %(h,))
        elif what == rpm.RPMCALLBACK_UNINST_PROGRESS:
            cur = self.progress.get_fraction()
            perpkg = 1 / self.total * (1 - PREP)
            if total > 0:
                pct = amount/float(total)
            else:
                pct = 0
            new = self.num / self.total * (1 - PREP) + PREP + (perpkg * pct)
            if new - cur > 0.05:
                self.progress.set_fraction(new)
        elif what == rpm.RPMCALLBACK_UNINST_STOP:
            self.num += 1
            self.progress.set_fraction(self.num / self.total * (1 - PREP) + PREP)
            if h not in self.installed_pkg_names:
                logmsg = _("Erased: %s") %(h,)

        self._runGtkMain()
        if len(logmsg) > 0:
            log = logging.getLogger("yum.filelogging")
            log.info(logmsg)

##
##
## CLI Progress Bars
##
##

class ProgressCLI:
    def __init__(self, title=""):
        """All we want is a widget. It's new, so it's set to fraction 0.0"""
        self.title = title
        self.fract = 0.0
        self.columns = os.getenv("COLUMNS", 80)
        self.space_left = 0
        self.space_right = 3
        self.reserved_left = 31
        self.reserved_right = 6
        self.set_fraction(self.fract)

    def show(self):
        pass

    def destroy(self):
        self.set_fraction(1.0)
        sys.stdout.write('\r\n')
        sys.stdout.flush()

    def set_fraction(self, fract):
        if fract <= 1.0:
            self.fract = fract

            room = self.columns - self.space_left - self.space_right - self.reserved_left - self.reserved_right

            perc = round(fract*100,1)
            show = int(room*perc/100)
            not_show = room - show
            sys.stdout.write('\r' + self.title + ': ' + str(' ' * (self.columns - len(self.title))) + ' ')
            sys.stdout.write('\r' + self.title + ': ' + str(' ' * (self.reserved_left - len(self.title))) + str('#' * show) + str(' ' * not_show) + str(' ' * (self.reserved_right-len(str(perc)))) + str(perc) + '% ')
            sys.stdout.flush()

    def get_fraction(self):
        return self.fract

    def set_markup(self, txt):
        pass

    def set_pbar_text(self, txt):
        pass

class ProgressCallbackCLI(ProgressCLI):
    def __init__(self, title="", num_tasks=1):
        """All we want is a widget, and the number of tasks we expect to complete"""
        ProgressCLI.__init__(self, title=title)

        self.num_tasks = float(num_tasks)
        self.cur_task = 0
        self.this_task = 1

    def progressbar(self, current, total, name=None):
        pct = float(current) / total
        curval = self.get_fraction()
        newval = (pct * 1/self.num_tasks) * self.this_task + (self.cur_task / self.num_tasks)

        if newval > curval + 0.01:
            self.set_fraction(newval)

    def next_task(self, incr=1, next=1):
        self.cur_task += incr
        self.this_task = next
        self.set_pbar_text("")
        self.set_fraction(float(self.cur_task) / float(self.num_tasks))

class TransactionProgressCLI:
    def __init__(self, progress, log=None):
        self.progress = progress

        self.rpmFD = None
        self.total = None
        self.num = 0

        self.log = log

        # stuff so that we can do the logging to the yum logfile
        self.installed_pkg_names = []
        self.tsInfo = None

    def callback(self, what, amount, total, h, user):
        # this is the amount of the progress bar we use for the preparing step
        PREP = 0.25
        logmsg = ""

        if what == rpm.RPMCALLBACK_TRANS_START:
            if amount == 6:
                self.total = float(total)
        elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
            self.progress.set_fraction(amount * PREP / total)
        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.progress.set_fraction(PREP) # arbitrary...
        elif what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            if h is not None:
                hdr, rpmloc = h
                try:
                    self.rpmFD = os.open(rpmloc, os.O_RDONLY)
                except OSError, e:
                    raise RevisorError, _("Unable to open %s: %s") %(rpmloc, e)
                self.log.debug(_("Installing %s") % (hdr['name']), level=4)
                self.installed_pkg_names.append(hdr['name'])
                return self.rpmFD
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            os.close(self.rpmFD)
            self.num += 1
            self.progress.set_fraction(self.num / self.total * (1 - PREP) + PREP)
            self.rpmFD = None

            hdr, rpmloc = h
            # logging shenanigans
            if hdr['epoch'] is not None:
                epoch = "%s" %(hdr['epoch'],)
            else:
                epoch = "0"
            (n,a,e,v,r) = hdr['name'], hdr['arch'], epoch, hdr['version'], hdr['release']
            pkg = "%s.%s %s-%s" %(n,a,v,r)
            if self.tsInfo:
                txmbr = self.tsInfo.getMembers(pkgtup=(n,a,e,v,r))[0]
                if txmbr.output_state == TS_UPDATE:
                    logmsg = _("Updated: %s") %(pkg,)
                else:
                    logmsg = _("Installed: %s") %(pkg,)

        elif what == rpm.RPMCALLBACK_INST_PROGRESS:
            cur = self.progress.get_fraction()
            perpkg = 1 / self.total * (1 - PREP)
            if total > 0:
                pct = amount/float(total)
            else:
                pct = 0
            new = self.num / self.total * (1 - PREP) + PREP + (perpkg * pct)
            if new - cur > 0.05:
                self.progress.set_fraction(new)
        elif what == rpm.RPMCALLBACK_UNINST_PROGRESS:
            cur = self.progress.get_fraction()
            perpkg = 1 / self.total * (1 - PREP)
            if total > 0:
                pct = amount/float(total)
            else:
                pct = 0
            new = self.num / self.total * (1 - PREP) + PREP + (perpkg * pct)
            if new - cur > 0.05:
                self.progress.set_fraction(new)
        elif what == rpm.RPMCALLBACK_UNINST_STOP:
            self.num += 1
            self.progress.set_fraction(self.num / self.total * (1 - PREP) + PREP)
            if h not in self.installed_pkg_names:
                logmsg = _("Erased: %s") %(h,)

        if len(logmsg) > 0:
            self.log.debug(logmsg, level=4)


class dlcb(urlgrabber.progress.BaseMeter):
    def __init__(self, pbar, dlpkgs, log=None, cfg=None):
        urlgrabber.progress.BaseMeter.__init__(self)
        self.pbar = pbar
        self.total = float(len(dlpkgs))
        self.current = 0
        self.last = 0
        self.log = log
        self.cfg = cfg
        self.prev_basename = None
        self.attempt = 1

    # Master GTK Interface update routine
    def _runGtkMain(self, *args):
        if self.cfg.gui_mode:
            import gtk
            while gtk.events_pending():
                gtk.main_iteration()

    def _do_start(self, now):
        txt = _("Downloading %s") % urllib2.unquote(self.url)
        if self.prev_basename == "":
            self.prev_basename = self.basename
        elif self.prev_basename == self.basename:
            self.attempt += 1
            self.current -= 1
        else:
            self.attempt = 1
            self.prev_basename = self.basename

        if self.attempt > 1:
            txt = "#%d: %s" % (self.attempt,txt)

        if self.log:
            self.log.debug(txt)
        self.pbar.set_markup("%s" %(txt,))

    def _do_end(self, amount_read, now=None):
        self.current += 1
        self.pbar.set_fraction(self.current / self.total)

    def update(self, amount_read, now=None):
        urlgrabber.progress.BaseMeter.update(self, amount_read, now)

    def _do_update(self, amount_read, now=None):
        if self.size is None:
            return

        if self.size == 0:
            return

        pct = float(amount_read) / self.size
        curval = self.pbar.get_fraction()
        newval = (pct * 1/self.total) + (self.current / self.total)
        if newval > curval + 0.001 or time.time() > self.last + 0.5:
            self.pbar.set_fraction(newval)
            self._runGtkMain()
            self.last = time.time()

class dscb:
    def __init__(self, pbar, ayum, cfg):
        self.pbar = pbar
        self.ayum = ayum
	self.cfg = cfg
        self.incr = 0.0

        # if we run pending events when we get a callback, things
        # seem more responsive which is good (tm)
        self.procReq = self.transactionPopulation = self.downloadHeader = self.start = self.unresolved = self.procConflict = self._runGtkMain

    # Master GTK Interface update routine
    def _runGtkMain(self, *args):
        if self.cfg.gui_mode:
                import gtk
                while gtk.events_pending():
                    gtk.main_iteration()

    def tscheck(self):
        num = len(self.ayum.tsInfo.getMembers())
        if num == 0: num = 1
        self.incr = (1.0 / num) * ((1.0 - self.pbar.get_fraction()) / 2)
        self._runGtkMain()

    def pkgAdded(self, *args):
        self.pbar.set_fraction(self.pbar.get_fraction() + self.incr)
        self._runGtkMain()

    def restartLoop(self):
        cur = self.pbar.get_fraction()
        new = ((1.0 - cur) / 2) + cur
        self.pbar.set_fraction(new)
        self._runGtkMain()

    def end(self):
        self.pbar.set_fraction(1.0)
        self._runGtkMain()

class PungiCallback:
    def __init__(self, pbar, pungi=None, cfg=None):
        self.pbar = pbar
        self.pungi = pungi
        self.cfg = cfg
        self.buildinstall_num = 0.0

        if self.cfg.version_from == "RHEL5":
            self.buildinstall_total = 116.0
        elif self.cfg.version_from == "F7":
            self.buildinstall_total = 500.0
        elif self.cfg.version_from == "F8":
            self.buildinstall_total = 9000.0
        elif self.cfg.version_from in [ "F9", "F10", "DEVEL" ]:
            self.buildinstall_total = 59000.0
        else:
            self.buildinstall_total = 59000.0

    # Master GTK Interface update routine
    def _runGtkMain(self, *args):
        if self.cfg.gui_mode:
            import gtk
            while gtk.events_pending():
                gtk.main_iteration()

    def parse_line(self, command, line):

        self.cfg.log.debug(_("%s: %s") % (command[0],line.rstrip()))

        if command[0] == "/usr/bin/createrepo":
            line = line.split()
            (num,total) = line[0].split('/')
            num = float(num)
            total = float(total)
            self.pbar.set_fraction(num/total)
            self._runGtkMain()

        elif command[0].endswith("buildinstall") or command[2].endswith("buildinstall"):
            self.buildinstall_num += 1.0
            if not self.buildinstall_num > self.buildinstall_total:
                if float(self.buildinstall_num / self.buildinstall_total) < 99.0:
                    self.pbar.set_fraction(self.buildinstall_num/self.buildinstall_total)
            self.pbar.set_markup(line.strip().trim())
            self._runGtkMain()

        elif command[0] == "/usr/bin/mkisofs":
            line = line.strip()
            line = line.split()
            num = line[0].replace('%','')
            num = float(num)
            total = float(100.0)
            if num < total:
                self.pbar.set_fraction(num/total)
            self._runGtkMain()

        elif command[0] == "/usr/lib/anaconda-runtime/implantisomd5":
            self.pbar.set_markup(line)
            self._runGtkMain()

        elif command[0] == "/usr/lib/anaconda-runtime/mk-rescueimage.i386":
            self.pbar.set_markup(line)
            self._runGtkMain()

        elif command[0] == "/usr/lib/anaconda-runtime/mk-rescueimage.x86_64":
            self.pbar.set_markup(line)
            self._runGtkMain()

        elif command[0] == "/usr/lib/anaconda-runtime/mk-rescueimage.ppc":
            self.pbar.set_markup(line)
            self._runGtkMain()

        else:
            print "PungiCallback.parse_line() for command: " + str(command) + " says " + str(line)
            pass

class DeltaCallback:
    def __init__(self, pbar, total):
        self.total = float(total + 10.0)
        self.current_line = float(0.0)
        self.pbar = pbar

    # Master GTK Interface update routine
    def _runGtkMain(self, *args):
        if self.cfg.gui_mode:
            import gtk
            while gtk.events_pending():
                gtk.main_iteration()

    def parse_line(self, command, line):
        self.current_line += 1.0
        if self.current_line < self.total:
            self.pbar.set_fraction(self.current_line/self.total)
        self._runGtkMain()

class CobblerCallbackHack:
    def __init__(self, pbar, cfg):
        self.total = float(100)
        self.current_line = float(0.0)
        self.pbar = pbar
        self.cfg = cfg

    # Master GTK Interface update routine
    def _runGtkMain(self, *args):
        if self.cfg.gui_mode:
            import gtk
            while gtk.events_pending():
                gtk.main_iteration()

    def write(self, text):
        """ Silence import_tree as much as we can, for now """
        self.current_line += 1.0
#        if self.current_line < self.total:
#            self.pbar.set_fraction(self.current_line/self.total)
        self._runGtkMain()

