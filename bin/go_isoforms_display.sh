#!/bin/sh

#
# process annotation isoform  and load into MGI_Note
#

cd `dirname $0`

. ${GOLOAD}/goload.config

LOG=${LOGDIR}/go_isoforms_display.log
rm -rf ${LOG}
touch ${LOG}

date | tee -a ${LOG}

${PYTHON} ${GOLOAD}/bin/go_isoforms_display.py |& tee -a ${LOG}

date | tee -a ${LOG}
