#!/bin/sh

#
# grep unique errors 
#

cd `dirname $0`

. ${GOLOAD}/goload.config
cd ${INPUTDIR}

#setenv POSTLOG $0.log
#rm -rf $POSTLOG
#touch $POSTLOG
 
#cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $POSTLOG
#select login from mgi_user where login like 'GO_%' order by login;
#EOSQL

rm -rf db_object_id
cut -f1 mgi.gpad | cut -f1 -d":" | sort | uniq > db_object_id

rm -rf taxon
cut -f8 mgi.gpad | sort | uniq > taxon

rm -rf assignedby
cut -f10 mgi.gpad | sort | uniq > assignedby

rm -rf invalidobject
grep "Invalid Object" goload.error | sort | uniq > invalidobject

rm -rf refs
grep "Invalid Reference" goload.error | sort | uniq > refs

rm -rf roid
grep "cannot find RO:" goload.error | sort | uniq > roid

rm -rf uber
grep "uberon id not found" goload.error | sort | uniq > uber

rm -rf uniprotkb
cut -f1 mgi.gpad | grep UniProtKB | sort | uniq > uniprotkb

