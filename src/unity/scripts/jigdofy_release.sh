#!/bin/bash

export VERSION=8
export BASEDIR=/data/os/distr/fedora/
export JIGDOFY_SOURCE_ISO=0
export JIGDO_MERGED=0
export CLEAR_CACHE=0
export archs=""
export tree=Fedora
export jigdo_path=jigdo

function jigdofy() {
    if [ ${JIGDO_MERGED} -eq 1 ]; then
        jigdo_file=${product_dir}/$2/${jigdo_path}/Fedora-${VERSION}.jigdo
        jigdo_opts="--merge"
    else
        jigdo_file=${product_dir}/$2/${jigdo_path}/`basename $1`.jigdo
    fi

    [ ! -d "`dirname ${jigdo_file}`" ] && mkdir -p `dirname ${jigdo_file}`
    [ ! -f "${jigdo_file}" ] && touch ${jigdo_file}

    jigdo-file make-template --image=$1 \
        ${BASEDIR}/releases/${VERSION}/Fedora/$2/os// \
        --jigdo=${jigdo_file} ${jigdo_opts} \
        --template=${product_dir}/$2/${jigdo_path}/`basename $1`.template --force \
        --cache=/var/tmp/jigdo-$2.cache \
        --label "Base-$2"="${BASEDIR}/releases/${VERSION}/Fedora/$2/os" \
        --uri "Base-$2"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${VERSION}/Fedora/$2/os/"
    sed -i -e "s|\+|\%2b|g" ${jigdo_file}
    sed -i -e "s|Template=|Template=http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${VERSION}/Fedora/$2/os/|g" ${jigdo_file}
}

while [ $# -gt 0 ]; do
    case $1 in
        --basedir)
            export BASEDIR=$2
            shift; shift
            ;;
        --version)
            export VERSION=$2
            shift; shift
            ;;
	--source)
	    export JIGDOFY_SOURCE_ISO=1
	    shift
            ;;
        --tree)
            export tree=$2
            shift; shift
            ;;
        --jigdo-path)
            export jigdo_path=$2
            shift; shift
            ;;
#        --product-dir)
#            export product_dir=$2
#            shift; shift
#            ;;
#        --jigdofile)
#            export jigdofile=$2
#            shift; shift
#            ;;
        --no-cache)
            export CLEAR_CACHE=1
            shift
            ;;
        --merge)
            export JIGDO_MERGED=1
            shift
            ;;
        --arch)
            export archs="${archs} $2"
            shift; shift
            ;;
        --usage|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo " --basedir    Top directory of the mirrored tree. In this directory"
            echo "              you usually find releases/ and updates/"
            echo " --version    Version to jigdofy (8 by default)"
            echo " --source     Also Jigdofy the Source ISO"
            echo " --arch       Architecture to Jigdofy. Specify multiple times does"
            echo "              them in batch."
            echo " --tree       Tree to use. Defaults to Fedora/. (Specify Everything"
            echo "              to exclude the repoview/ directory which has all"
            echo "              way too many small files"
            echo " --jigdo-path Directory name to create next to the iso/ directories"
            echo " --merge      Incompatible with Jigdo GUI. Results in a single .jigdo"
            echo " --no-cache   Destroy the cache of scanned files before Jigdofying"
            echo ""
            exit
    esac
done

export product_dir=${BASEDIR}/releases/${VERSION}/Fedora/

# Makes basedir work
path=`dirname ${BASEDIR}`
dir=`basename ${BASEDIR}`
export BASEDIR=$path/$dir

for arch in ${archs}; do
    [ -f "/var/tmp/jigdo-${arch}.cache" -a "${CLEAR_CACHE}" == "1" ] && rm -rf "/var/tmp/jigdo-$arch.cache"
    for iso in `ls ${product_dir}/${arch}/iso/*.iso`; do
        jigdofy $iso $arch
    done
done

if [ "${JIGDOFY_SOURCE_ISO}" == "1" ]; then
# Jigdofy source image
    for iso in `ls ${product_dir}/${arch}/iso/*.iso`; do
        if [ ${JIGDO_MERGED} == 1 ];
            jigdo_file=${product_dir}/source/${jigdo_path}/Fedora-${VERSION}.jigdo
            jigdo_opts="--merge"
        else
            jigdo_file=${product_dir}/source/${jigdo_path}/${jigdo_path}/`basename $iso`.jigdo
        fi

        [ ! -d "`dirname ${jigdo_file}`" ] && mkdir -p `dirname ${jigdo_file}`
        [ ! -f "${jigdo_file}" ] && touch ${jigdo_file}

        jigdo-file make-template --image=$iso \
            ${BASEDIR}/releases/${VERSION}/Fedora/source/SRPMS// \
            --jigdo=${jigdo_file} \
            --template=${product_dir}/source/${jigdo_path}/`basename $iso`.template --force \
            --cache=/var/tmp/jigdo-source.cache \
            --label "Base-source"="${BASEDIR}/releases/${VERSION}/Fedora/source/SRPMS" \
            --uri "Base-source"="http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${VERSION}/Fedora/source/SRPMS/"
        sed -i -e "s|\+|\%2b|g" ${jigdo_file}
        sed -i -e "s|Template=|Template=http://mirrors.fedoraproject.org/mirrorlist?redirect=1&path=pub/fedora/linux/releases/${VERSION}/Fedora/source/SRPMS/|g" ${jigdo_file}
    done
fi
