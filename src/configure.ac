AC_INIT([revisor], 2.2)
AC_SUBST([RELEASE], 1)

AC_CONFIG_SRCDIR(revisor/__init__.py.in)

ALL_LINGUAS="bn_IN bn ca cs da de el es fi fr gl gu hi hr hu is it ja ko ml ms nb nl or pa pl pt pt_BR ru sk sl sr@latin sr sv ta tr uk zh_CN zh_TW"

AM_INIT_AUTOMAKE
AM_MAINTAINER_MODE
AM_PATH_PYTHON

dnl prevent to copy po/Makefile.in.in
GETTEXT_PACKAGE=revisor
AC_SUBST(GETTEXT_PACKAGE)
AM_GLIB_GNU_GETTEXT
AC_PROG_INTLTOOL
AC_PROG_LN_S

AC_SUBST(DATESTAMP,`date +"%a %b %d %Y"`)

AM_PATH_PYTHON

AC_CONFIG_FILES([
conf/Makefile
doc/Makefile
po/Makefile.in
scripts/Makefile
Makefile
revisor.spec
revisor/Makefile
revisor/__init__.py
revisor/modcobbler/Makefile
revisor/modcomposer/Makefile
revisor/moddelta/Makefile
revisor/modgui/Makefile
revisor/modgui/glade/base_screen.glade
revisor/modhub/Makefile
revisor/modisolinux/Makefile
revisor/modjigdo/Makefile
revisor/modmock/Makefile
revisor/modrebrand/Makefile
revisor/modreuseinstaller/Makefile
revisor/modserver/Makefile
revisor/modvirt/Makefile
revisor/modwui/Makefile
unity/Makefile
])

AC_OUTPUT
