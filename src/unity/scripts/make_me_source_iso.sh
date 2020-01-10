#!/bin/bash

DATA=/data/revisor/
DIR1=$1
DIR2=$2
DIR3=$3

usage() {
    echo Usage:" $0 --datestamp <date> --version <version> --arch <arch> [--arch <arch> [--arch <arch>]]"
    exit 1
}

while [ $# -gt 0 ]; do
    case $1 in
        --datestamp)
            DATA=$DATA/$2
            shift; shift
        ;;
        --arch)
            ARCHES="$ARCHES $2"
            shift; shift
        ;;
        --version)
            VERSION=$2
            shift; shift
        ;;
        *)
            usage
        ;;
    esac
done

[ -z "${VERSION}" ] && usage

if [ ! -d "$DATA" ]; then
    echo No such file or directory: $DATA/
    usage
fi

for arch in $ARCHES; do
    [ ! -d "$DATA/f${VERSION}-$arch-respin/" ] && usage
done

DIR_SOURCE="f${VERSION}-source-respin"

[ -d "$DATA/$DIR_SOURCE" ] && rm -rf "$DATA/$DIR_SOURCE"
mkdir -p $DATA/$DIR_SOURCE/os/source/SRPMS
mkdir -p $DATA/$DIR_SOURCE/iso

for arch in $ARCHES; do
    ln -v $DATA/f${VERSION}-$arch-respin/os/source/SRPMS/* $DATA/$DIR_SOURCE/os/source/SRPMS/. 2>/dev/null
done

iso=`find $DATA/*-respin/iso/ -name "*DVD*.iso" | head -n 1`
basename=`echo $iso | sed -e 's/i386/source/g' | sed -e 's/x86_64/source/g'`

echo Found iso $iso
echo Using basename $basename

cd $DATA/$DIR_SOURCE/os/source/

createrepo -v SRPMS

cd $DATA

mkisofs -v -U -J -R -T -f -o $basename $DIR_SOURCE/os/source/

implantisomd5 $basename || /usr/lib/anaconda-runtime/implantisomd5 $basename

cd $DATA/$DIR_SOURCE/iso/

sha1sum *.iso > SHA1SUM
