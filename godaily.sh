#!/bin/sh
#
#  go.sh
#
#  See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
#  Run daily GO loads from loadadmin/prod/dailytasks.csh
#

cd `dirname $0`

if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

GOLOG=${DATALOADSOUTPUT}/go/godaily.log
rm -rf $GOLOG
touch $GOLOG
 
date | tee -a $GOLOG

#
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
LASTRUN_FILE=${DATALOADSOUTPUT}/go/lastrun
if [ -f ${LASTRUN_FILE} ]
then
    if test ${LASTRUN_FILE} -nt ${FROM_MGIINFILE_NAME_GZ}
    then
        echo "Input file has not been updated - skipping load" | tee -a ${GOLOG}
        echo 'shutting down'
        exit 0
    fi
fi

#echo 'runnning proisoformload...'
#${PROISOFORMLOAD}/bin/proisoform.sh | tee -a ${GOLOG} || exit 1

#echo 'generate GPI file (gomousenoctua depends on it)...'
#REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
#${PYTHON} ${PUBRPTS}/daily/GO_gpi.py | tee -a ${GOLOG} || exit 1

#echo '1:running GO/Mouse/Noctua Load' | tee -a ${GOLOG}
#${GOLOAD}/gomousenoctua/gomousenoctua.sh | tee -a ${GOLOG} || exit 1

#echo 'processing protein complex go_qualifier/part_of' | tee -a ${GOLOG}
#${GOLOAD}/proteincomplex.sh | tee -a ${GOLOG} || exit 1

#echo 'running go_annot_extensions_display_load.csh' | tee -a ${GOLOG}
#${MGICACHELOAD}/go_annot_extensions_display_load.csh | tee -a ${GOLOG} || exit 1

#echo 'running go_isoforms_display_load.csh' | tee -a ${GOLOG}
#${MGICACHELOAD}/go_isoforms_display_load.csh | tee -a ${GOLOG} || exit 1

touch ${LASTRUN_FILE}

