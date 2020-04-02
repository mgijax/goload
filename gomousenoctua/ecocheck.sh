#!/bin/sh

#
# Template
#

cd `dirname $0` 

. ${GOLOAD}/gomousenoctua/gomousenoctua.config

ECOLOG=${LOGDIR}/ecocheck.sh.log
rm -rf $ECOLOG
touch $ECOLOG
 
date | tee -a $ECOLOG
 
echo 'Eco Id -> Evidence Code associations' | tee -a ${ECOLOG}
${PYTHON} ${GOLOAD}/lib/ecolib.py | sort | tee -a ${ECOLOG}

echo '' | tee -a ${ECOLOG}

echo 'Eco Id -> Evidence Code associations used in GO annotatins' | tee -a ${ECOLOG}

cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0 | tee -a ${ECOLOG}
select distinct p.value, t.term, t.abbreviation, m.symbol
from VOC_Annot a, VOC_Evidence e, VOC_Term t, MRK_Marker m, VOC_Evidence_Property p, VOC_Term pt
where a._AnnotType_key = 1000
and a._Annot_key = e._Annot_key
and e._CreatedBy_key = 1559
and e._EvidenceTerm_key = t._Term_key
and a._Object_key = m._Marker_key
and e._AnnotEvidence_key = p._AnnotEvidence_key
and p._PropertyTerm_key = pt._Term_key
and pt.term = 'evidence'
order by symbol, value
;

EOSQL

date |tee -a ${ECOLOG}

