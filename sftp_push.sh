#!/bin/sh

fifo=/home/dcedev/sftpfifo
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
   echo $(date +'%s') $@ $? >> $log

   sftp $5 > /dev/null 2>&1 <<-__CMD_SCRIPT2__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
	__CMD_SCRIPT2__
   echo $(date +'%s') $@ $? >> $log

   sftp $6 > /dev/null 2>&1 <<-__CMD_SCRIPT3__
	cd /svc/remote
	mkdir ${username}
	cd ${username}
	put ${filename} ${sha512}
	exit 
	__CMD_SCRIPT3__
   echo $(date +'%s') $@ $? >> $log

   if [ -f $filename ]; then
      rm $filename
   fi
}



if [ ! -p ${fifo} ]; then
   echo "FIFO ${fifo} does not exist.  exiting."
   exit 3
fi

if [ ! -f ${log} ]; then
   touch $log
fi

while /bin/true; do
   args=$(cat ${fifo})
   ( fork_sftp $args ) &
done
