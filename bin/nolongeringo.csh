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

--select c.mgiid, c.jnumid, wfs.*
select c.jnumid, r.modification_date
from bib_workflow_status wfs, bib_citation_cache c, bib_refs r
where wfs._refs_key = c._refs_key
and wfs.iscurrent = 1
and wfs._group_key =  31576666
and wfs._status_key = 31576674
and c._refs_key = r._refs_key
and r._createdby_key in (1000,1569)
and not exists (select 1 from voc_annot v, voc_evidence e 
        where v._annottype_key = 1000 
        and v._annot_key = e._annot_key
        and wfs._refs_key = e._refs_key
        )
order by r.modification_date, c.jnumid
;

EOSQL

date |tee -a $LOG

