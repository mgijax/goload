#!/bin/sh

#
# process inferredfrom and load into ACC_Accession table
#

cd `dirname $0` 

. ${GOLOAD}/goload.config

INFERREDLOG=${LOGDIR}/inferredfrom.log
rm -rf ${INFERREDLOG}
touch ${INFERREDLOG}
 
date | tee -a ${INFERREDLOG}

${PYTHON} ${GOLOAD}/bin/inferredfrom.py -S${MGD_DBSERVER} -D${MGD_DBNAME} -U${MGD_DBUSER} -P${MGD_DBPASSWORDFILE} |& tee -a ${INFERREDLOG}
${PG_DBUTILS_BCP} ${MGD_DBSERVER} ${MGD_DBNAME} ACC_Accession ${OUTPUTDIR} ACC_Accession.bcp "|" "\n" ${PG_DB_SCHEMA} |& tee -a ${INFERREDLOG}

date | tee -a ${INFERREDLOG}

