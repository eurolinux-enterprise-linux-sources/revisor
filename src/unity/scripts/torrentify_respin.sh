#!/bin/bash

TORRENTDIR=/data/bittorrent/
REVISORDIR=/data/revisor/

while [ $# -gt 0 ]; do
    case $1 in
        --datestamp)
            DATESTAMP=$2
            shift; shift
        ;;
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
        mkdir -p $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-${arch}-${media}/
        ln $REVISORDIR/$DATESTAMP/f${VERSION}-${arch}-respin/iso/*${media}*.iso $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-${arch}-${media}/
        ln $REVISORDIR/$DATESTAMP/f${VERSION}-${arch}-respin/iso/SHA1SUM $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-${arch}-${media}/SHA1SUM
        maketorrent-console --piece_size_pow2 19 \
            --tracker_name http://spinner.fedoraunity.org:6969/announce \
            --comment "Fedora Unity $DATESTAMP $VERSION ${arch} ${media}" \
            --target $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-${arch}-${media}.torrent \
            http://spinner.fedoraunity.org:6969/announce \
            $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-${arch}-${media}/;
    done;
done

mkdir -p $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-Source-DVD/
ln $REVISORDIR/$DATESTAMP/f${VERSION}-source-respin/iso/*.iso $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-Source-DVD/
ln $REVISORDIR/$DATESTAMP/f${VERSION}-source-respin/iso/SHA1SUM $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-Source-DVD/SHA1SUM
maketorrent-console --piece_size_pow2 19 \
    --tracker_name http://spinner.fedoraunity.org:6969/announce \
    --comment "Fedora Unity $DATESTAMP $VERSION Source ${media}" \
    --target $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-Source-${media}.torrent \
    http://spinner.fedoraunity.org:6969/announce \
    $TORRENTDIR/Fedora-Unity-$DATESTAMP-$VERSION-Source-${media}/;

chown -R torrent:torrent $TORRENTDIR
