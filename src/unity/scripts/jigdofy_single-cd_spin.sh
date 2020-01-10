#!/bin/bash

function jigdofy() {
        jigdo-file make-template \
                --image=$1 \
                /data/os/distr/fedora/releases/${version}/Fedora/$2/os// \
                /data/os/distr/fedora/releases/${version}/Everything/$2/os// \
                --label "Fedora-$2"="/data/os/distr/fedora/releases/${version}/Fedora/$2/os" \
                --uri "Fedora-$2"="http://download.fedoraproject.org/pub/fedora/linux/releases/${version}/Fedora/$2/os/" \
                --label "Everything-$2"="/data/os/distr/fedora/releases/${version}/Everything/$2/os" \
                --uri "Everything-$2"="http://download.fedoraproject.org/pub/fedora/linux/releases/${version}/Everything/$2/os/" \
                --jigdo=$jigdofile \
                --template=/var/www/jigdo/templates/Fedora-${version}-Single-CD/`basename $1`.template \
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

export jigdofile=/var/www/jigdo/templates/Fedora-${version}-Single-CD/Fedora-${version}-Single-CD.jigdo
export product_dir=/data/revisor/

[ ! -d /var/www/jigdo/data/Fedora-${version}-Single-CD ] && mkdir -p /var/www/jigdo/data/Fedora-${version}-Single-CD
[ ! -d /var/www/jigdo/templates/Fedora-${version}-Single-CD ] && mkdir -p /var/www/jigdo/templates/Fedora-${version}-Single-CD

[ ! -f ${jigdofile} ] && touch ${jigdofile}

for arch in ${archs}; do
	for iso in `ls ${product_dir}/f${version}-$arch-single-cd/iso/*.iso`; do
		jigdofy $iso $arch
	done
	cat ${product_dir}/f${version}-$arch-single-cd/iso/SHA1SUM >> /var/www/jigdo/templates/Fedora-${version}-Single-CD/Fedora-${version}-Single-CD.SHA1SUM
done

## Grab sha1sums
##cat /srv/revisor/*/iso/SHA1SUM >> /var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.SHA1SUM

sed -i -e "s/\+/\%2b/g" $jigdofile
sed -i -e "s/Template=F/Template=http:\/\/jigdo.fedoraunity.org\/templates\/Fedora-${version}-Single-CD\/F/g" $jigdofile

