#!/bin/sh

#
# process inferredfrom and load into ACC_Accession table
#

cd `dirname $0` 

. ${GOLOAD}/goload.config

LOG=${LOGDIR}/inferredfrom.log
rm -rf ${LOG}
touch ${LOG}
 
date | tee -a ${LOG}

${PYTHON} ${GOLOAD}/bin/inferredfrom.py -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} |& tee -a ${LOG}

date | tee -a ${LOG}

