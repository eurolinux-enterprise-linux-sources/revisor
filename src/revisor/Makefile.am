PYTHON_FILES = \
    base.py                       \
    cfg.py                        \
    cli.py                        \
    constants.py                  \
    errors.py                     \
    image.py                      \
    __init__.py                   \
    kickstart.py                  \
    logger.py                     \
    misc.py                       \
    pkgorder.py                   \
    plugins.py                    \
    translate.py                    \
    progress.py                   \
    pungi.py                      \
    splittree.py

EXTRA_DIST = \
    $(PYTHON_FILES) \
    __init__.py.in

pydir = $(pythondir)/revisor
py_PYTHON = $(PYTHON_FILES)

SUBDIRS = \
    modcobbler \
    modcomposer \
    moddelta \
    modgui \
    modhub \
    modisolinux \
    modjigdo \
    modmock \
    modrebrand \
    modreuseinstaller \
    modserver \
    modvirt \
    modwui \
    modhub
