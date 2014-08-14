#!/bin/sh

log=/home/dcedev/sftp.log

fork_sftp() {
   username=$1
   filename=$2
   sha512=$3

   sftp $4 > /dev/null 2>&1 <<-__CMD_SCRIPT1__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
	__CMD_SCRIPT1__
   echo $(date +'%s') $1 $2 $3 $4 $? >> $log

   sftp $5 > /dev/null 2>&1 <<-__CMD_SCRIPT2__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
	__CMD_SCRIPT2__
   echo $(date +'%s') $1 $2 $3 $5 $? >> $log

   sftp $6 > /dev/null 2>&1 <<-__CMD_SCRIPT3__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
	__CMD_SCRIPT3__
   echo $(date +'%s') $1 $2 $3 $6 $? >> $log

   if [ -f $filename ]; then
      rm $filename
   fi
}

if [ ! -f ${log} ]; then
   touch $log
fi

( fork_sftp $* ) &
exit 0
