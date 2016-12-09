#!/usr/local/bin/python

'''
#
# goamousepost.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#	goa.annot : file of GOA annotations that can be loaded into MGI via the Annotation loader
#
# Process
#
# 1) read goa.annot input file
# 2) add BIB_DataSet_Assoc records, if needed
# 3) add MGI_Reference_Assoc records, if needed
#
# Usage:
#       goamousepost.py
#
# History:
#
# lec	12/08/2016
#	- TR11938/autoindex marker/autoselect reference
#
'''

import sys
import os
import db
import reportlib

#db.setTrace()
db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

#
# in case we ever need to delete the GOA_ associations...
#
#
#deleteBib = '''
#delete from BIB_DataSet_Assoc a
#using MGI_User u
#where a._DataSet_key = 1005
#and a._CreatedBy_key = u._User_key
#and u.login like 'GOA_%'
#'''

#deleteRef = '''
#delete from MGI_Reference_Assoc a
#using MGI_User u
#where a._MGIType_key = 2
#and a._RefAssocType_key = 1018
#and a._CreatedBy_key = u._User_key
#and u.login like 'GOA_%'
#'''

#
# insert statements
#

bibSQL = '''
insert into BIB_DataSet_Assoc 
values ((select max(_Assoc_key) + 1 from BIB_DataSet_Assoc),
%s, 1005, 0, 0, %s, %s, now(), now());
'''

refSQL = '''
insert into MGI_Reference_Assoc 
values ((select max(_Assoc_key) + 1 from MGI_Reference_Assoc),
%s, %s, 2, 1018, %s, %s, now(), now());
'''

#
# lookups
#

#print 'reading user'
assignedByLookup = {}
results = db.sql('''
select _User_key, login from MGI_User where login like 'GOA_%'
''', 'auto')
for r in results:
    key = r['login']
    value = r['_User_key']
    assignedByLookup[key] = []
    assignedByLookup[key].append(value)

#print 'reading refNotListed'
refNotExists = {}
results = db.sql('''
	select distinct c._Refs_key, c.jnumID 
	from BIB_Citation_Cache c
	where not exists (select 1 from BIB_DataSet_Assoc b where c._Refs_key = b._Refs_key and b._DataSet_key = 1005)
''', 'auto')
for r in results:
    key = r['jnumID']
    value = r['_Refs_key']
    refNotExists[key] = []
    refNotExists[key].append(value)
#print refNotExists

#print 'reading refExists'
refExists = {}
results = db.sql('''
	select distinct c._Refs_key, c.jnumID 
	from BIB_Citation_Cache c
	where exists (select 1 from BIB_DataSet_Assoc b where c._Refs_key = b._Refs_key and b._DataSet_key = 1005)
''', 'auto')
for r in results:
    key = r['jnumID']
    value = r['_Refs_key']
    refExists[key] = []
    refExists[key].append(value)
#print refExists

markerrefNotExists = '''
select distinct c._Object_key
from ACC_Accession c
where c.accID = '%s'
and c._MGIType_key = 2
and c._LogicalDB_key = 1
and c.prefixPart = 'MGI:'
and c.preferred = 1
and not exists (select 1 from MGI_Reference_Assoc b
	where c._Object_key = b._Object_key
	and b._Refs_key = %s
	and b._MGIType_key = 2
	and b._RefAssocType_key = 1018
	)
'''

#
#
# read annotFile.post
#

refcount = 0
markercount = 0

annotFile = open(os.environ['OUTPUTDIR'] + '/goamouse.annot.post', 'r')
for line in annotFile.readlines():

    line = line[:-1]
    tokens = line.split('\t')

    markerID = tokens[0]
    refID = tokens[1]
    assignedBy = tokens[2]
    
    assignedByKey = assignedByLookup[assignedBy][0]

    #  if this J: does not have the "selected" bit on, then add it
    if refID in refNotExists:
	refKey = refNotExists[refID][0]
	#print bibSQL % (refKey, assignedByKey, assignedByKey)
        db.sql(bibSQL % (refKey, assignedByKey, assignedByKey))
	refcount += 1
    elif refID in refExists:
	refKey = refExists[refID][0]

    # if the marker/reference association does not exist, then add it
    results = db.sql(markerrefNotExists % (markerID, refKey), 'auto')
    for r in results:
        markerKey = r['_Object_key']
        #print refSQL % (refKey, markerKey, assignedByKey, assignedByKey)
        db.sql(refSQL % (refKey, markerKey, assignedByKey, assignedByKey))
	markercount += 1

annotFile.close()
db.commit()
#print 'refcount: ' + str(refcount)
#print 'markercount: ' + str(markercount)
sys.exit(0)

