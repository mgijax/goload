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

echo 'runnning proisoformload...'
${PROISOFORMLOAD}/bin/proisoform.sh | tee -a ${GOLOG} || exit 1

echo 'generate GPI file (gomousenoctua depends on it)...'
REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
${PYTHON} ${PUBRPTS}/daily/GO_gpi.py | tee -a ${GOLOG} || exit 1

echo '1:running GO/Mouse/Noctua Load' | tee -a ${GOLOG}
${GOLOAD}/gomousenoctua/gomousenoctua.sh | tee -a ${GOLOG} || exit 1

echo 'running go_annot_extensions_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_annot_extensions_display_load.csh | tee -a ${GOLOG} || exit 1

echo 'running go_isoforms_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_isoforms_display_load.csh | tee -a ${GOLOG} || exit 1

