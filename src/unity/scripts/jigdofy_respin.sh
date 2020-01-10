#!/bin/bash

function jigdofy() {
        jigdo-file make-template \
                --image=$1 \
                /data/os/distr/fedora/releases/${version}/Everything/$2/os// \
                /data/os/archive/fedora/updates/${version}/$2// \
                --label "Base-$2"="/data/os/distr/fedora/releases/${version}/Everything/$2/os" \
		--uri "Base-$2"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${version}/Everything/$2/os/" \
                --label "Updates-$2"="/data/os/archive/fedora/updates/${version}/$2" \
		--uri "Updates-$2"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/updates/${version}/$2/" \
                --jigdo=$jigdofile \
                --template=/var/www/jigdo/templates/${datestamp}/`basename $1`.template \
                --force --merge=$jigdofile \
                --cache=${jigdofile}.cache
}

export archs=""
export JIGDOFY_SOURCE_ISO=0

while [ $# -gt 0 ]; do
    case $1 in
        --datestamp)
            export datestamp=$2
            shift; shift
            ;;
        --version)
            export version=$2
            shift; shift
            ;;
        --source)
	    export JIGDOFY_SOURCE_ISO=1
	    shift
            ;;
#        --product-dir)
#            export product_dir=$2
#            shift; shift
#            ;;
#        --jigdofile)
#            export jigdofile=$2
#            shift; shift
#            ;;
        --arch)
            export archs="${archs} $2"
            shift; shift
            ;;
    esac
done

if [ -z "$datestamp" -o -z "$version" ]; then
    echo Usage: $0 --datestamp [datestamp] --version [version] --arch [arch1] [[--arch [arch2]] [--arch [arch3]]] [--source]
    exit 1
fi

export jigdofile=/var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.jigdo
export product_dir=/data/revisor/${datestamp}/

[ ! -d /var/www/jigdo/data/${datestamp} ] && mkdir -p /var/www/jigdo/data/${datestamp}
[ ! -d /var/www/jigdo/templates/${datestamp} ] && mkdir -p /var/www/jigdo/templates/${datestamp}

[ ! -f ${jigdofile} ] && touch ${jigdofile}

for arch in ${archs}; do
	for iso in `ls ${product_dir}/f${version}-$arch-respin/iso/*.iso`; do
		jigdofy $iso $arch
	done
	cat ${product_dir}/f${version}-$arch-respin/iso/SHA1SUM >> /var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.SHA1SUM
done

if [ "${JIGDOFY_SOURCE_ISO}" == "1" ]; then
# Jigdofy source image
	jigdo-file make-template \
		--image=${product_dir}/f${version}-source-respin/iso/Fedora-Unity-${datestamp}-${version}-source-DVD.iso \
		/data/os/distr/fedora/releases/${version}/Everything/source// \
		/data/os/archive/fedora/updates/${version}/SRPMS// \
		--label "Base-Source"="/data/os/distr/fedora/releases/${version}/Everything/source" \
		--uri "Base-Source"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${version}/Everything/source/SRPMS/" \
		--label "Updates-Source"="/data/os/archive/fedora/updates/${version}/SRPMS" \
		--uri "Updates-Source"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/updates/${version}/SRPMS/" \
		--jigdo=${jigdofile} \
		--template=/var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}-source-DVD.iso.template \
		--force --merge=${jigdofile} \
		--cache=${jigdofile}.cache

	cat ${product_dir}/f${version}-source-respin/iso/SHA1SUM >> /var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.SHA1SUM
fi
## Grab sha1sums
##cat /srv/revisor/*/iso/SHA1SUM >> /var/www/jigdo/templates/${datestamp}/Fedora-Unity-${datestamp}-${version}.SHA1SUM

sed -i -e "s/\+/\%2b/g" $jigdofile
sed -i -e "s/Template=F/Template=http:\/\/jigdo.fedoraunity.org\/templates\/${datestamp}\/F/g" $jigdofile

