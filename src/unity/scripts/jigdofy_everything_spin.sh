#!/bin/bash

function jigdofy() {
        jigdo-file make-template \
                --image=$1 \
                /data/os/distr/fedora/releases/${version}/Fedora/$2/os// \
                /data/os/distr/fedora/releases/${version}/Everything/$2/os// \
                --label "Fedora-$2"="/data/os/distr/fedora/releases/${version}/Fedora/$2/os" \
                --uri "Fedora-$2"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${version}/Fedora/$2/os/" \
                --label "Everything-$2"="/data/os/distr/fedora/releases/${version}/Everything/$2/os" \
                --uri "Everything-$2"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${version}/Everything/$2/os/" \
                --jigdo=$jigdofile \
                --template=/var/www/jigdo/templates/Fedora-${version}-Everything/`basename $1`.template \
                --force --merge=$jigdofile \
                --cache=${jigdofile}.cache
}

export archs=""
export JIGDOFY_SOURCE_ISO=0

while [ $# -gt 0 ]; do
    case $1 in
        --version)
            export version=$2
            shift; shift
            ;;
        --arch)
            export archs="${archs} $2"
            shift; shift
            ;;
    esac
done

if [ -z "$version" ]; then
    echo Usage: $0 --version [version] --arch [arch1] [[--arch [arch2]] [--arch [arch3]]] 
    exit 1
fi

export jigdofile=/var/www/jigdo/templates/Fedora-${version}-Everything/Fedora-${version}-Everything.jigdo
export product_dir=/data/revisor/

[ ! -d /var/www/jigdo/data/Fedora-${version}-Everything ] && mkdir -p /var/www/jigdo/data/Fedora-${version}-Everything
[ ! -d /var/www/jigdo/templates/Fedora-${version}-Everything ] && mkdir -p /var/www/jigdo/templates/Fedora-${version}-Everything

[ ! -f ${jigdofile} ] && touch ${jigdofile}

for arch in ${archs}; do
	for iso in `ls ${product_dir}/f${version}-$arch-everything/iso/*.iso`; do
		jigdofy $iso $arch
	done
	cat ${product_dir}/f${version}-$arch-everything/iso/SHA1SUM >> /var/www/jigdo/templates/Fedora-${version}-Everything/Fedora-${version}-Everything.SHA1SUM
done

## Grab sha1sums
##cat /srv/revisor/*/iso/SHA1SUM >> /var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.SHA1SUM

sed -i -e "s/\+/\%2b/g" $jigdofile
sed -i -e "s/Template=F/Template=http:\/\/jigdo.fedoraunity.org\/templates\/Fedora-${version}-Everything\/F/g" $jigdofile

