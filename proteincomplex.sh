#!/bin/sh
#
# for each GO id in the 'GO Protein Complex' (_vocab_key = 171)
#       for each Annotation that uses this GO id:
#               if the Annotation does not contain a stanza/go_qualifier/part_of
#                       then add the stanza/go_qualifier/part_of
#

cd `dirname $0`

if [ "${MGICONFIG}" = "" ]
then
    MGICONFIG=/usr/local/mgi/live/mgiconfig
    export MGICONFIG
fi

. ${MGICONFIG}/master.config.sh

date | tee -a $GOLOG

cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a $GOLOG

--for testing only
--delete from voc_evidence_property where _evidenceproperty_key > 1184924825;
--Gmpr

select distinct m.symbol, a.accid, c._term_key, substring(t.term,1,30) as term, e._annotevidence_key, p.stanza, 1 as hasStanza
into temp table toAdd
from voc_annot v, voc_evidence e, mrk_marker m, acc_accession a, voc_term c, voc_term t, voc_evidence_property p
where v._annottype_key = 1000
and v._annot_key = e._annot_key
and v._object_key = m._marker_key
and v._term_key = a._object_key
and a._mgitype_key = 13
and a.preferred = 1
and a.accid = c.term
and c._vocab_key = 171
and v._term_key = t._term_key
and e._annotevidence_key = p._annotevidence_key
and not exists (select 1 from voc_evidence_property p where e._annotevidence_key = p._annotevidence_key and p._propertyterm_key in (18583064))
union
select distinct m.symbol, a.accid, c._term_key, substring(t.term,1,30) as term, e._annotevidence_key, 1, 0
from voc_annot v, voc_evidence e, mrk_marker m, acc_accession a, voc_term c, voc_term t
where v._annottype_key = 1000
and v._annot_key = e._annot_key
and v._object_key = m._marker_key
and v._term_key = a._object_key
and a._mgitype_key = 13
and a.preferred = 1
and a.accid = c.term
and c._vocab_key = 171
and v._term_key = t._term_key
-- no stanza exist
and not exists (select 1 from voc_evidence_property p where e._annotevidence_key = p._annotevidence_key)
and not exists (select 1 from voc_evidence_property p where e._annotevidence_key = p._annotevidence_key and p._propertyterm_key in (18583064))
;

select last_value from voc_evidence_property_seq;

select * from toAdd order by symbol, accid, hasStanza;

insert into voc_evidence_property
select nextval('voc_evidence_property_seq'), _annotevidence_key, 18583064, stanza, 1, 'part_of', 1001, 1001
from toAdd
;

select last_value from voc_evidence_property_seq;

EOSQL

date | tee -a $GOLOG
