#!/bin/sh
#
#  go.sh
#
#  See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
#  Run all GO loads from loadadmin/prod/sundaytasks.csh
#

cd `dirname $0`

if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

GOLOG=${DATALOADSOUTPUT}/go/go.log
rm -rf $GOLOG
touch $GOLOG
 
date | tee -a $GOLOG

echo 'runnning proisoformload...'
${PROISOFORMLOAD}/bin/proisoform.sh | tee -a ${GOLOG} || exit 1

echo 'generate GPI file (gomousenoctua depends on it)...'
REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
${PYTHON} ${PUBRPTS}/daily/GO_gpi.py | tee -a ${GOLOG} || exit 1

echo '1:running GO/Mouse/Noctua Load' | tee -a ${GOLOG}
${GOLOAD}/gomousenoctua/gomousenoctua.sh | tee -a ${GOLOG} || exit 1

echo '2:running GOA/Mouse Load' | tee -a ${GOLOG}
${GOLOAD}/goamouse/goamouse.sh | tee -a ${GOLOG} || exit 1

echo '3:running GO/Rat Load' | tee -a ${GOLOG}
${GOLOAD}/gorat/gorat.sh | tee -a ${GOLOG} || exit 1

echo '4:running GO/PAINT Load' | tee -a ${GOLOG}
${GOLOAD}/gorefgen/gorefgen.sh | tee -a ${GOLOG} || exit 1

echo '5:running GOA/Human Load' | tee -a ${GOLOG}
${GOLOAD}/goahuman/goahuman.sh | tee -a ${GOLOG} || exit 1

echo '6:running GO/CFP Load' | tee -a ${GOLOG}
${GOLOAD}/gocfp/gocfp.sh | tee -a ${GOLOG} || exit 1

echo 'processing protein complex go_qualifier/part_of' | tee -a ${GOLOG}
${GOLOAD}/proteincomplex.sh | tee -a ${GOLOG} || exit 1

echo 'running go_annot_extensions_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_annot_extensions_display_load.csh | tee -a ${GOLOG} || exit 1

echo 'running go_isoforms_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_isoforms_display_load.csh | tee -a ${GOLOG} || exit 1

echo 'running BIB_updateWFStatusGO' | tee -a ${GOLOG}
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${GOLOG}
select BIB_updateWFStatusGO();
EOSQL
