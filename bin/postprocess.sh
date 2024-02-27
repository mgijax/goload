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

rm -rf db_object_id.error
cut -f1 mgi.gpad | cut -f1 -d":" | sort | uniq > db_object_id.error

rm -rf taxon.error
cut -f8 mgi.gpad | sort | uniq > taxon.error

rm -rf assignedby.error
cut -f10 mgi.gpad | sort | uniq > assignedby.error

rm -rf invalidobject.error
grep "Invalid Object" goload.error | sort | uniq > invalidobject.error

rm -rf refs.error
grep "Invalid Reference" goload.error | sort | uniq > refs.error

rm -rf roid.error
grep "cannot find RO:" goload.error | sort | uniq > roid.error

rm -rf uber.error
grep "uberon id not found" goload.error | sort | uniq > uber.error
grep "uberon id has" goload.error | sort | uniq >> uber.error

rm -rf uniprotkb.error
cut -f1 mgi.gpad | grep UniProtKB | sort | uniq > uniprotkb.error

