#!/bin/bash

SUCCEEDED=0

tries=0
while [ ${SUCCEEDED} -eq 0 -a $tries -lt 3 ]; do
        rsync -rlptDHvz \
        --progress \
        --delete-after \
        --exclude="core/" \
        --exclude="extras/" \
        --exclude="*ppc/" \
        --exclude="*ppc64/" \
	--exclude="*debug/" \
	--exclude="releases/test/" \
	rsync://ftp.surfnet.nl/Fedora/linux/ \
        /data/fedora/

        if [ $? -eq 0 ]; then
                SUCCEEDED=1
        else
                tries=$[ $tries + 1 ]
        fi
done

# fast but not always up-to-date
#	rsync://mirror.karneval.cz/fedora/linux/ \
#	rsync://ftp-stud.hs-esslingen.de/fedora/linux/ \

# slow?
#	rsync://mirror.karneval.cz/fedora/linux/
#	rsync://rsync.mirrorservice.org/download.fedora.redhat.com/pub/fedora/linux/ \

