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
    for media in $MEDIATYPES; do
        mkdir -p $TORRENTDIR/Fedora-$VERSION-Everything-${arch}-${media}/
        ln -f $REVISORDIR/f${VERSION}-${arch}-everything/iso/*${media}*.iso $TORRENTDIR/Fedora-$VERSION-Everything-${arch}-${media}/
        [ "${media}" == "DVD" ] && rm -f $TORRENTDIR/Fedora-${VERSION}-Everything-${arch}-DVD/*DVD-DL*
        ln -f $REVISORDIR/f${VERSION}-${arch}-everything/iso/SHA1SUM $TORRENTDIR/Fedora-$VERSION-Everything-${arch}-${media}/SHA1SUM
        maketorrent-console --piece_size_pow2 19 \
            --tracker_name http://spinner.fedoraunity.org:6969/announce \
            --comment "Fedora $VERSION Everything ${arch} ${media}" \
            --target $TORRENTDIR/Fedora-$VERSION-Everything-${arch}-${media}.torrent \
            http://spinner.fedoraunity.org:6969/announce \
            $TORRENTDIR/Fedora-$VERSION-Everything-${arch}-${media}/;
    done;
done
