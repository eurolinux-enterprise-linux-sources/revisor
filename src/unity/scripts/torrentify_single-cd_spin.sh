#!/bin/bash

TORRENTDIR=/data/bittorrent/
REVISORDIR=/data/revisor/

while [ $# -gt 0 ]; do
    case $1 in
        --version)
            VERSION=$2
            shift; shift
        ;;
        --arch)
            ARCHES="$ARCHES $2"
            shift; shift
        ;;
        --source)
            SOURCE=1
            shift
        ;;
        --media)
            MEDIATYPES="$MEDIATYPES $2"
            shift; shift
        ;;
    esac
done

for arch in $ARCHES; do
    mkdir -p $TORRENTDIR/Fedora-$VERSION-Single-CD-${arch}/
    ln $REVISORDIR/f${VERSION}-${arch}-single-cd/iso/* $TORRENTDIR/Fedora-$VERSION-Single-CD-${arch}/
    maketorrent-console --piece_size_pow2 19 \
            --tracker_name http://spinner.fedoraunity.org:6969/announce \
            --comment "Fedora $VERSION Single CD ${arch}" \
            --target $TORRENTDIR/Fedora-$VERSION-Single-CD-${arch}.torrent \
            http://spinner.fedoraunity.org:6969/announce \
            $TORRENTDIR/Fedora-$VERSION-Single-CD-${arch}/;
done;
