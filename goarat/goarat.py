#!/usr/local/bin/python

'''
#
# goarat.py
#
#	See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goratload
#
#       The GO/Rat file contains:
#
#               field 1: Database ID (RGD or UniProtKB)
#               field 2: RGD ID (12345)
#               field 4: Qualifier value
#               field 5: GO ID
#               field 6: RGD|PMID
#               field 7: Evidence code
#               field 8: Inferred From
#               field 14: Modification Date
#               field 15: Assigned By
#
#       The annotation loader format has the following columns:
#
#       A tab-delimited file in the format:
#               field 1: Accession ID of Vocabulary Term being Annotated to
#               field 2: ID of MGI Object being Annotated (ex. MGI ID)
#               field 3: J::155856
#               field 4: Evidence Code Abbreviation = ISO
#               field 5: Inferred From = UniProt ID
#               field 6: Qualifier = null
#               field 7: Editor = RGD
#               field 8: Date (MM/DD/YYYY)
#               field 9: Notes 
#
# Usage:
#       goarat.py
#
#
# History:
#
# lec	01/13/2014
#	- TR11570/11571/qualifier contains "_" in both input and MGI
#	- use VOC_Term instead of MGI_Synonym
#	- fix qualifierValue verification ('not') bug
#	- fix clusterID bug
#
# sc    02/2013 - N2MO/TR6519 - updated go use MRK_Cluster* tables with new rules
#
# lec   04/23/2012
#       - TR11041; add GO:0005488 to goIDList (exclude)
#
# lec   11/09/2010
#       - TR10445; marker type "gene"/1 only
#
# lec   04/13/2010
#       - TR10166; exclude GO:0005515 annotations
#
# lec   02/16/2010
#       - created
#
'''

import sys
import os
import string
import db

db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

# GAF file from the dataloads directory
inFileName = None

# GAF file pointer
inFile = None

# annotation formatted file
annotFileName = None

# annotation file pointer
annotFile = None

# line by line report with reason codes
reasonCodeFile = None

# list of evidence codes that are loaded into MGI
evidenceCodeList = ['IDA', 'IPI', 'IGI', 'IMP', 'EXP']

# list of GO ids that are skipped
excludedList = ['GO:0005515', 'GO:0005488']

# RGD rat IDs that contain mouse orthologs 
# {ratID:[mouse MGI ID|clusterID, ...], ...}
ratIdDict = {}

#  mouse annotations that contain a "NOT" qualifier
# {ratID: [GoID,...], ...}
isNotDict = {}

# Dict of marker/go id/inferredFrom for J:73065 from the database
# value is db.sql result set
# {mouse mgiID: [{'goID':goID, 'accID':mouse MGI ID, 'inferredFrom':evidInfFrom, ...}, ...]
infFromExistsDict = {}

# Dict of number of members by class
# {clusterID:numMembers, ...}
memberNumDict = {}

# list of all Biological Process GO Ids
# These are not transfered when no 1:1
bioProcessList = []

# cluster IDs mapped to rat NOT GO IDs 
clusterIDsWithNotDict = {}

#
# Purpose: reinitialize input file descriptor`
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Copies & opens files
# Throws: Nothing
#
def reinitialize():
    global inFile

    inFile.close()
    inFileName = os.environ['INFILE_NAME_GOAGAF']
    inFile = open(inFileName, 'r')

#
# Purpose:  Create lookup of MGI clusters with rat NOT annotations
# Returns: 
# Assumes: 
# Effects: 
# Throws: 
#

def preprocess():
    global clusterIDsWithNotDict

    for line in inFile.readlines():
        if line[0] == '!':
            continue

        tokens = string.split(line[:-1], '\t')

        databaseID = tokens[0]
        ratID = tokens[1]
        symbol = tokens[2]
        qualifierValue = tokens[3].lower()
        goID = tokens[4]
	references = tokens[5]
        evidenceCode = tokens[6]
        inferredFrom = tokens[7]
        modDate = tokens[13]
        assignedBy = tokens[14]
        note = ''
        properties = ''
	clusterID = ''

        # if goa/mouse orthology by RGD or UniProt ID get cluster ID
        if ratIdDict.has_key(ratID):
            mgiIDandClusterIDList = ratIdDict[ratID]
            # cluster will be the same for all markers with this ratID
            for ids in mgiIDandClusterIDList:
                (mgiID, cID) = string.split(ids, '|')
                clusterID = cID

        if len(qualifierValue) > 0 and qualifierValue[:3] == 'not':
            #print 'qualifierValue has NOT data: %s ' % line
            if not clusterIDsWithNotDict.has_key(clusterID):
                clusterIDsWithNotDict[clusterID] = []
            clusterIDsWithNotDict[clusterID].append(goID)

#
# Purpose: Open and copy files. Create lookups
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Copies & opens files
# Throws: Nothing
#
def initialize():

    global inFileName, inFile
    global annotFileName, annotFile
    global reasonCodeFile, memberNumDict
    global ratIdDict, isNotDict, infFromExistsDict, bioProcessList

    inFileName = os.environ['INFILE_NAME_GOAGAF']
    annotFileName = os.environ['INFILE_NAME_GOA']
    reasonCodeFileName = os.environ['RPTDIR'] + '/reasonCode.rpt'

    inFile = open(inFileName, 'r')

    annotFile = open(annotFileName, 'w')

    reasonCodeFile = open(reasonCodeFileName, 'w')

    db.useOneConnection(1)
  
    # select all bioprocess go terms and load into a list 
    results = db.sql('''select t.term, a.accid
	from DAG_Node dn, VOC_Term t, ACC_Accession a
	where dn._DAG_Key = 3
	and dn._Object_key = t._Term_key
	and t._term_key = a._Object_key
	and a._MGIType_key = 13
	and a._LogicalDB_key = 31''', 'auto')

    for r in results:
	bioProcessList.append(r['accid'])

    #
    # select rat and human cluster members from all clusters with both
    # and get all rat uniprot ids and mouse mgi ids
    #
    # load lookups:
    # 1. number of members by class ID
    # 2. MGI cluster ID and mouse gene MGI IDs by uniprot (goa) or RGD ID
    # 3. MGI NOT annotation lookup
    # 4. MGI GO annotations to J:73065
    #

    db.sql('''select c.clusterID, cm.*, m._Organism_key
	into temp mouse
	from MRK_Cluster c, MRK_ClusterMember cm, MRK_Marker m
	where c._ClusterType_key = 9272150
	and c._ClusterSource_key = 9272151
	and c._Cluster_key = cm._Cluster_key
	and cm._Marker_key = m._Marker_key
	and m._Organism_key = 1
	and m._Marker_Type_key = 1 
	and lower(m.symbol) not  like 'gm%'
	and lower(m.name) not like '%predicted%' ''', None)

    db.sql('create index m_idx1 on mouse(clusterID)', None)

    db.sql('''select c.clusterID, cm.*, m._Organism_key
	into temp rat
	from MRK_Cluster c, MRK_ClusterMember cm, MRK_Marker m
	where c._ClusterType_key = 9272150
	and c._ClusterSource_key = 9272151
	and c._Cluster_key = cm._Cluster_key
	and cm._Marker_key = m._Marker_key
	and m._Organism_key = 40
	and m._Marker_Type_key = 1''', None)

    db.sql('create index r_idx1 on rat(clusterID)', None)

    db.sql('''select m.*
	into temp mouseRat
	from mouse m, rat h
	where m.clusterID = h.clusterID
	UNION
	select h.*
	from mouse m, rat h
	where m.clusterID = h.clusterID''', None)

    # get rat RGD ids/uniprot IDs and mouse marker MGI IDs
    db.sql('''select distinct h2.clusterID, h2._Marker_key, a1.accID as ratID, a2.accID as mouseID
	into temp goarat
	from mouseRat h1, mouseRat h2, ACC_Accession a1, ACC_Accession a2
	where h1._Organism_key = 40
	and h1.clusterID = h2.clusterID
	and h2._Organism_key = 1
	and h1._Marker_key = a1._Object_key
	and a1._MGIType_key = 2
	and (a1._LogicalDB_key = 47 or a1._LogicalDB_key = 13)
	and a1.preferred = 1
	and h2._Marker_key = a2._Object_key
	and a2._MGIType_key = 2
	and a2._LogicalDB_key = 1
	and a2.preferred = 1''', None)

    db.sql('create index gr_idx1 on goarat(_Marker_key)', None)

    # Load the number of members by class lookup
    results = db.sql('select * from mouseRat order by clusterID' , 'auto')
    for r in results:
	clusterID = r['clusterID']
	if not memberNumDict.has_key(clusterID):
	    memberNumDict[clusterID] = 0
	memberNumDict[clusterID] += 1

    results = db.sql('select * from goarat', 'auto')
    for r in results:
	key = r['ratID']
	mouseID = r['mouseID']
	clusterID = r['clusterID']
	value = '%s|%s' % (mouseID, clusterID)
	if not ratIdDict.has_key(key):
	    ratIdDict[key] = []
	ratIdDict[key].append(value)

    # create MGI mouse NOT lookup
    results = db.sql('''select distinct g.ratID, acc.accID as goID
	      from goarat g join
		voc_annot a on (
			a._object_key = g._marker_key
			and a._annottype_key = 1000
		) join
		voc_term q on q._term_key = a._qualifier_key
		left outer join
		acc_accession acc on (
			acc._object_key = a._term_key
			and acc._mgitype_key = 13
			and acc.preferred = 1
		)
	      where q.term = 'NOT'
	  ''', 'auto')

    for r in results:
	key = r['ratID']
	value = r['goID']
	if not isNotDict.has_key(key):
	    isNotDict[key] = []
	isNotDict[key].append(value)

    # create lookup of MGI GO annotations to J:73065
    results = db.sql('''select t.accID as goID, a2.accID, e.inferredFrom
	      from VOC_Annot a, VOC_Evidence e, VOC_Term_View t, ACC_Accession a2
	      where a._AnnotType_key = 1000
	      and a._AnnotType_key = 1000
	      and a._Annot_key = e._Annot_key
	      and e._Refs_key = 74017
	      and e._EvidenceTerm_key = 3251466
	      and a._Term_key = t._Term_key
	      and a._Object_key = a2._Object_key
	      and a2._MGIType_key = 2
	      and a2._LogicalDB_key = 1
	      and a2.preferred = 1
	  ''', 'auto')

    for r in results:
	key = r['accID']
	value = r
	if not infFromExistsDict.has_key(key):
	    infFromExistsDict[key] = []
	infFromExistsDict[key].append(value)

    db.useOneConnection(0)

#
# Purpose: Read GAF file and generate Annotation file
# Returns: 1 if file can be read/processed correctly, else 0
# Assumes: Nothing
# Effects: Reads input file and creates output annotation file
# Throws: Nothing
#
def readGAF():

    # reference used by this load
    jnumID = 'J:155856'

    # evidence code for all annotations
    new_evidenceCode = 'ISO'

    # annotation editor value
    editor = 'RGD'

    # prefix for the single property type we create
    propertyPrefix = 'external ref&=&'

    # build a dictionary of lines to write to output file (annotload input file)
    # {annotLine sans modDate, note, properties: [list of properties], ...}
    annotToWriteDict = {}
    
    # annotation line sans modDate, note, properties
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t'

    # Use reasonCodeFile to report every line prepended with
    # 1. line number
    # 2. reason code
    # 3. cluster ID if applicable/TAB if not
    # 4. line 

    lineNum = 0
    for line in inFile.readlines():
    	lineNum += 1
	if line[0] == '!':
	    continue

	# field 1: Database ID (RGD or UniProtKB)
        # field 2: RGD ID or UniProtKB ID
        # field 3: Symbol
        # field 4: Qualifier value
        # field 5: GO ID
        # field 6: RGD|PMID
        # field 7: Evidence code
        # field 8: Inferred From
        # field 14: Modification Date
        # field 15: Assigned By

	tokens = string.split(line[:-1], '\t')

        databaseID = tokens[0]
        ratID = tokens[0] + ':' + tokens[1]
        qualifierValue = tokens[3].lower()
        goID = tokens[4]
	references = tokens[5]
        evidenceCode = tokens[6]
        inferredFrom = tokens[7]
        modDate = tokens[13]
        assignedBy = tokens[14]
        note = ''
        properties = ''

	# if database is not RGD, then skip
	if databaseID != 'RGD' and databaseID != 'UniProtKB':
	    reasonCodeFile.write(str(lineNum) + '\tNON_RGD_UNIPROTKB\t\t' + line[:-1] + '\t\n')
	    continue

	# if goID is in goID list then skip
	if goID in excludedList:
	    reasonCodeFile.write(str(lineNum) + '\tEXCL_GO\t\t' + line[:-1] + '\t\n')
	    continue

	# if not in evidence list, then skip
	if evidenceCode not in evidenceCodeList:
	    reasonCodeFile.write(str(lineNum) + '\tEXCL_EVID\t\t' + line[:-1] + '\t\n')
	    continue

	# if assignedBy has a value = "MGI", then skip
	if assignedBy == 'MGI':
	    reasonCodeFile.write(str(lineNum) + '\tMGI\t\t' + line[:-1] + '\t\n')
	    continue

	# if no rat/mouse orthology by RGD ID or UniProtKB, then skip
	clusterID = ''
	if not ratIdDict.has_key(ratID):
	    reasonCodeFile.write(str(lineNum) + '\tNO_HOM\t\t' +line[:-1] + '\t\n')
	    continue
	else:
	    # cluster will be the same for all markers with this ratID
	    # get the cluster ID

	    mgiIDandClusterIDList = ratIdDict[ratID]
	    mgiIDList = []
	    for ids in mgiIDandClusterIDList:
		(mgiID, cID) = string.split(ids, '|')
		mgiIDList.append(mgiID)
		clusterID = cID

	# if qualifier has a value, then skip sc - incorrect, need to filter for 'NOT'
	# sc - current values:
	# Colocalizes_with
	# colocalizes_with
	# Contributes_to
	# contributes_to
	# NOT
	# Not
	# NOT|colocalizes_with
	# NOT|contributes_to

	if len(qualifierValue) > 0 and qualifierValue[:3] == 'not':
	    reasonCodeFile.write(str(lineNum) + '\tIS_RAT_NOT\t' + clusterID + '\t' + line[:-1] + '\t\n')
	    continue

	# if ratID/goID is in the "not" list, then skip
	skip = 0
	if isNotDict.has_key(ratID):
	    for n in isNotDict[ratID]:
		if goID == n:
		    skip = 1
	if skip == 1:
	    reasonCodeFile.write(str(lineNum) + '\tIS_MGI_NOT\t' + clusterID + '\t' + line[:-1] + '\t\n')
	    continue

        # attach reference accession id(s) to properties
        properties = ''

	if len(references) > 0:
            properties = properties + references
	else:
	    # if no references found, then skip
	    reasonCodeFile.write(str(lineNum) + '\tNO_PMID\t\t' + line[:-1] + '\t\n')
	    continue

	if len(inferredFrom) > 0:
	    properties = properties + '|' + inferredFrom

	new_inferredFrom = ratID

	# If not 1:1 and GO ID is Bio Process - skip
	if memberNumDict[clusterID] != 2 and goID in bioProcessList:
	    #print 'Not 1:1 and GO ID is Bio Process, skipping clusterID: %s %s' % (clusterID, line)
	    reasonCodeFile.write(str(lineNum) + '\tNON_1TO1_P\t' + clusterID + '\t' + line[:-1] + '\t\n')
	    continue

	# get the go IDs with NOT qualifiers in the input for this clusterID
	notIdList = []
	if clusterIDsWithNotDict.has_key(clusterID):
	    notIdList = clusterIDsWithNotDict[clusterID]
	    #print 'clusterIDsWithNotDict[%s]:  %s' % (clusterID, notIdList)
	    #print 'incoming goID: %s' % goID
	if goID in notIdList:
	    #print 'goID  has NOT qualifier in input, skipping clusterID: %s %s' % (clusterID, line)
	    reasonCodeFile.write(str(lineNum) + '\tNOT_NO_TRANSFER\t' + clusterID + '\t' + line[:-1] + '\t\n')
	    continue

	# skip if an MGI annotation already exists 
	# for J:73065/GO id/ISO/inferredFrom
	# 
	skip = 0
	for mgiID in mgiIDList:
	    if infFromExistsDict.has_key(mgiID):
		for e in infFromExistsDict[mgiID]:
		    if goID == e['goID'] and new_inferredFrom == e['inferredFrom']:
			#print mgiID, goID, new_inferredFrom
			skip = 1
        if skip == 1:
	    reasonCodeFile.write(str(lineNum) + '\tANNOT_IN_MGI_TO ' + mgiID + '\t' + clusterID + '\t' + line[:-1] + '\t\n')
	    continue

        #
        # For each mouse marker in the class, determine if new annotation
        # dup annotation, or already created annotation with additional properties
        #
        for mgiID in mgiIDList:

	    # new annotloadLine sans modDate, note, properties
	    annotloadLine = annotLine % \
		(goID, mgiID, jnumID, new_evidenceCode, new_inferredFrom, qualifierValue, editor)
	    
	    # this annotation not yet in the dictionary
	    if not annotToWriteDict.has_key(annotloadLine):
		annotToWriteDict[annotloadLine] = [modDate + '\t\t\t' + propertyPrefix + properties]
		reasonCodeFile.write(str(lineNum) + '\tCREATE_ANNOT\t' + clusterID + '\t' + line) 

	    # this annotation and properties in the dictionary and so exact dup
	    elif annotToWriteDict.has_key(annotloadLine) and propertyPrefix + properties in annotToWriteDict[annotloadLine]:
		reasonCodeFile.write(str(lineNum) + '\tDUP_IN_INPUT\t' + clusterID + '\t' + line) 
	
	    # this annotation in dictionary, add additional properties
	    else:
		annotToWriteDict[annotloadLine].append(propertyPrefix + properties)
		reasonCodeFile.write(str(lineNum) + '\tCREATE_ANNOT_COL\t' + clusterID + '\t' + line) 

    #
    # now write to annotload file
    #
    for line in annotToWriteDict.keys():
	#get the list of properties
	pList = annotToWriteDict[line]
        line = line  + string.join(pList, '&===&') + '\n'
	annotFile.write(line)


#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Closes files
# Throws: Nothing
#
def closeFiles():

    inFile.close()
    annotFile.close()
    reasonCodeFile.close()

#
# main
#

initialize()
preprocess()
reinitialize()
readGAF()

closeFiles()
