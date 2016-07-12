#!/bin/sh
#
#  go.sh
#
#  See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
#  Run all GOA loads from loadadmin/prod/sundaytasks.csh
#

cd `dirname $0`

if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

GOLOG=${DATALOADSOUTPUT}/go/goload.log
rm -rf $GOLOG
touch $GOLOG
 
date | tee -a $GOLOG

echo '1:Run GOA/Mouse/Noctua Load' | tee -a ${GOLOG}
${GOLOAD}/goamousenoctua/goamousenoctua.sh | tee -a ${GOLOG}

echo '2:Run GOA/Mouse Load' | tee -a ${GOLOG}
${GOLOAD}/goamouse/goamouse.sh | tee -a ${GOLOG}

echo '3:Run GOA/Rat Load' | tee -a ${GOLOG}
${GOLOAD}/goarat/goarat.sh | tee -a ${GOLOG}

echo '4:Run GOA/PAINT Load' | tee -a ${GOLOG}
${GOLOAD}/goarefgen/goarefgen.sh | tee -a ${GOLOG}

echo '5:Run GOA/Human Load' | tee -a ${GOLOG}
${GOLOAD}/goahuman/goahuman.sh | tee -a ${GOLOG}

echo '6:Run GOA/CFP Load' | tee -a ${GOLOG}
${GOLOAD}/goacfp/goacfp.sh | tee -a ${GOLOG}

echo 'running go_annot_extensions_display_load...' | tee -a ${GOLOG}
${MGICACHELOAD}/gxdexpression.csh | tee -a ${GOLOG}

date | tee -a $GOLOG
