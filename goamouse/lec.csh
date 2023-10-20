#!/bin/csh -f

#
# Template
#


if ( ${?MGICONFIG} == 0 ) then
        setenv MGICONFIG /usr/local/mgi/live/mgiconfig
endif

source ${MGICONFIG}/master.config.csh

cd `dirname $0`

setenv LOG $0.log
rm -rf $LOG
touch $LOG
 
date | tee -a $LOG
 
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $LOG

EOSQL

scp bhmgiapp01:/data/downloads/goa/MOUSE/goa_mouse.gaf.gz ${DATADOWNLOADS}/goa/MOUSE
scp bhmgiapp01:/data/downloads/goa/MOUSE/goa_mouse.gpi.gz ${DATADOWNLOADS}/goa/MOUSE
scp bhmgiapp01:/data/downloads/goa/MOUSE/goa_mouse_isoform.gaf.gz ${DATADOWNLOADS}/goa/MOUSE
scp bhmgiapp01:/data/downloads/purl.obolibrary.org/obo/uberon.obo ${DATADOWNLOADS}/purl.obolibrary.org/obo/

${GOLOAD}/goamouse/goamouse.sh

date |tee -a $LOG

