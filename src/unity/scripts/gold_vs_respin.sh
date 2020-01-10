#!/bin/bash

function usage() {
	echo This script checks if a all packages in a directory tree are
	echo in another directory tree, both of which may be specified
	echo as an ISO image that we loopmount.
	echo ""
	echo "Usage: $0 [dir|iso] [dir|iso]"
	exit 1
}

if [ -z "$1" ]; then
	echo No directory specified
	usage
fi

if [ ! -d "$1" -a ! -f "$1" ]; then
	echo This is not a directory or an ISO image
	usage
fi

if [ -z "$2" ]; then
	echo No directory specified
	usage
fi

if [ ! -d "$2" -a ! -f "$2" ]; then
	echo This is not a directory or an ISO image
	usage
fi

if [ -f "$1" ]; then
	sudo mkdir -p /mnt/respin-mnt/original
	sudo mount -o loop -t iso9660 $1 /mnt/respin-mnt/original
else
	sudo mkdir -p /mnt/respin-mnt
	sudo ln -sf $1 /mnt/respin-mnt/original
fi

if [ -f "$2" ]; then
	sudo mkdir -p /mnt/respin-mnt/respin
	sudo mount -o loop -t iso9660 $2 /mnt/respin-mnt/respin
else
	sudo mkdir -p /mnt/respin-mnt
	sudo ln -sf $2 /mnt/respin-mnt/respin
fi

orig_rpms=`find /mnt/respin-mnt/original/ -type f -name "*.rpm"`
orig_rpms_total=`find /mnt/respin-mnt/original/ -type f -name "*.rpm" | wc -l`
respin_rpms_total=`find /mnt/respin-mnt/respin/ -type f -name "*.rpm" | wc -l`

echo "RPMs in Original: $orig_rpms_total"
echo "RPMs in Re-Spin:  $respin_rpms_total"

i=0
for orig_rpm in $orig_rpms; do
	i=$[ $i + 1 ]
	echo -en "\rChecking: $i/$orig_rpms_total"
	FOUND_OK=0
	orig_rpm_name=`rpmquery --nosignature --queryformat="%{NAME}" -p $orig_rpm`
	orig_rpm_arch=`rpmquery --nosignature --queryformat="%{ARCH}" -p $orig_rpm`
	respin_rpms=`find /mnt/respin-mnt/respin/ -type f -name $orig_rpm_name*.rpm`

	for respin_rpm in $respin_rpms; do
		respin_rpm_name=`rpmquery --nosignature --queryformat="%{NAME}" -p $respin_rpm`
		respin_rpm_arch=`rpmquery --nosignature --queryformat="%{ARCH}" -p $respin_rpm`

		if [ "$orig_rpm_name" == "$respin_rpm_name" -a "$orig_rpm_arch" == "$respin_rpm_arch" ]; then
			# Found a hit for this original rpm, so we're good
			FOUND_OK=1
		fi
	done

	if [ $FOUND_OK -eq 0 ]; then
		# FOUND_OK still 0? We should complain!
		echo -e " WARNING: Missing package $orig_rpm_name from Re-Spin"
	fi
done

if [ -f "$1" ]; then
        sudo umount /mnt/respin-mnt/original
else
        sudo rm -f /mnt/respin-mnt/original
fi

if [ -f "$2" ]; then
        sudo umount /mnt/respin-mnt/respin
else
        sudo rm -f /mnt/respin-mnt/respin
fi

echo -e ""
echo "Done."
