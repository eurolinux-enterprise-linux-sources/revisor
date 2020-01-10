#!/bin/bash

revisor_deps="comps-extras createrepo rhpl pykickstart livecd-tools
        anaconda-runtime squashfs-tools busybox-anaconda notify-python usermode
        pam python automake intltool gettext desktop-file-utils glib2-devel gcc
        cobbler koan deltarpm pygtk pygtk2-libglade gnome-python2-gconf
        system-config-kickstart jigdo livecd-tools python-virtinst git sudo
        spin-kickstarts mock"

function usage() {
    echo "$0 [--version v1 [--version v2]] [--arch a1 [--arch a2]]"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

while [ $# -gt 0 ]; do
    case $1 in
        --version)
            versions="$versions $2"
            shift; shift
        ;;
        --arch)
            arches="$arches $2"
            shift; shift
        ;;
        *)
            usage
        ;;
    esac
done

for version in $versions; do
    for arch in $arches; do
        mock -r fedora-$version-$arch init && \
        mock -r fedora-$version-$arch install $revisor_deps && \
        echo -en "git clone git://git.fedorahosted.org/revisor\n" | mock -r fedora-$version-$arch shell
        echo -en "cd /revisor; ./switchhere --yes\n" | mock -r fedora-$version-$arch shell
        echo -en "cd /revisor; autoreconf && ./configure\n" | mock -r fedora-$version-$arch shell
        echo -en "find /var/lib/rpm/ -name '__db.*' -delete\n" | mock -r fedora-$version-$arch shell
        echo -en "cd /revisor; ./revisor.py --cli --config /etc/revisor-unity/f$version-install-respin.conf --model f$version-$arch-respin --debug 9\n" | mock -r fedora-$version-$arch shell;
    done
done