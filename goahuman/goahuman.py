'''
#
# goahuman.py
#
#	See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#	${PROTEIN_GAF}      the GAF file
#	${ISOFORM_GAF}      the GAF file
#
#       The GAF 2.2 file contains:
#               1  DB             
#               2  DB Object ID    
#               3  DB Object Symbol
#               4  Qualifier      
#               5  GO ID             
#               6  DB:Reference (|DB:Reference)
#               7  Evidence Code              
#               8  With (or) From            
#               9  Aspect                   
#               10 DB Object Name          
#               11 DB Object Synonym (|Synonym) 
#               12 DB Object Type              
#               13 Taxon(|taxon)              
#               14 Date                      
#               15 Assigned By              
#               16 Annotation Extension    
#               17 Gene Product Form ID   
#
# Outputs:
#
#       ${INFILE_NAME}          the file that will be used to load the annotations
#       ${INFILE_NAME_ERROR}    errors
#
# 	The annotation loader format has the following columns:
#
#	A tab-delimited file in the format:
#		1  Accession ID of Vocabulary Term being Annotated to
#		2  ID of MGI Object being Annotated (ex. MGI ID)
#		3  J: (J:#####)
#		4  Evidence Code Abbreviation (max length 5)
#		5  Inferred From 
#		6  Qualifier 
#		7  Editor (max length 30)
#		8  Date (MM/DD/YYYY)
#		9  Notes 
#		10 Logical DB Name of Object (leave null)
#		11 Properties
#
# Usage:
#       goahuman.py
#
# History:
#
# lec   01/13/2014
#       - TR11570/11571/qualifier contains "_" in both input and MGI
#
# sc	02/2013 - N2MO/TR6519 - updated go use MRK_Cluster* tables with new rules
#
# lec	04/23/2012
#	- TR11041/add GO:0005488 to excludedList
#
# lec	11/09/2010
#	- TR10445/marker type 'gene' (1) only
#
# lec   10/06/2010
#       - created TR10393
#
'''

import sys
import os
import db

# GAF file from the dataloads directory
inFileName = None
# GAF file pointer
inFile = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# error fromatted file
errorFileName = None
errorFile = None

# list of evidence codes that are loaded into MGI
evidenceCodeList = ['IDA', 'IPI', 'IGI', 'IMP', 'EXP']

# list of GO ids that are skipped
excludedList = ['GO:0005515', 'GO:0005488']

# goa/human IDs that contain mouse orthologs by UniProt ID
# {goaID:[mouse MGI ID, ...], ...}
goaIdDict = {}

#  mouse annotations that contain a "NOT" qualifier
# {goaID: [GoID,...], ...}
isNotDict = {}

# Dict of marker/go id/inferredFrom for J:73065 from the database
# value is db.sql result set
# {mouse mgiID: [{'goID':goID, 'accID':mouse MGI ID, 'inferredFrom':evidInfFrom, ...}, ...]
goaExistsDict = {}

# Dict of number of members by class
# {clusterId:numMembers, ...}
memberNumDict = {}

# list of all Biological Process GO Ids
# These are not transfered when no 1:1
bioProcessList = []

# cluster IDs mapped to goa NOT GO IDs 
clusterIdsWithNotDict = {}

#
# Purpose: Create lookup of MGI clusters with human NOT annotations
#
def preprocess(inFile):
    global clusterIdsWithNotDict

    for line in inFile.readlines():
        if line[0] == '!':
            continue

        tokens = str.split(line[:-1], '\t')

        databaseID = tokens[0]
        goaID = tokens[1]
        symbol = tokens[2]
        qualifier = tokens[3]
        goID = tokens[4]
        references = tokens[5]
        evidenceCode = tokens[6]
        inferredFrom = tokens[7]
        modDate = tokens[13]
        assignedBy = tokens[14]
        note = ''
        properties = ''
        clusterId = 0

        # if goa/mouse orthology by UniProt ID get cluster ID
        if goaID in goaIdDict:
            mgiIDandClusterIDList = goaIdDict[goaID]
            # cluster will be the same for all markers with this goaID
            for ids in mgiIDandClusterIDList:
                (mgiID, cID) = str.split(ids, '|')
                clusterId = int(cID)

        #
        # if at least one cluster member has a NOT, 
        # then *all* of the cluster members will be added to the clusterIdsWithNotDict
        # and will be reported as in the NOT_NO_TRANSFER
        # example:  cluster Q14186/TFDP1/does not have NOT, TFDP3/has a NOT
        #
        if len(qualifier) > 0 and qualifier[:3] == 'NOT':
            #if clusterId == 45295081:
            #    print('found qualifier NOT')
            #    print('cluster: ' + str(clusterId))
            #    print('qualifier: ' + str(qualifier))
            #    print(tokens)
            if clusterId not in clusterIdsWithNotDict:
                clusterIdsWithNotDict[clusterId] = []
            clusterIdsWithNotDict[clusterId].append(goID)

    inFile.close()

    return 0

#
# Purpose:  Open and copy files. Create lookups
#
def initialize():

    global annotFileName, annotFile
    global errorFileName, errorFile
    global goaIdDict, isNotDict, goaExistsDict, bioProcessList, memberNumDict

    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']

    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')

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
    # select mouse and human cluster members from all clusters with both
    # and get all human uniprot ids and mouse mgi ids
    #
    # load lookups:
    # 1. number of members by class ID
    # 2. MGI cluster ID and mouse gene MGI IDs by uniprot (goa) ID
    # 3. MGI NOT annotation lookup
    # 4. MGI GO annotations to J:73065
    #

    db.sql('''select cm.*, m._Organism_key
        into temp mouse
        from MRK_Cluster c, MRK_ClusterMember cm, MRK_Marker m
        where c._ClusterType_key = 9272150
        and c._ClusterSource_key = 75885739
        and c._Cluster_key = cm._Cluster_key
        and cm._Marker_key = m._Marker_key
        and m._Organism_key = 1
        and m._Marker_Type_key in (1,7,10)
        and lower(m.symbol) not  like 'gm%'
        and lower(m.name) not like '%predicted%' ''', None)

    db.sql('create index m_idx1 on mouse(_Cluster_key)', None)

    db.sql('''select cm.*, m._Organism_key
        into temp human
        from MRK_Cluster c, MRK_ClusterMember cm, MRK_Marker m
        where c._ClusterType_key = 9272150
        and c._ClusterSource_key = 75885739
        and c._Cluster_key = cm._Cluster_key
        and cm._Marker_key = m._Marker_key
        and m._Organism_key = 2
        and m._Marker_Type_key in (1,7,10)
        ''', None)

    db.sql('create index h_idx1 on human(_Cluster_key)', None)

    db.sql('''select m.*
        into temp mouseHuman
        from mouse m, human h
        where m._Cluster_key = h._Cluster_key
        UNION
        select h.*
        from mouse m,human h
        where m._Cluster_key = h._Cluster_key''', None)

    # get human uniprot ids and mouse marker MGI IDs
    db.sql('''select distinct h2._Cluster_key, h2._Marker_key, a1.accID as goaID, a2.accID as mouseID
        into temp goa
        from mouseHuman h1, mouseHuman h2, ACC_Accession a1, ACC_Accession a2
        where h1._Organism_key = 2
        and h1._Cluster_key = h2._Cluster_key
        and h2._Organism_key = 1
        and h1._Marker_key = a1._Object_key
        and a1._MGIType_key = 2
        and a1._LogicalDB_key = 13
        and a1.preferred = 1
        and h2._Marker_key = a2._Object_key
        and a2._MGIType_key = 2
        and a2._LogicalDB_key = 1
        and a2.preferred = 1''', None)

    db.sql('create index goa_idx1 on goa(_Marker_key)', None)

    # Load the number of members by class lookup
    results = db.sql('select * from mouseHuman order by _Cluster_key' , 'auto')
    for r in results:
        clusterId = r['_Cluster_key']
        if clusterId not in memberNumDict:
            memberNumDict[clusterId] = 0
        memberNumDict[clusterId] += 1

    results = db.sql('select * from goa', 'auto')
    for r in results:
        key = r['goaID']
        mouseID = r['mouseID']
        clusterId = r['_Cluster_key']
        value = '%s|%s' % (mouseID, clusterId)
        if key not in goaIdDict:
            goaIdDict[key] = []
        goaIdDict[key].append(value)

    # create MGI mouse NOT lookup
    results = db.sql('''select distinct g.goaID, acc.accID as goID
              from goa g join
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
        key = r['goaID']
        value = r['goID']
        if key not in isNotDict:
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
        if key not in goaExistsDict:
            goaExistsDict[key] = []
        goaExistsDict[key].append(value)

    return 0

#
# Purpose: Read GAF file and generate Annotation file
#
def readGAF(inFile):

    # reference used by this load
    jnumID = 'J:164563'

    # evidence code for all annotations
    new_evidenceCode = 'ISO'

    # annotation editor value
    editor = 'UniProtKB'

    # prefix for the single property type we create
    propertyPrefix = 'external ref&=&'

    # build a dictionary of lines to write to output file (annotload input file)
    # {annotLine sans modDate, note, properties: [list of properties], ...}
    annotToWriteDict = {}

    # annotation line sans modDate, note, properties
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t'

    # Use errorFile to report every line prepended with
    # 1. line number
    # 2. reason code
    # 3. cluster ID if applicable/TAB if not
    # 4. line 

    #try:
    lineNum = 0
    for line in inFile.readlines():
        lineNum += 1
        if line[0] == '!':
            continue

        tokens = str.split(line[:-1], '\t')

        databaseID = tokens[0]
        goaID = tokens[1]
        symbol = tokens[2]
        qualifier = tokens[3]
        goID = tokens[4]
        references = tokens[5]
        evidenceCode = tokens[6]
        inferredFrom = tokens[7]
        modDate = tokens[13]
        assignedBy = tokens[14]
        note = ''
        properties = ''

        # if database is not GOA, then skip
        if databaseID != 'UniProtKB':
            errorFile.write(str(lineNum) + '\tNON_UPKB\t\t' + line[:-1] + '\t\n')
            continue

        # if goID is in goID list then skip
        if goID in excludedList:
            errorFile.write(str(lineNum) + '\tEXCL_GO\t\t' + line[:-1] + '\t\n')
            continue

        # if not in evidence list, then skip
        if evidenceCode not in evidenceCodeList:
            errorFile.write(str(lineNum) + '\tEXCL_EVID\t\t' + line[:-1] + '\t\n')
            continue

        # if assignedBy has a value = "MGI", then skip
        if assignedBy == 'MGI':
            errorFile.write(str(lineNum) + '\tMGI\t\t' + line[:-1] + '\t\n')
            continue

        # if no goa/mouse orthology by UniProt ID, then skip
        clusterId = 0
        if goaID not in goaIdDict:
            errorFile.write(str(lineNum) + '\tNO_HOM\t\t' +line[:-1] + '\t\n')
            continue

        #
        # cluster will be the same for all markers with this goaID
        # get the cluster ID
        #
        mgiIDandClusterIDList = goaIdDict[goaID]
        mgiIDList = []
        for ids in mgiIDandClusterIDList:
            (mgiID, cID) = str.split(ids, '|')
            mgiIDList.append(mgiID)
            clusterId = int(cID)

        # if qualifier has a "NOT" value, then skip
        if len(qualifier) > 0 and qualifier[:3] == 'NOT':
            errorFile.write(str(lineNum) + '\tIS_GOA_NOT\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        # if goaID/goID is in the "not" list, then skip
        skip = 0
        if goaID in isNotDict:
            for n in isNotDict[goaID]:
                if goID == n:
                    skip = 1
        if skip == 1:
            errorFile.write(str(lineNum) + '\tIS_MGI_NOT\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        # attach reference accession ids to properties
        properties = ''
        if len(references) > 0:
            properties = properties + references

        # if no references found, then skip
        else:
            errorFile.write(str(lineNum) + '\tNO_REFERENCE\t\t' + line[:-1] + '\t\n')
            continue

        if len(inferredFrom) > 0:
            properties = properties + '|' + inferredFrom

        new_inferredFrom = databaseID + ':' + goaID

        if clusterId not in memberNumDict:
            errorFile.write(str(lineNum) + '\tNO_MEMBER\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        # If not 1:1 and GO ID is Bio Process - skip
        if memberNumDict[clusterId] != 2 and goID in bioProcessList:
            errorFile.write(str(lineNum) + '\tNON_1TO1_P\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        # get the go IDs with NOT qualifiers in the input for this clusterId
        notIdList = []
        if clusterId in clusterIdsWithNotDict:
            notIdList = clusterIdsWithNotDict[clusterId]
        if goID in notIdList:
            errorFile.write(str(lineNum) + '\tNOT_NO_TRANSFER\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        # skip if an MGI annotation for
        # for J:73065/GO id/ISO/inferredFrom exists
        # 
        skip = 0
        for mgiID in mgiIDList:
            if mgiID in goaExistsDict:
                for e in goaExistsDict[mgiID]:
                    if goID == e['goID'] and new_inferredFrom == e['inferredFrom']:
                        skip = 1
        if skip == 1:
            errorFile.write(str(lineNum) + '\tANNOT_IN_MGI_TO ' + mgiID + '\t' + str(clusterId) + '\t' + line[:-1] + '\t\n')
            continue

        #
        # if column 4 is not None and 
        #       column 4 is not in('NOT', 'colocalizes_with', 'NOT|colocalizes_with', 'contributes_to', 'NOT|contributes_to')
        #       then
        #
        #       if column 4 = NOT|$ ($=string) 
        #               then property = 'go_qualfier' value = 'NOT' + value
        #       else 
        #               then property = 'go_qualfier' value = + value
        #

        if qualifier != '' and qualifier != None \
                and qualifier not in ('NOT', 'colocalizes_with', 'NOT|colocalizes_with', 'contributes_to', 'NOT|contributes_to'):

            if qualifier.startswith('NOT|'):
                qtoken = qualifier.split('|')
                qualifier = 'NOT'
                if len(properties) > 0:
                    properties = properties + '&==&'
                properties += 'go_qualifier&=&' + qtoken[1]
            else:
                if len(properties) > 0:
                    properties = properties + '&==&'
                properties += 'go_qualifier&=&' + qualifier
                qualifier = ''

        #
        # For each mouse marker in the class, determine if new annotation
        # dup annotation, or already created annotation with additional properties
        #
        for mgiID in mgiIDList:

            # new annotloadLine sans modDate, note, properties
            annotloadLine = annotLine % \
                (goID, mgiID, jnumID, new_evidenceCode, new_inferredFrom, qualifier, editor)

            # this annotation not yet in the dictionary
            if annotloadLine not in annotToWriteDict:
                annotToWriteDict[annotloadLine] = [modDate + '\t\t\t' + propertyPrefix + properties]
                errorFile.write(str(lineNum) + '\tCREATE_ANNOT\t' + str(clusterId) + '\t' + line) 

            # this annotation and properties in the dictionary and so exact dup
            elif annotloadLine in annotToWriteDict:
                errorFile.write(str(lineNum) + '\tDUP_IN_INPUT\t' + str(clusterId) + '\t' + line)

            # this annotation in dictionary, add additional properties 
            else:
                annotToWriteDict[annotloadLine].append(propertyPrefix + properties)
                errorFile.write(str(lineNum) + '\tCREATE_ANNOT_COL\t' + str(clusterId) + '\t' + line) 

    #
    # now write to annotload file
    #
    for line in list(annotToWriteDict.keys()):
        #get the list of properties
        pList = annotToWriteDict[line]
        line = line  + str.join('&===&', pList) + '\n'
        annotFile.write(line)

    inFile.close()

    return 0

#
# Purpose: Close files
#
def closeFiles():

    annotFile.close()
    errorFile.close()
    return 0

#
# main
#

if initialize() != 0:
    sys.exit(1)

for inFileName in (os.environ['PROTEIN_GAF'], \
        os.environ['ISOFORM_GAF']):

    inFile = open(inFileName, 'r')

    if preprocess(inFile) != 0:
        sys.exit(1)

    # reopen file
    inFile = open(inFileName, 'r')

    if readGAF(inFile) != 0:
        sys.exit(1)

closeFiles()
sys.exit(0)
