#!/bin/sh

#
# grep unique errors and store in seperate error files to make it a little easier to see
#
# Invalid Object not in GPI file (1:DB_Object_ID): 
# Invalid col1/databaseID not expected (1:DB_Object_ID): 
# Invalid Reference/either no GO_REF, no pubmed id or no jnum (5:References): 
# Invalid ECO id : cannot find valid GO Evidence Code (6:Evidence_Type): 
# Invalid Relation in GO-Property (11:Annotation_Extensions,12:Annotation_Properties): cannot find RO:,BFO: id: 
# Invalid Relation in GO-Property (3:Relation Ontology): cannot find RO:,BFO: id: 
# Missing Assigned By (10):
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

rm -rf invalidcol1.error
grep "Invalid col1" goload.error | sort | uniq > invalidcol1.error

rm -rf refs.error
grep "Invalid Reference" goload.error | sort | uniq > refs.error

rm -rf roid.error
grep "cannot find RO:" goload.error | sort | uniq > roid.error

rm -rf uberon.error
grep "uberon id not found" goload.error | sort | uniq > uberon.error
grep "uberon id has" goload.error | sort | uniq >> uberon.error

rm -rf uniprotkb.error
cut -f1 mgi.gpad | grep UniProtKB | sort | uniq > uniprotkb.error

