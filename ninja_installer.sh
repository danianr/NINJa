#!/bin/sh


unmount_filesystems() for fs in $*; do
                         umount $fs
                         if [ $? != 0 ]; then
                            echo unable to unmount $fs filsystem
                         fi
                      done


diskdevice=/dev/sda
printf ",1024,L,*\n,4096,L\n,4096,S\n,+,E\n,2048,L\n,2048,L\n,4096,L\n,+,L\n"  | sfdisk -D -uM $diskdevice

if [ $? != 0 ]; then
   echo there was a problem paritioning the disk
   exit 2
else
   # zero out the first 512 bytes of each partition
   dd if=/dev/zero of=${diskdevice}1 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}2 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}3 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}5 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}6 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}7 bs=512 count=1
   dd if=/dev/zero of=${diskdevice}8 bs=512 count=1
fi

# Make the filesystems

mkfs -t ext3 -L ROOT  ${diskdevice}2
if [ $? != 0 ]; then
   echo there was a problem creating the root filesystem
   exit 3
fi


mkfs -t ext3 -L BOOT  ${diskdevice}1
if [ $? != 0 ]; then
   echo there was a problem creating the /boot filesystem
   exit 3
fi


mkfs -t ext3 -L VAR   ${diskdevice}5
if [ $? != 0 ]; then
   echo there was a problem creating the /var filesystem
   exit 3
fi


mkfs -t ext3 -L HOME  ${diskdevice}6
if [ $? != 0 ]; then
   echo there was a problem creating the /home filesystem
   exit 3
fi


mkfs -t ext3 -L IMAGE ${diskdevice}7
if [ $? != 0 ]; then
   echo there was a problem creating the filesystem for the image
   exit 4
fi

mkfs -t ext3 -L SVC   ${diskdevice}8
if [ $? != 0 ]; then
   echo there was a problem creating the /svc filesystem
fi


# format the swap partion and load it
mkswap -L SWAP ${diskdevice}3
if [ $? != 0 ]; then
   echo there was a problem initializing the swap partion
else
   swapon -L SWAP
fi

# mount the newly created filesystems under /mnt/ninja
# note that the /mnt/ninja mount point is on the USB
# thumbdrive used by the installer

mount -o rw -L ROOT /mnt
if [ $? != 0 ]; then
   echo unable to mount the root filesystem under /mnt
   exit 5
else
   mounted_filesystems=/mnt
fi

# Create the basic mount points
# we only care about atomic success, so unless all
# mkdir commands succeed, proceed to rolling back the changes
mkdir /mnt/dev  && \
mkdir /mnt/proc && \
mkdir /mnt/sys  && \
mkdir /mnt/tmp  && \
mkdir /mnt/mnt  && \
mkdir /mnt/boot && \
mkdir /mnt/var  && \
mkdir /mnt/home && \
mkdir /mnt/svc

if [ $? != 0 ]; then
   # Flush the pending writes to avoid a directory in
   # a "busy" state being removed (cached file entries
   # which have yet to be committed to disk will cause
   # the directory to declare itself busy)
   sync
   rmdir /mnt/dev /mnt/proc /mnt/sys /mnt/boot /mnt/var /mnt/home /mnt/svc 
   unmount_filesystems ${mounted_filesystems}
fi


mount -o rw -L VAR /mnt/var
if [ $? != 0 ]; then
   unmount_filesystems ${mounted_filesystems}
   exit 5
else
   mounted_filesystems="/mnt/var ${mounted_filesystems}"
fi


mount -o rw -L HOME /mnt/home
if [ $? != 0 ]; then
   unmount_filesystems ${mounted_filesystems}
   exit 5
else
   mounted_filesystems="/mnt/home ${mounted_filesystems}"
fi

mount -o rw -L BOOT /mnt/boot
if [ $? != 0 ]; then
   unmount_filesystems ${mounted_filesystems}
   exit 5
else
   mounted_filesystems="/mnt/boot ${mounted_filesystems}"
fi

mount -o rw -L SVC /mnt/svc
if [ $? != 0 ]; then
   unmount_filesystems ${mounted_filesystems}
   exit 5
else
   mounted_filesystems="/mnt/svc ${mounted_filesystems}"
   mkdir /mnt/svc/remote
   chown 1000:1000 /mnt/svc/remote
   chmod 775 /mnt/svc/remote
fi

cd /mnt
if [ -f /lib/live/mount/medium/ninja/base.cpio ]; then
   cpio -idmuV -F /lib/live/mount/medium/ninja/base.cpio
else
   unmount_filesystems ${mounted_filesystems}
   exit 6
fi



if [ "$1x" = "x" ]; then
   # Determine the hostname of the client system based on assigned ip address
   # and copy in the appropriate ssh host keys
   #
   ip=`/sbin/ifconfig eth0 | sed -n 's/.*inet addr[^123456789]*\([^ ]*\).*/\1/p'`
   ninja_hostname=`dig +short -x ${ip} | sed 's/\.$//'`
else
   ip=$1
   ninja_hostname=$2
fi
   
ninja=`echo ${ninja_hostname} | sed 's/\..*//'`
rm /mnt/etc/ssh/ssh_host_*
cp /lib/live/mount/medium/ninja/keyring/${ninja}/* /mnt/etc/ssh/

 # Give the cloned images the proper hostname
 sed -i "/ninja/ {s/.*/${ip} ${ninja} ${ninja_hostname}/;}" /mnt/etc/hosts
 echo ${ninja_hostname} > /mnt/etc/mailname
 echo ${ninja} > /mnt/etc/hostname


mkdir /mnt/var/log && cd /mnt/var/log
if [ $? = 0 ]; then
   touch pm-powersave.log aptitude daemon.log btmp mail.log syslog debug lpr.log Xorg.0.log kern.log dmesg  \
         lastlog user.log  faillog fontconfig.log  wtmp mail.info mail.warn mail.err auth.log \
         messages alternatives.log dpkg.log

   mkdir apt && touch apt/term.log apt/history.log
   mkdir ConsoleKit && touch ConsoleKit/history
   mkdir exim4 && touch exim4/mainlog 
   mkdir cups && touch cups/access_log cups/page_log cups/error_log
   mkdir fsck && touch fsck/checkfs fsck/checkroot
fi

# Remove the cloned system's network interface entry if present
if [ -f /mnt/etc/udev/rules.d/70-persistent-net.rules ]; then
   rm /mnt/etc/udev/rules.d/70-persistent-net.rules
fi

if [ -d /mnt/boot/grub -a -x /mnt/usr/sbin/grub-setup ]; then
   /mnt/usr/sbin/grub-setup -d /mnt/boot/grub ${diskdevice}
fi 

if [ $? != 0 ]; then
   echo unable to install grub bootloader to the MBR 
   exit 6
fi

mount --rbind /dev  /mnt/dev
mount --rbind /sys  /mnt/sys
mount -t proc proc  /mnt/proc
mount -t tmpfs swap /mnt/tmp

cat > /mnt/tmp/setup_chrooted.sh<<__SETUP_CHROOTED__
#!/bin/sh
cd /etc
rm mtab
egrep -v 'rootfs|live|sdb' /proc/mounts > mtab

cat > fstab<<__ETC_FSTAB__
# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
# / was on /dev/sda1 during installation
tmpfs      /tmp           tmpfs   nodev,nosuid      0       0
LABEL=ROOT /              ext3    errors=remount-ro 0       1
LABEL=BOOT /boot          ext3    defaults 0 2
LABEL=HOME /home          ext3    defaults 0 2
LABEL=SWAP none           swap    sw       0 0
LABEL=VAR /var            ext3    defaults 0 2
LABEL=SVC /svc            ext3    defaults 0 2
__ETC_FSTAB__

# create the new device.map with only a single entry for the primary disk
ls /dev/disk/by-id/ata-* | grep -v part | sed -n '1,1s/.*/(hd0)\t&/p' > /boot/grub/device.map
grub-mkconfig -o /boot/grub/grub.cfg
grub-install ${diskdevice}


rm mtab
ln -s /proc/mounts mtab

__SETUP_CHROOTED__

chmod 755 /mnt/tmp/setup_chrooted.sh

chroot /mnt /bin/bash /tmp/setup_chrooted.sh


sync
mount -L IMAGE -t ext3 -o rw /mnt/mnt
if [ $? = 0 ]; then
   cp /lib/live/mount/medium/ninja/base.cpio /mnt/mnt/ninja.cpio && \
   cp /lib/live/mount/medium/ninja/base.sha1 /mnt/mnt/base.sha1 && \
   cd /mnt && \
   sync && \
   cpio -oav --append -F /mnt/mnt/ninja.cpio <<__APPEND_LIST__
etc/fstab
etc/hosts
etc/hostname
etc/mailname
etc/ssh/ssh_host_rsa_key
etc/ssh/ssh_host_rsa_key.pub
etc/ssh/ssh_host_dsa_key
etc/ssh/ssh_host_dsa_key.pub
etc/ssh/ssh_host_ecdsa_key
etc/ssh/ssh_host_ecdsa_key.pub
boot/grub/device.map
boot/grub/grub.cfg
__APPEND_LIST__
   /usr/bin/openssl dgst -sha1 /mnt/mnt/ninja.cpio | cut -f 2 -d " " > /mnt/mnt/ninja.sha1
fi

sync
umount -l /mnt/mnt
umount -l /mnt/home
umount -l /mnt/var
umount -l /mnt/boot
umount -l /mnt/svc
umount -l /mnt/tmp
umount -l /mnt/sys
umount -l /mnt/proc
umount -l /mnt/dev
umount /mnt

echo "${ninja_hostname} has been successfully installed"
exit 0
