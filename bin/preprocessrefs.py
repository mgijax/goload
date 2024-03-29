'''
#
# preprocessrefs.py
#
#       The purpose of this script is to process a set of pubmedis from goload
#
#       The input files are generated from:
#
#               goload.sh
#                       - creates input/goload.pmid
#
#       Then the specific shell script will call preprocessrefs.py, passing it the input file name
#
#       for pubmedid in input file:
#
#               if pubmedid exists in MGI and relevance = discard and no Jnumber then
#                       set Relevance = keep
#                       add Jnumber
#
#               if pubmedid exists in MGI and relevance = keep and no Jnumber then
#                       add Jnumber
#
# History:
#
# lec   06/30/2022
#       wts2-730/Need to be sure refs that are used in annotations (i.e. in GOA folder processing) are not marked 'discard'
#
'''

import sys 
import os
import db

# only turn on when debugging
#db.setTrace()

#
# Main
#

print('\nRunning pre-procesing pmid: ', sys.argv[1])

# read input file & add quotes for SQL query
inFile = open(sys.argv[1], 'r')
pubmedids = []
for line in inFile.readlines():
        p = "'" + line[:-1] + "'"
        pubmedids.append(p)
inFile.close()

for i in pubmedids:
    # select where jnumid is null ; includes relevance = keep and discard
    cmd = '''
    select _refs_key, _relevance_key, pubmedid
    from bib_citation_cache
    where pubmedid in (%s)
    and jnumid is null
    ''' % i
    #''' % ','.join(pubmedids)

    relevanceSQL = ""
    jnumSQL = ""

    results = db.sql(cmd, 'auto')
    for r in results:
        refsKey = r['_refs_key']
        relevanceKey = r['_relevance_key']

        # if 'discard', then add 'keep'
        if relevanceKey == 70594666:
            print('setting relevance = keep for: ', r['pubmedid'])
            relevanceSQL += "\nselect * from BIB_keepWFRelevance(%s,1000);" % (refsKey);

        # always add jnum and update bib_citation_cache
        print('adding jnum for: ', r['pubmedid'])
        jnumSQL += "\nselect * from ACC_assignJ(1000,%s);" % (refsKey)
        jnumSQL += "\nselect * from BIB_reloadCache (%s);" % (refsKey)

if len(relevanceSQL) > 0:
       #print(relevanceSQL)
       db.sql(relevanceSQL, None)
else:
       print('no relevance changes needed')

if len(jnumSQL) > 0:
       #print(jnumSQL)
       db.sql(jnumSQL, None)
else:
       print('no jnum changes needed')

db.commit()

