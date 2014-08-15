#!/bin/sh


landing_dir=$1

# these subdirectories of the root filesystem will be copied in their
# entirety
fulldump="bin boot lib lib64 sbin selinux usr vmlinuz home/dcedev"

# Create the file to append listing of files to include in the
# root filesystem image
manifest_file=/tmp/root_manifest.$$
if [ -f "${manifest_file}" ]; then
   cat /dev/null > $manifest_file
else
   touch $manifest_file
fi


if [ $? != 0 ]; then
   echo "Unable to create / truncate $manifest_file" 1>&2
   exit 1
fi


chdir /
if [ $? != 0 ]; then
   echo "Unable to change directory into the root filesystem, aborting." 1>&2
   exit 1
fi

find $fulldump -mount -print > $manifest_file && \
find etc -not \( -regex 'etc/udev/rules.d/.*persistent-.*rules' \
         -o -regex 'etc/ssh/ssh_host_.*_key' -o -regex 'etc/ssh/ssh_host_.*_key.pub' \
         -o -regex 'etc/cups/.*\.conf.*' -o -regex 'etc/cups/ppd/.*' \) -print >> $manifest_file && \
find var -not \( -regex 'var/spool/cups/c.*' -o -regex 'var/lib/dhcp/dhclient.*lease' \
         -o -regex 'var/log.*' \) >> $manifest_file && \
find run -not \( -regex 'run/udev/links/.*' -o -regex 'run/udev/tags/.*' \
         -o -regex 'run/udev/data/.*' -o -regex 'run/udev/watch/.*' \
         -o -name '*.pid' -o -name 'pid' -o -name '*.sock' -o -regex '.*socket' \
         -o -name '*.lock' \) -print >> $manifest_file

find_status=$?
if [ $find_status != 0 ]; then
   echo "find returned non-zero exit status: ${find_status}" 1>&2
   exit 1
fi

cat >> ${manifest_file} << __stand_alone__
etc/cups/cupsd.conf
etc/cups/cupsd.conf.default
etc/cups/cups-files.conf
etc/cups/snmp.conf
root/.bashrc
root/.aptitude
root/.aptitude/config
root/.aptitude/cache
root/image_system.sh
root/.gitconfig
root/.bash_history
root/.dbus
root/.ssh
root/.ssh/known_hosts
root/.profile
root/.gconf
__stand_alone__


if [ $? != 0 ]; then
   echo "Unable to append standalone files to ${manifest_file}, aborting." 1>&2
   exit 1
fi

for prev_cpio in $(ls -1 ${landing_dir}/base.cpio* | sort -k3,3 -t. -rn) ; do
   backup_cpio=$(echo $prev_cpio | perl -pe 's/base.cpio\.?(\d+)?/q(base.cpio.).(int($1) + 1)/e')
   mv $prev_cpio $backup_cpio
   if [ $? != 0 ]; then
      echo "unable to backup previous image, aborting" 1>&2
      exit 1
   fi
done

cat $manifest_file | cpio --create --reset-access-time --verbose -F ${landing_dir}/base.cpio
if [ $? != 0 ]; then
   echo "creation of root image unsuccessful." 1>&2
   exit 2
fi


