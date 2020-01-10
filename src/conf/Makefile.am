revisorconfdir = $(sysconfdir)/revisor/conf.d/
revisorconf_DATA = \
    conf.d/revisor-f12-i386.conf   \
    conf.d/revisor-f12-ppc64.conf  \
    conf.d/revisor-f12-ppc.conf    \
    conf.d/revisor-f12-x86_64.conf \
    conf.d/revisor-f13-i386.conf   \
    conf.d/revisor-f13-x86_64.conf \
    conf.d/revisor-rawhide-i386.conf   \
    conf.d/revisor-rawhide-ppc64.conf  \
    conf.d/revisor-rawhide-ppc.conf    \
    conf.d/revisor-rawhide-x86_64.conf \
    conf.d/fedora-12-gold.cfg

etcconfdir = $(sysconfdir)/revisor/
etcconf_DATA = revisor.conf

desktopdatadir = $(datadir)/applications/
desktopdata_in_files = revisor.desktop.in
desktopdata_DATA = $(desktopdata_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

sharedatadir = $(pkgdatadir)/
sharedata_DATA = \
    comps-cleanup.xsl

compsdatadir = $(pkgdatadir)/comps/
compsdata_DATA = \
	comps-f12.xml \
	comps-f13.xml

REVISORCONFIG = \
	revisor.pam                        \
	revisor.console                    \
	revisor.conf                       \
	revisor.desktop.in                 \
	$(revisorconf_DATA)                \
	$(etcconf_DATA)

EXTRA_DIST = \
    conf.d/fedora-7-gold.cfg           \
    conf.d/fedora-8-gold.cfg           \
    conf.d/fedora-9-gold.cfg \
    conf.d/fedora-10-gold.cfg \
    conf.d/fedora-11-gold.cfg \
    conf.d/revisor-c5-i386.conf        \
    conf.d/revisor-c5-ppc.conf         \
    conf.d/revisor-c5-x86_64.conf      \
    conf.d/revisor-fc6-i386.conf       \
    conf.d/revisor-fc6-ppc.conf        \
    conf.d/revisor-fc6-x86_64.conf     \
    conf.d/revisor-f7-i386.conf        \
    conf.d/revisor-f7-ppc.conf         \
    conf.d/revisor-f7-x86_64.conf      \
    conf.d/revisor-f8-i386.conf        \
    conf.d/revisor-f8-ppc64.conf       \
    conf.d/revisor-f8-ppc.conf         \
    conf.d/revisor-f8-x86_64.conf      \
    conf.d/revisor-f9-i386.conf        \
    conf.d/revisor-f9-ppc64.conf       \
    conf.d/revisor-f9-ppc.conf         \
    conf.d/revisor-f9-x86_64.conf      \
    conf.d/revisor-f10-i386.conf        \
    conf.d/revisor-f10-ppc64.conf       \
    conf.d/revisor-f10-ppc.conf         \
    conf.d/revisor-f10-x86_64.conf      \
    conf.d/revisor-f11-i386.conf   \
    conf.d/revisor-f11-ppc64.conf  \
    conf.d/revisor-f11-ppc.conf    \
    conf.d/revisor-f11-x86_64.conf \
	comps-fc6.xml                      \
	comps-fe6.xml                      \
    comps-f7.xml                       \
    comps-f8.xml                       \
	comps-f9.xml \
	comps-f10.xml \
	comps-f11.xml \
	comps-c5.xml                       \
	comps-el5.xml                      \
	$(REVISORCONFIG) \
	$(sharedata_DATA) \
	$(compsdata_DATA)

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)/pam.d
	$(mkinstalldirs) $(DESTDIR)$(sysconfdir)/security/console.apps/
	$(INSTALL) -m 644 revisor.pam $(DESTDIR)$(sysconfdir)/pam.d/revisor
	$(INSTALL) -m 644 revisor.console $(DESTDIR)$(sysconfdir)/security/console.apps/revisor

uninstall-local:
	rm -f $(DESTDIR)$(sysconfdir)/pam.d/revisor
	rm -f $(DESTDIR)$(sysconfdir)/security/console.apps/revisor
	rm -f $(DESTDIR)$(datadir)/applications/revisor.desktop

clean:
	rm -f *~
