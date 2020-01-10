PYTHON_FILES = \
    build_media.py                \
    build_type.py                 \
    configuration.py              \
    finished_screen.py            \
    __init__.py                   \
    lm_auth.py                    \
    lm_basic.py                   \
    lm_bootloader.py              \
    lm_display.py                 \
    lm_install_callback.py        \
    lm_network.py                 \
    lm_security.py                \
    lm_usercustomize.py           \
    load_kickstart.py             \
    package_selection.py          \
    ready_screen.py               \
    select_media.py               \
    welcome_screen.py

GLADE_FILES = \
	glade/base_buttons.glade                       \
	glade/base_screen.glade                        \
	glade/base_statusbar.glade                     \
	glade/build_media.glade                        \
	glade/build_type.glade                         \
	glade/dialog_alert.glade                       \
	glade/dialog_filechooser.glade                 \
	glade/finished_buttons.glade                   \
	glade/finished_screen.glade                    \
	glade/lm_auth.glade                            \
	glade/lm_basic.glade                           \
	glade/lm_bootloader.glade                      \
	glade/lm_display.glade                         \
	glade/lm_network.glade                         \
	glade/lm_security.glade                        \
	glade/lm_usercustomize.glade                   \
	glade/load_kickstart.glade                     \
	glade/package_selection.glade                  \
	glade/progress.glade                           \
	glade/ready_screen.glade                       \
	glade/revisor_configuration.glade              \
	glade/select_media.glade                       \
	glade/select_media_advanced.glade              \
	glade/select_media_installation.glade          \
	glade/select_media_live.glade                  \
	glade/select_media_utility.glade               \
	glade/select_media_virtualization.glade        \
	glade/welcome_buttons.glade                    \
	glade/welcome_screen.glade

PIXMAPS = \
	glade/pixmaps/header_kickstart.png \
	glade/pixmaps/header_main.png      \
	glade/pixmaps/header_packages.png  \
	glade/pixmaps/header_yum.png       \
	glade/pixmaps/revisor_finished.png \
	glade/pixmaps/revisor_icon.png     \
	glade/pixmaps/revisor.png          \
	glade/pixmaps/select_media.png     \
	glade/pixmaps/welcome_splash.png

EXTRA_DIST = \
    $(PYTHON_FILES) \
    $(GLADE_FILES) \
    $(PIXMAPS)

pydir = $(pythondir)/revisor/modgui
py_PYTHON = $(PYTHON_FILES)

gladedir = $(pkgdatadir)/ui
glade_DATA = $(GLADE_FILES)

pixmapdir = $(pkgdatadir)/pixmaps
pixmap_DATA = $(PIXMAPS)

install-data-local:
	$(mkinstalldirs) $(DESTDIR)$(datadir)/pixmaps
	$(INSTALL) -m 644 glade/pixmaps/revisor.png $(DESTDIR)$(datadir)/pixmaps/revisor.png

uninstall-local:
	rm -f $(DESTDIR)$(pkgdatadir)/pixmaps/*.png
	rm -f $(DESTDIR)$(pkgdatadir)/ui/*
	rm -f $(DESTDIR)$(datadir)/pixmaps/revisor.png
