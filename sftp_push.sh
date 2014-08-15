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


   for host in $*; do
      sftp $host > /dev/null 2>&1 <<-__CMD_SCRIPT__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
__CMD_SCRIPT__
      echo $(date +'%s') $username $filename $sha512 $host $? >> $log
   done

   if [ -f $filename ]; then
      rm $filename
   fi
}

if [ ! -f ${log} ]; then
   touch $log
fi

( fork_sftp $* ) &
exit 0
