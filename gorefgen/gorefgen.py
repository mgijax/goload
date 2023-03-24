'''
#
# gorefgen.py
#
#	See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#	${INFILE_NAME_GAF}	the GAF file in the input directory
#	${JNUMBER}		the J number to use for the annotation load
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
#	${INFILE_NAME}	the file that will be used to load the annotations
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
# Report:
#	TR 9962
#
#	for each row in the GAF file (INFILE_NAME_GAF):
#
#	    field 6 (DB:Reference(s)) = PMID:21873635
#	    field 8 (With/Inferred From) contains PANTHER ids
#
#	    note that the annotation loader checks for duplciates
#	    (mgiID, goID, evidence code, jnumID)
#
#           write the record to the annotation file (INFILE_NAME)
#    
# Usage:
#       gorefgen.py
#
# History:
#
# lec	08/13/2018
#	- TR12918/new PAINT input file
#
# lec	01/14/2014
#	- TR11570/11571/qualifier contains "_" in both input and MGI
#
# lec	09/06/2011
#	- TR 10339/added new evidence codes/added evidenceCodeList
#
# lec	02/21/2011
#	- TR 10603/marker type 'gene' only (markerList)
#
# lec	01/11/2011
#	- add IAS (TR10339)
#
# lec	11/23/2010
#	- re-open TR to exclude 'not' qualifiers
#
# lec	09/21/2010
#	- re-opened TR to add 'qualifier' to the annotation file
#	  this field was not included in the original TR
#
# lec   03/02/2010
#       - created TR9962
#
'''

import sys 
import os
import db

# GAF file input file
inFileName = None

# GAF file pointer
inFile = None

# LOG_CUR file
logCurName = None
logCur = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# error formatted file
errorFileName = None
# error file pointer
errorFile = None

# j number for annotation load
jnumID = None

# markerList = list of all markers of type 'gene'
# value = accession id
markerList = []

# evidnece codes for GO annotations (_Vocab_key = 3)
evidenceCodeList = {}

#
# Purpose: Initialization
#
def initialize():

    global inFileName, inFile
    global logCurFileName, logCurFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global jnumID
    global markerList
    global evidenceCodeList

    #
    # open files
    #

    inFileName =  os.environ['INFILE_NAME_GAF']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']
    logCurFileName = os.environ['LOG_CUR']
    jnumID = os.environ['JNUMBER']

    try:
        inFile = open(inFileName, 'r')
    except:
        print('Cannot open input file: ' + inFileName)
        return 1

    # this file is created/opened by wrapper
    try:
        logCurFile = open(logCurFileName, 'a+')
    except:
        print('Cannot open log curator file for writing: ' + logCurFileName)
        return 1

    try:
        annotFile = open(annotFileName, 'w')
    except:
        print('Cannot open annotation file for writing: ' + annotFileName)
        return 1

    try:
        errorFile = open(errorFileName, 'w')
    except:
        print('Cannot open error file for writing: ' + errorFileName)
        return 1

    #
    # list of markers type 'gene', status in (1,3) (no withdrawns)
    #
    results = db.sql('''select a.accID
              from MRK_Marker m, ACC_Accession a
              where m._Marker_Type_key in (1,7,10)
              and m._Marker_key = a._Object_key
              and m._Marker_Status_key in (1,3)
              and a._MGIType_key = 2
              and a._LogicalDB_key = 1
          ''', 'auto')

    for r in results:
        value = r['accID']
        markerList.append(value)

    #
    # list of evidence codes
    #
    results = db.sql('select _Term_key, abbreviation from VOC_Term where _Vocab_key = 3', 'auto')
    for r in results:
        evidenceCodeList[r['abbreviation']] = r['_Term_key']

    return 0

#
# Purpose: Initialization
#
def readGAF():

    #
    #	for each row in the GAF file (INFILE_NAME_GAF):
    #
    #           write the record to the annotation file (INFILE_NAME)
    #

    # see annotload/annotload.py for format
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t\t%s\n' 

    for line in inFile.readlines():

        if line[0] == '!':
            continue

        tokens = str.split(line[:-1],'\t')

        databaseID = tokens[0]
        mgiID = tokens[1]
        qualifier = tokens[3]
        goID = tokens[4]
        dbRef = tokens[5]
        evidenceCode = tokens[6]
        modDate = tokens[13]
        createdBy = tokens[14]

        if dbRef not in ['PMID:21873635']:
            continue
        
        if mgiID.find('MGI:') < 0:
            continue

        if mgiID not in markerList:
            logCurFile.write('Withdrawn or Non-Gene Marker\n' + line + '\n')
            continue

        if evidenceCode not in evidenceCodeList:
            logCurFile.write('Invalid Evidence\n' + line + '\n')
            continue

        #
        # only interested in: PANTHER:
        #
        allInferredFrom = tokens[7].split('|')
        inferredFrom = []
        for i in allInferredFrom:
            if i.find('PANTHER:') >= 0:
                inferredFrom.append(i)

        #
        # start : column 11 (properties)
        #
        
        #
        # if column 4 is not None and 
        #       column 4 is not in('NOT', 'colocalizes_with', 'NOT|colocalizes_with', 'contributes_to', 'NOT|contributes_to')
        #       then
        #
        #       if column 4 = NOT|$ ($=string) 
        #               then property = 'go_qualfier' value = 'not' + value
        #       else 
        #               then property = 'go_qualfier' value = + value
        #

        mgiproperties = ''

        if qualifier != '' and qualifier != None and qualifier not in ('NOT', 'colocalizes_with', 'NOT|colocalizes_with', 'contributes_to', 'NOT|contributes_to'):
            if qualifier.startswith('NOT|'):
                qtoken = qualifier.split('|')
                qualifier = 'NOT'
                if len(mgiproperties) > 0:
                    mgiproperties = mgiproperties + '&==&'
                mgiproperties += 'go_qualifier&=&' + qtoken[1]
            else:
                if len(mgiproperties) > 0:
                    mgiproperties = mgiproperties + '&==&'
                mgiproperties += 'go_qualifier&=&' + qualifier
                qualifier = ''

        #
        # end : column 11
        #

        # write data to the annotation file
        # note that the annotation load will qc duplicate annotations itself
        # (mgiID, goID, evidenceCode, jnumID)

        annotFile.write(annotLine % (goID, mgiID, jnumID, evidenceCode, '|'.join(inferredFrom), qualifier, createdBy, modDate, mgiproperties))

    return 0

#
# Purpose: Close files
#
def closeFiles():

    inFile.close()
    annotFile.close()
    errorFile.close()

    # this file is opened/closed by wrapper
    #logCur.close()

    return 0

#
# main
#

if initialize() != 0:
    sys.exit(1)

if readGAF() != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)
