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

GOLOG=${DATALOADSOUTPUT}/go/goload.log
rm -rf ${GOLOG}
touch ${GOLOG}
 
date | tee -a $GOLOG

#
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${DATALOADSOUTPUT}/go/lastrun
if [ -f ${LASTRUN_FILE} ]
then
    if test ${LASTRUN_FILE} -nt ${DATADOWNLOADS}/go_noctua/mgi.gpad.gz
    then
        echo "Input file has not been updated - skipping load" | tee -a ${GOLOG}
        echo 'shutting down'
        exit 0
    fi
fi

#
# only run these on Sunday
#
set weekday=`date '+%u'`
if ( $weekday == 7 ) then
        date | tee -a $GOLOG
        echo 'sunday: runnning proisoformload...'
        ${PROISOFORMLOAD}/bin/proisoform.sh | tee -a ${GOLOG} || exit 1

        date | tee -a $GOLOG
        echo 'sunday: generate GPI file (goload depends on it)...'
        REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
        ${PYTHON} ${PUBRPTS}/daily/GO_gpi.py | tee -a ${GOLOG} || exit 1
endif

date | tee -a $GOLOG
echo '1:running GO load' | tee -a ${GOLOG}
${GOLOAD}/bin/goload.sh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '2:running go_annot_extensions_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_annot_extensions_display_load.csh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '3:running go_isoforms_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_isoforms_display_load.csh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '4:running BIB_updateWFStatusGO' | tee -a ${GOLOG}
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${GOLOG}
select BIB_updateWFStatusGO();
EOSQL

touch ${LASTRUN_FILE}

date | tee -a $GOLOG

