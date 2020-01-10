#!/bin/bash

export ARCHS="i386 x86_64"
export BRANCHES="7 8"

export BASE_PATH="/media/mntrepo/"
export SRPMS_SOURCES="${BASE_PATH}SRPMS/"
export SRPMS_TARGETS="${BASE_PATH}\$branch/SRPMS/"
export RPMS_LOCATION="${BASE_PATH}\$branch/\$arch/"
export LOGS_LOCATION="${BASE_PATH}\$branch/\$arch/logs/"

function build_rpm() {
    SRPM=$1
    branch=$2

    for arch in $ARCHS; do
        [ ! -d $(eval echo $RPMS_LOCATION) ] && mkdir -p $(eval echo $RPMS_LOCATION)

        # Get some details
        RPM_NAME=`rpmquery --queryformat="%{NAME}" -p $SRPM`
        RPM_VERSION=`rpmquery --queryformat="%{VERSION}" -p $SRPM`
        RPM_RELEASE=`rpmquery --queryformat="%{RELEASE}" -p $SRPM`
        RPM_NVR="${RPM_NAME}-${RPM_VERSION}-${RPM_RELEASE}"

        mock_succeed=0

        if [ "`uname -i`" != "$arch" ]; then
            setarch $arch mock -r fedora-$branch-$arch rebuild $SRPM && mock_succeed=1
        else
            mock -r fedora-$branch-$arch rebuild $SRPM && mock_succeed=1
        fi

        # If mock returns no errors...
        if [ $mock_succeed -eq 1 ]; then
            # RPMLint the built rpms, getting the output into a log file
            for file in `ls /var/lib/mock/fedora-$branch-$arch/result/*.rpm`; do
                rpmlint -i $file > `basename $file`.rpmlint.log 2>&1
            done

            # And move the (S)RPMs into their correct locations
            [ ! -d $(eval echo $SRPMS_TARGETS) ] && mkdir -p $(eval echo $SRPMS_TARGETS)
            mv -f /var/lib/mock/fedora-$branch-$arch/result/*.src.rpm $(eval echo $SRPMS_TARGETS)
            [ ! -d $(eval echo $RPMS_LOCATION) ] && mkdir -p $(eval echo $RPMS_LOCATION)
            mv -f /var/lib/mock/fedora-$branch-$arch/result/*.rpm $(eval echo $RPMS_LOCATION)

            # Also move the RPMLint log files
            [ ! -d $(eval echo $SRPMS_TARGETS)logs ] && mkdir -p $(eval echo $SRPMS_TARGETS)logs
            mv -f *.src.rpm.rpmlint.log $(eval echo $SRPMS_TARGETS)logs
            for log in `ls *.rpmlint.log`; do
                mv -f $log $(eval echo $LOGS_LOCATION)
            done
        fi
        [ ! -d $(eval echo $LOGS_LOCATION) ] && mkdir -p $(eval echo $LOGS_LOCATION)
        for log in `ls /var/lib/mock/fedora-$branch-$arch/result/*.log`; do
            mv -f $log $(eval echo $LOGS_LOCATION)${RPM_NVR}-`basename $log`
        done
    done
}
if [ -z "$1" ]; then
    echo "You know you should specify a name for a source RPM don't you?"
    exit 1
fi

SRPM_MATCH=$1

if [ ! -z "`ls ${SRPMS_SOURCES}${SRPM_MATCH}*`" ]; then
    echo OK, found the following SRPMS to build:
    for SRPM in `ls ${SRPMS_SOURCES}${SRPM_MATCH}*`; do
        [ ! -z "`echo ${SRPM} | grep fc7.src.rpm`" ] && target_branch=7
        [ ! -z "`echo ${SRPM} | grep fc8.src.rpm`" ] && target_branch=8
        [ ! -z "`echo ${SRPM} | grep fc9.src.rpm`" ] && target_branch=devel
        [ -z "$target_branch" ] && target_branch=devel

        # Just be verbose this time
        echo "-> ${SRPM} (Going to build for fc$target_branch)"
    done
fi

echo -n "Continue building? [Y/n] "
read -n 1 INPUT
echo ""

if [ "$INPUT" == "n" ]; then
    exit 0
fi

for SRPM in `ls ${SRPMS_SOURCES}${SRPM_MATCH}*`; do
    [ ! -z "`echo ${SRPM} | grep fc7.src.rpm`" ] && target_branch=7
    [ ! -z "`echo ${SRPM} | grep fc8.src.rpm`" ] && target_branch=8
    [ ! -z "`echo ${SRPM} | grep fc9.src.rpm`" ] && target_branch=devel
    [ -z "$target_branch" ] && target_branch=devel
    build_rpm $SRPM $target_branch
done

for arch in $ARCHS SRPMS; do
    for branch in $BRANCHES; do
        cd ${BASE_PATH}$branch/$arch/
        createrepo .
    done
done
