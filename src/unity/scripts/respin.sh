#!/bin/bash

#
# Copyright 2008-2009 Jeroen van Meeuwen <kanarip@fedoraunity.org>
#
# This is a script to automate respins for both installation and live media.
#
# The script makes the following assumptions:
#
# - you have sudo configured for the user you are executing the script with, for
#   at least the following commands:
#
#   1) sudo make install (in ${TMPDIR:-/tmp}/spin-kickstarts)
#   2) sudo ./revisor.py (if running from source)
#   3) sudo revisor (if running from installed RPMs)
#   4) sudo mkdir -p
#   5) sudo mv
#
# - you have all the required packages installed (see $revisor_deps)
# - you have enough disk space (haha, no estimate here)
#
# And, last but not least, you have configured the following in
# /etc/mock/site-defaults.cfg:
#
# # bind mount plugin is enabled by default but has no configured directories to mount
# # config_opts['plugin_conf']['bind_mount_enable'] = True
# config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('/selinux/', '/selinux/' ))
# config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('${REVISORDIR}/', '${REVISORDIR}/' ))
# # (optional, saves you a lot of downloads if you run the default revisor setup and are respinning
# # in batch)
# config_opts['plugin_conf']['bind_mount_opts']['dirs'].append(('/var/tmp/revisor-yumcache/', '/var/tmp/revisor-yumcache/' ))
#
##
## Wishlist
##
# - diff different versions of live media (done)
# - enable rawhide composes (done)
# - jigdofying and torrentifying installation media (torrentifying done)
# - torrentifying live media (done)
# - gold_vs_respin.shs
#

# Who to notify on failure, or success, and where to send the message from.
NOTIFICATION_FAILURE="test-team@lists.fedoraunity.org"
NOTIFICATION_SUCCESS="test-team@lists.fedoraunity.org"
NOTIFICATION_FROMADD="kanarip@kanarip.com"

GIT_SPINKICKSTARTS=git://git.fedorahosted.org/spin-kickstarts.git
GIT_REVISOR=git://git.fedorahosted.org/revisor

# The temp directory to use. Defaults to /tmp
#TMPDIR=/tmp

# Where do you store your torrents?
export TORRENTDIR=/data/bittorrent/

# What is the base directory for all revisor products?
export REVISORDIR=/data/revisor/

# The start date of this run
export STARTDATE=`date +%Y%m%d`

# See if we have a proxy. If so, use it.
[ `host proxy >/dev/null 2>&1; echo $?` -eq 0 -a -z "${HTTP_PROXY}" ] && export HTTP_PROXY=proxy:3128

function usage() {
    echo "$0 [options]"
    echo ""
    echo "--version <version>    - The version of the distribution to respin. Can"
    echo "                         be specified multiple times."
    echo "--arch <arch>          - The architectures to respin. Can also be specified"
    echo "                         multiple times."
    echo ""
    echo "--cleanup              - Pass Revisor how to clean up after itself (default: 1)"
    echo "                         See Revisor help for details."
    echo "--list                 - Just list what would have otherwise been respun."

    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

revisor_deps="comps-extras createrepo rhpl pykickstart livecd-tools
        anaconda squashfs-tools notify-python usermode
        pam python automake intltool gettext desktop-file-utils glib2-devel gcc
        koan deltarpm pygtk2-libglade gnome-python2-gconf
        system-config-kickstart jigdo python-virtinst git sudo
        spin-kickstarts mock yum-utils bittorrent bash"

##
##  Defaults
##

LIVE=0
LIVE_LOCALIZED=0
INSTALL=0
JUST_LIST=0
cleanup=1

##
## Get the options
##

while [ $# -gt 0 ]; do
    case $1 in
        --live)
            LIVE=1
            shift
        ;;

        --live-localized)
            LIVE_LOCALIZED=1
            shift
        ;;

        --install)
            INSTALL=1
            shift
        ;;

        --version)
            VERSIONS="${VERSIONS} $2"
            shift; shift
        ;;

        --arch)
            ARCHES="$ARCHES $2"
            shift; shift
        ;;

        --clean-up|--cleanup)
            cleanup=$2
            shift; shift
        ;;

        --list)
            JUST_LIST=1
            shift
        ;;

        --notify-failure)
            NOTIFICATION_FAILURE="$2"
            shift; shift
        ;;

        --notify-success)
            NOTIFICATION_SUCCESS="$2"
            shift; shift
        ;;

        *)
            usage
        ;;
    esac
done

# Thanks. Now, before we do anything, let's check if the packages we depend
# on are actually installed.

for pkg in $revisor_deps; do
    if [ -z "`rpm -qv $pkg | grep -v 'not installed'`" ]; then
        pkg_error="$pkg_error\nPackage $pkg not installed"
    fi
done

# Exit if any of the dependencies are not installed.
[ ! -z "$pkg_error" ] && echo -en "ERROR:\n$pkg_error" && exit 1

##
## Now, we have our options:
## - a list of versions to compose
## - a list of architectures to compose
##
## Let's continue
##

##
## First, we try to run from the source tree. This requires that Revisor is
## *NOT* installed from an RPM, so check that, too.
##
## If that fails, we'll look for an installed RPM and just execute the system
## Revisor.
##

if [ -z "`rpm -qv revisor-cli | grep -v 'not installed'`" ]; then
    [ -d "${TMPDIR:-/tmp}/revisor" ] && rm -rf ${TMPDIR:-/tmp}/revisor
    git clone ${GIT_REVISOR} ${TMPDIR:-/tmp}/revisor
    cd ${TMPDIR:-/tmp}/revisor/
    autoreconf -v && ./configure
    ./switchhere --yes
    revisor_cmd="sudo ./revisor.py --cli"
    revisor_cwd="${TMPDIR:-/tmp}/revisor/"
else
    revisor_cmd="sudo revisor"
    revisor_cwd="${TMPDIR:-/tmp}/"
fi

# If we're in the *.kanarip.com network, our webserver is called www.kanarip.com
# If we're not in the *.kanarip.com network, the webserver is the hostname of the
# box this script is going to run on.
[ -z "`hostname | grep kanarip.com`" ] && WEB_HOSTNAME=$HOSTNAME || WEB_HOSTNAME="www.kanarip.com"

# Some variables, for the message content and the emailaddresses to notify, etc.
MESSAGE_END="\\n\\nThe size of the iso image is: %b.\\n\\nGo to http://$WEB_HOSTNAME/revisor/%b/%b/ for more details.\\n\\nKind regards,\\n\\nJeroen van Meeuwen\\n-kanarip"

# Temp disabled because we're building everything in mock now
# Cheat our way through spin-kickstarts
[ -d ${TMPDIR:-/tmp}/spin-kickstarts ] && rm -rf ${TMPDIR:-/tmp}/spin-kickstarts
git clone ${GIT_SPINKICKSTARTS} ${TMPDIR:-/tmp}/spin-kickstarts

for version in ${VERSIONS}; do

    # If the version is rawhide, the branch for spin-kickstarts should be "master".
    # If the version is not rawhide, but, say, 9 or 10, we should be looking at
    # branch "F-9" or "F-10".
    #
    # Also, Revisor has neat "f9", "f10" and "rawhide" configuration files and models.
    # The version specified however is "9", "10" or "rawhide". So, for the non-rawhide
    # versions, append the "f".
    #
    if [ "${version}" == "rawhide" ]; then
        real_version="rawhide"
        real_branch="master"
    else
        real_version="f${version}"
        real_branch="F-${version}"
    fi

    # Now, start composing for each architecture specified with --arch
    # Loop through the list of architectures
    for arch in $ARCHES; do

        # Initialize mock and revisor for this version and architecture
        mock -v -r revisor-$version-$arch clean
        mock -v -r revisor-$version-$arch init
        mock -v -r revisor-$version-$arch install $revisor_deps
        echo -en "test -d /revisor && (cd revisor; git pull) || git clone ${GIT_REVISOR}; \\
                cd /revisor; \\
                autoreconf && ./configure; \\
                ./switchhere --yes;" | mock -v -r revisor-$version-$arch shell

        # Ghe, we know where we are. Let's do this. Get the spin-kickstarts repo
        # we cloned earlier, checkout the correct branch and install it somewhere
        # the process running in mock can find it.
        cd ${TMPDIR:-/tmp}/spin-kickstarts
        [ ! -z "`git branch -la | grep -E \"^(\*|\s)+ $real_branch\"`" ] && \
                git checkout $real_branch || \
                git checkout --track -b $real_branch origin/$real_branch
        autoreconf -v && ./configure --prefix=/var/lib/mock/revisor-$version-$arch/root/usr/ && sudo make install
        cd -

        if [ $LIVE -eq 1 ]; then
            # Loop through the available models in the /etc/revisor-unity/*-live-respin.conf
            # file, and make sure we only get the models that are the architecture we are running for
            # during this loop.

            cd ${revisor_cwd}

            if [ $LIVE_LOCALIZED -eq 1 ]; then
                spins=`${revisor_cmd} --cli --config /etc/revisor-unity/${real_version}-live-respin.conf --list-models 2>/dev/null | \
                        grep "^ ${real_version}-${arch}-" | awk '{print $1}'`
            else
                spins=`${revisor_cmd} --cli --config /etc/revisor-unity/${real_version}-live-respin.conf --list-models 2>/dev/null | \
                        grep "^ ${real_version}-${arch}-" | awk '{print $1}' | grep -vE '[[:alpha:]]{2}_[[:alpha:]]{2}'`
            fi

#              # Cheating for testing purposes
#              spins=`${revisor_cmd} --cli --config /etc/revisor-unity/${real_version}-live-respin.conf --list-models 2>/dev/null | \
#                          grep "^ ${real_version}-${arch}-" | awk '{print $1}' | grep lxde | head -n 1`

            for spin in $spins; do

                # If we're just listing what we were about to spin, echo and continue
                [ $JUST_LIST -eq 1 ] && echo $spin && continue

                echo "Creating $spin"

                # And today is... ?
                datestamp=`date +'%Y%m%d'`

                [ "$STARTDATE" != "$datestamp" ] && continue

                # Let's make sure we remove the entire directory before we attempt a respin.
                # The log files that were there get confusing if you are currently composing,
                # you know ;-)
                #
                sudo rm -rf ${REVISORDIR}/$datestamp/$spin/{*.torrent,log/}
                sudo rm -rf ${REVISORDIR}/$datestamp/$spin.{failed,success}

                echo "find /var/lib/rpm/ -name '__db.*' -delete; \\
                        cd /revisor; \\
                        autoreconf && ./configure; \\
                        sed -i -e 's/^mirrorlist/#mirrorlist/g' /revisor/unity/conf/conf.d/*.conf; \\
                        ./revisor.py --cli --config unity/conf/${real_version}-live-respin.conf \\
                                --destination-directory ${REVISORDIR}/$datestamp/ \\
                                --model $spin --copy-local --debug 9 --logfile /revisor/revisor-$spin.log \\
                                --clean-up $cleanup > /revisor/revisor-$spin-stdout.log 2>&1" | mock -v -r revisor-$version-$arch shell

                retval=$?

#                 if [ $retval -ne 0 ]; then
#                     for i in 0 1 2 3 4 5 6 7; do
#                         losetup=0
#                         while [ $losetup -eq 0 ]; do
#                             sudo /sbin/losetup -d /dev/loop$i && losetup=1
#                         done
#                     done
#                 fi

                # Damn that was freaking awesome. Now let's see what our product looks like.
                # Find the iso image, and get it's size so we can add it to the message we send out.
                isoimage=`find ${REVISORDIR}/$datestamp/$spin/live/ -name "*.iso"`

                [ ! -z "$isoimage" ] && isosize=`ls -lh $isoimage | awk '{print $5}'` || isosize="0M"

                if [ $retval -gt 0 ]; then
#                     printf "Spin $spin failed, log file attached.$MESSAGE_END" "N/A" "$datestamp" "$spin" \
#                         | mail -s "[respin] $spin $datestamp failed" \
#                             -a revisor-$spin.log \
#                             -r $NOTIFICATION_FROMADD \
#                             -c $NOTIFICATION_FAILURE $NOTIFICATION_SUCCESS
                    sudo touch ${REVISORDIR}/$datestamp/$spin.failed
                else
#                     printf "Spin $spin succeeded, log file attached.$MESSAGE_END" "$isosize" "$datestamp" "$spin" \
#                         | mail -s "[respin] $spin $datestamp succeeded" \
#                             -a revisor-$spin.log \
#                             -r $NOTIFICATION_FROMADD \
#                             $NOTIFICATION_SUCCESS
                    sudo touch ${REVISORDIR}/$datestamp/$spin.success
                fi

                sudo mkdir -p ${REVISORDIR}/$datestamp/$spin/log/
                sudo mv /var/lib/mock/revisor-$version-$arch/root/revisor/revisor-$spin.log ${REVISORDIR}/$datestamp/$spin/log/
                sudo mv /var/lib/mock/revisor-$version-$arch/root/revisor/revisor-$spin-stdout.log ${REVISORDIR}/$datestamp/$spin/log/

                # Now that it is done, run some more reporting on the spin
                if [ ! -z "${isoimage}" ]; then
                    for pkg in `find ${REVISORDIR}/$datestamp/$spin/os/$arch/ -name "*.rpm"`; do
                        rpmquery -p --nogpg --qf="%{SIZE}\t%{NAME}.%{ARCH}\n" $pkg
                    done | sort -n -r > ${TMPDIR:-/tmp}/rpms-$spin.log

                    sudo mv ${TMPDIR:-/tmp}/rpms-$spin.log ${REVISORDIR}/$datestamp/$spin/log/

                    # Now that we have today's spin, if we have yesterday's spin, we can compare
                    #
                    # Go back four weeks and generate the diffs

                    for i in `seq 28`; do
                        hist_date=`date --date="$i days ago" +"%Y%m%d"`
                        rpms_log_history=`find ${REVISORDIR}/$hist_date/$spin/log/ -name "rpms-$spin.log" 2>/dev/null | head -n 1`
                        rpms_log_today=`find ${REVISORDIR}/$datestamp/$spin/log/ -name "rpms-$spin.log" 2>/dev/null | head -n 1`
                        if [ ! -z "$rpms_log_history" -a ! -z "$rpms_log_today" ]; then
                            `pwd`/unity/scripts/live-respin-size-diff.py $rpms_log_history $rpms_log_today > ${TMPDIR:-/tmp}/rpms-diff-${hist_date}-$datestamp.log 2>&1
                            sudo mv ${TMPDIR:-/tmp}/rpms-diff-${hist_date}-$datestamp.log ${REVISORDIR}/$datestamp/$spin/log/
                        fi
                        i=$[ $i + 1 ]
                    done

                    # Make some torrents
                    #
                    # The torrent is called .new initially, so that the tracker picks up the torrent
                    # before the seeder does. We give the tracker 60 seconds.
                    #
                    spin_name=`echo $(basename $isoimage) | sed -e 's/.iso//g'`
                    [ -d $TORRENTDIR/$spin_name/ ] && sudo rm -rf $TORRENTDIR/$spin_name/
                    sudo mkdir -p $TORRENTDIR/$spin_name/
                    sudo ln $REVISORDIR/${datestamp}/${spin}/live/*.iso $TORRENTDIR/${spin_name}/
                    sudo ln $REVISORDIR/${datestamp}/${spin}/live/SHA1SUM $TORRENTDIR/${spin_name}/SHA1SUM
                    sudo maketorrent-console --piece_size_pow2 19 \
                                        --tracker_name http://kanarip.kicks-ass.org:6969/announce \
                                        --comment "Fedora Unity ${datestamp} ${version} ${arch} ${media}" \
                                        --target $TORRENTDIR/$spin_name.torrent.new \
                                        http://kanarip.kicks-ass.org:6969/announce \
                                        $TORRENTDIR/$spin_name/

                    rsync -rltpHvz --progress $TORRENTDIR/$spin_name.torrent.new rsync://kanarip.kicks-ass.org/torrent-tracker/$spin_name.torrent

                    sudo cp $TORRENTDIR/$spin_name.torrent.new $REVISORDIR/${datestamp}/${spin}/$spin_name.torrent

                    sleep 60

                    sudo mv $TORRENTDIR/$spin_name.torrent.new $TORRENTDIR/$spin_name.torrent

                    sudo chown -R torrent:torrent $TORRENTDIR

                fi

                sleep 10
            done
        fi

        if [ $INSTALL -eq 1 ]; then
            cd ${revisor_cwd}

            [ $JUST_LIST -eq 1 ] && echo ${real_version}-$arch-respin && continue

            spin_name="${real_version}-${arch}-respin"

            echo "Creating ${real_version}-${arch}-respin"

            sleep 10

            datestamp=`date +'%Y%m%d'`

            [ "$STARTDATE" != "$datestamp" ] && continue

            # Let's make sure we remove the entire directory before we attempt a respin.
            # The log files get confusing, you know ;-)
            #
            sudo rm -rf ${REVISORDIR}/$datestamp/${real_version}-$arch-respin/{*.torrent,log/}
            sudo rm -rf ${REVISORDIR}/$datestamp/${real_version}-$arch-respin.{failed,success}

            echo -en "find /var/lib/rpm/ -name '__db.*' -delete; \\
                    cd /revisor; \\
                    autoreconf && ./configure; \\
                    sed -i -e 's/^mirrorlist/#mirrorlist/g' /revisor/unity/conf/conf.d/*.conf; \\
                    ./revisor.py --cli --config unity/conf/${real_version}-install-respin.conf \\
                            --destination-directory ${REVISORDIR}/$datestamp/ \\
                            --model ${real_version}-$arch-respin --copy-local --debug 9 --logfile /revisor/revisor-${real_version}-$arch-respin.log \\
                            --clean-up $cleanup > /revisor/revisor-${real_version}-$arch-respin-stdout.log 2>&1" | mock -v -r revisor-$version-$arch shell

            retval=$?

            if [ $retval -gt 0 ]; then
#                 printf "Spin ${real_version}-$arch-respin failed, log file attached.$MESSAGE_END" "N/A" "$datestamp" "${real_version}-$arch-respin" \
#                     | mail -s "[respin] ${real_version}-$arch-respin $datestamp failed" \
#                         -a revisor-${real_version}-$arch-respin.log \
#                         -r $NOTIFICATION_FROMADD \
#                         -c $NOTIFICATION_FAILURE $NOTIFICATION_SUCCESS
                sudo touch ${REVISORDIR}/$datestamp/${real_version}-$arch-respin.failed
            else
#                 printf "Spin ${real_version}-$arch-respin succeeded, log file attached.$MESSAGE_END" "N/A" "$datestamp" "${real_version}-$arch-respin" \
#                     | mail -s "[respin] ${real_version}-$arch-respin $datestamp succeeded" \
#                         -a revisor-${real_version}-$arch-respin.log \
#                         -r $NOTIFICATION_FROMADD \
#                         $NOTIFICATION_SUCCESS
                sudo touch ${REVISORDIR}/$datestamp/${real_version}-$arch-respin.success
            fi

            sudo mkdir -p ${REVISORDIR}/$datestamp/${real_version}-$arch-respin/log/
            sudo mv /var/lib/mock/revisor-${version}-$arch/root/revisor/revisor-${real_version}-$arch-respin.log \
                        ${REVISORDIR}/$datestamp/${real_version}-$arch-respin/log/
            sudo mv /var/lib/mock/revisor-${version}-$arch/root/revisor/revisor-${real_version}-$arch-respin-stdout.log \
                        ${REVISORDIR}/$datestamp/${real_version}-$arch-respin/log/

            # Make some torrents

            if [ $retval -eq 0 ]; then
                for media in CD DVD; do
                    sudo mkdir -p $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}/
                    sudo ln $REVISORDIR/${datestamp}/${real_version}-${arch}-respin/iso/*${media}*.iso \
                                $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}/
                    sudo ln $REVISORDIR/${datestamp}/${real_version}-${arch}-respin/iso/SHA1SUM \
                                $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}/SHA1SUM
                    sudo maketorrent-console --piece_size_pow2 19 \
                                --tracker_name http://kanarip.kicks-ass.org:6969/announce \
                                --comment "Fedora Unity ${datestamp} ${version} ${arch} ${media}" \
                                --target $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}.torrent \
                                http://kanarip.kicks-ass.org:6969/announce \
                                $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}/

                    rsync -rltpHvz --progress $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}.torrent \
                                rsync://kanarip.kicks-ass.org/torrent-tracker/.

                    sudo cp $TORRENTDIR/Fedora-Unity-${datestamp}-${version}-${arch}-${media}.torrent \
                                $REVISORDIR/${datestamp}/${real_version}-${arch}-respin/

                done

                sudo chown -R torrent:torrent $TORRENTDIR

            fi
        fi
        echo -e "${arch} Respins for Fedora ${version} are done.\n\nCheckout http://www.kanarip.com/revisor for more details\n\nKind regards,\n\nJeroen van Meeuwen\n-kanarip" | \
                mail -s "[respin] Fedora ${version} ${arch} Respin Report" -r $NOTIFICATION_FROMADD $NOTIFICATION_SUCCESS
    done
done
