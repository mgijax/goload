#!/bin/sh
#
#  go.sh
#
#  See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload_overview
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

#echo '1A:Run GOA/Mouse/Noctua Load' | tee -a ${LOG}
#${GOLOAD}/goamousenoctua/goamousenoctua.sh | tee -a ${LOG}

echo '1:Run GOA/Mouse Load' | tee -a ${LOG}
${GOLOAD}/goamouse/goamouse.sh | tee -a ${LOG}

echo '2:Run GOA/Rat Load' | tee -a ${LOG}
${GOLOAD}/goarat/goarat.sh | tee -a ${LOG}

echo '3:Run GOA/PAINT Load' | tee -a ${LOG}
${GOLOAD}/goarefgen/goarefgen.sh | tee -a ${LOG}

echo '4:Run GOA/Human Load' | tee -a ${LOG}
${GOLOAD}/goahuman/goahuman.sh | tee -a ${LOG}

echo '5:Run GOA/CFP Load' | tee -a ${LOG}
${GOLOAD}/goacfp/goacfp.sh | tee -a ${LOG}

date | tee -a $LOG
