#!/bin/sh

GHOSTSCRIPT=/usr/local/bin/gs
CUT=/usr/bin/cut
GREP=/usr/bin/grep
SED=/usr/bin/sed
REMOVE=/bin/rm

FILETYPE="$1"
TMPFILE="$2"

exit_status=1

# if there's a problem, just pretend it's a one page doc
if [ -z "${TMPFILE}" -o ! -f "${TMPFILE}"  ]; then
   echo 1
   exit $exit_status
fi


if   [ "$1" = "application/postscript" ]; then
   $GREP '^%%Pages: [0-9]' ${TMPFILE} | $CUT -d" " -f2
   exit_status=$?

elif [ "$1" = "application/pdf" ]; then
   $GHOSTSCRIPT -q -dNODISPLAY -c "(${TMPFILE}) (r) file runpdfbegin pdfpagecount = quit"
   exit_status=$?

elif [ "$1" = "text/plain" ]; then
   declare -i pages
   pages=`$SED -n '$=' ${TMPFILE}`
   exit_status=$?
   if let "pages % 64"; then
      pages="pages / 64 + 1"
   else
      pages="pages / 64"
   fi
   echo $pages 

else
   echo 1
fi

$REMOVE ${TMPFILE} >& /dev/null
exit $exit_status
