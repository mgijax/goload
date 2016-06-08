#!/bin/sh
#
#  go.sh
#
#  Run all GOA loads from loadadmin/sundaytasks.csh
#

cd `dirname $0`

if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

LOG=${DATALOADSOUTPUT}/go/$0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG

echo 'Run GOA Load' | tee -a ${LOG}
${GOLOAD}/goamouse/goamouse.sh | tee -a ${LOG}

echo 'Run GO/Rat Load' | tee -a ${LOG}
${GOLOAD}/goarat/goarat.sh | tee -a ${LOG}

echo 'Run GO/PAINT Load' | tee -a ${LOG}
${GOLOAD}/goarefgen/goarefgen.sh | tee -a ${LOG}

echo 'Run GOA/Human Load' | tee -a ${LOG}
${GOLOAD}/goahuman/goahuman.sh | tee -a ${LOG}

echo 'Run GO/CFP Load' | tee -a ${LOG}
${GOLOAD}/goacfp/goacfp.sh | tee -a ${LOG}

date | tee -a $LOG
