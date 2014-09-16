#!/bin/sh

log=/home/dcedev/sftp.log

fork_sftp() {
   username=$1
   filename=$2
   sha512=$3
   shift; shift; shift

   if [ ! -f "${filename}" ]; then
      echo $(date +'%s') $username $filename $sha512 unable to find file >> $log
      exit 1
   fi

   if [ -f "/svc/remote/UPLOAD/${username}_${sha512}" ]; then
      echo $(date +'%s') $username $filename $sha512 has been previously processed >> $log
      rm $filename
      exit 0
   fi

   thishost=$(/bin/cat /etc/mailname)

   for host in $*; do

      if [ $host = $thishost ]; then
        if [ ! -d /svc/remote/${username} ]; then
           mkdir /svc/remote/${username}
        fi
        cp ${filename} /svc/remote/${username}/${sha512}
        echo $(date +'%s') $username $filename $sha512 $host $? >> $log
      else
        sftp $host > /dev/null 2>&1 <<-__CMD_SCRIPT__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
__CMD_SCRIPT__
        echo $(date +'%s') $username $filename $sha512 $host $? >> $log
      fi
   done

   /usr/bin/touch /svc/remote/UPLOAD/${username}_${sha512}

   if [ -f $filename ]; then
      rm $filename
   fi
}

if [ ! -f ${log} ]; then
   touch $log
fi

/usr/bin/renice 12 $$
( fork_sftp $* ) &
exit 0
