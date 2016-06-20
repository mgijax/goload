#!/bin/sh

#
# Template
#

cd `dirname $0` 

. ${GOLOAD}/goamousenoctua/goamousenoctua.config

ECOLOG=${LOGDIR}/ecocheck.sh.log
rm -rf $ECOLOG
touch $ECOLOG
 
date | tee -a $ECOLOG
 
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${ECOLOG}

select p.value, t.term, t.abbreviation, m.symbol
from VOC_Annot a, VOC_Evidence e, VOC_Term t, MRK_Marker m, VOC_Evidence_Property p, VOC_Term pt
where a._AnnotType_key = 1000
and a._Annot_key = e._Annot_key
and e._CreatedBy_key = 1559
and e._EvidenceTerm_key = t._Term_key
and a._Object_key = m._Marker_key
and e._AnnotEvidence_key = p._AnnotEvidence_key
and p._PropertyTerm_key = pt._Term_key
and pt.term = 'evidence'
;

(
select distinct a.accID as ecoID, s.synonym
from ACC_Accession a, MGI_Synonym s, MGI_SynonymType st, VOC_Term t
where a._LogicalDB_key = 182 
and a._Object_key = s._Object_key
and s._MGIType_key = 13
and s.synonym = t.abbreviation
and t._vocab_key = 3 
and s._SynonymType_key = st._SynonymType_key
and st.synonymtype = 'exact'
union all 
select distinct a2.accID, s.synonym
from ACC_Accession a, MGI_Synonym s, MGI_SynonymType st, VOC_Term t, DAG_Closure dc, ACC_Accession a2
where a._LogicalDB_key = 182 
and a._Object_key = s._Object_key
and s._MGIType_key = 13
and s.synonym = t.abbreviation
and t._vocab_key = 3 
and s._SynonymType_key = st._SynonymType_key
and st.synonymtype = 'exact'
and a._Object_key = dc._ancestorobject_key
and dc._descendentobject_key = a2._Object_key
and a2._LogicalDB_key = 182 
)
order by ecoID, synonym desc
;

EOSQL

date |tee -a ${ECOLOG}

