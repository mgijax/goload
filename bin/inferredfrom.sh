#!/bin/sh

#
# process inferredfrom and load into ACC_Accession
#

cd `dirname $0` 

. ${GOLOAD}/goload.config

LOG=${LOGDIR}/inferredfrom.log
rm -rf ${LOG}
touch ${LOG}
 
date | tee -a ${LOG}

${PYTHON} ${GOLOAD}/bin/inferredfrom.py |& tee -a ${LOG}

date | tee -a ${LOG}

