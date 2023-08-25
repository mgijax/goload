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

echo '1:runnning proisoformload...'
${PROISOFORMLOAD}/bin/proisoform.sh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '2:generate GPI file (gomousenoctua depends on it)...'
REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
${PYTHON} ${PUBRPTS}/daily/GO_gpi.py | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '3:running BIB_updateWFStatusGO' | tee -a ${GOLOG}

#${PG_MGD_DBSCHEMADIR}/trigger/VOC_Evidence_Property_drop.object | tee -a ${GOLOG}
#cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${GOLOG}
#select e._Annot_key, e._AnnotEvidence_key, p._EvidenceProperty_key
#into temp toDelete
#from VOC_Annot a, VOC_Evidence e, VOC_Evidence_Property p
#where a._AnnotType_key = 1000
#and a._Annot_key = e._Annot_key
#and e._AnnotEvidence_key = p._AnnotEvidence_key
#;
#
#create index td2_idx1 on toDelete(_Annot_key);
#create index td2_idx2 on toDelete(_AnnotEvidence_key);
#create index td2_idx3 on toDelete(_EvidenceProperty_key);
#
#delete from MGI_Note n using toDelete d where n._MGIType_key = 41 and d._EvidenceProperty_key = n._Object_key;
#delete from VOC_Evidence_Property  p using toDelete d where d._AnnotEvidence_key = p._AnnotEvidence_key;
#delete from VOC_Evidence e using toDelete d where d._AnnotEvidence_key = e._AnnotEvidence_key;
#delete from VOC_Annot a using toDelete d where d._Annot_key = a._Annot_key;
#
#EOSQL
#${PG_MGD_DBSCHEMADIR}/trigger/VOC_Evidence_Property_create.object | tee -a ${GOLOG}

date | tee -a $GOLOG
echo '4:running GO/Mouse/Noctua Load' | tee -a ${GOLOG}
${GOLOAD}/gomousenoctua/gomousenoctua.sh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '8:running go_annot_extensions_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_annot_extensions_display_load.csh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '9:running go_isoforms_display_load.csh' | tee -a ${GOLOG}
${MGICACHELOAD}/go_isoforms_display_load.csh | tee -a ${GOLOG} || exit 1

date | tee -a $GOLOG
echo '10:running BIB_updateWFStatusGO' | tee -a ${GOLOG}
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${GOLOG}
select BIB_updateWFStatusGO();
EOSQL

touch ${LASTRUN_FILE}

date | tee -a $GOLOG
