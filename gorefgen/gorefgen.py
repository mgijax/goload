#!/usr/local/bin/python

'''
#
# goarefgen.py
#
#	See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#	${INFILE_NAME_GAF}	the GAF file in the input directory
#	${JNUMBER}		the J number to use for the annotation load
#
# 	The GAF file contains:
#
# 		field 1: Database ID (MGI)
# 		field 2: MGI ID
#		field 5: GO ID
#		field 6: MGI:MGI:#### (reference) (ignore)
#	        field 7: Evidence code (always ISS)
#	        field 8: With (inferred from)
#		field 14: Modification Date
#		field 15: Assigned By
#
# Outputs:
#
#	${INFILE_NAME}	the file that will be used to load the annotations
#
# 	The annotation loader format has the following columns:
#
#	A tab-delimited file in the format:
#		field 1: GO ID 		GAF field 5
#		field 2: MGI ID 	GAF field 2
#		field 3: J:
#		field 4: Evidence Code 	GAF field 7 (IC)
#		field 5: Inferred From	GAF field 8
#		field 6: Qualifier 	GAF field 4
#		field 7: Editor 	GAF field 15
#		field 8: Date 		GAF field 14
#		field 9: none
#
# Report:
#	TR 9962
#
#	for each row in the GAF file (INFILE_NAME_GAF):
#
#	    skip if qualifier = "NOT"
#
#	    field 8 (With/Inferred From) contains:
#
#	 	PANTHER ids
#
#	    note that the annotation loader checks for duplciates
#	    (mgiID, goID, evidence code, jnumID)
#
#           write the record to the annotation file (INFILE_NAME)
#    
# Usage:
#       goarefgen.py
#
# History:
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
import string
import db

db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

# GAF file input file
inFileName = None

# GAF file pointer
inFile = None

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
    jnumID = os.environ['JNUMBER']

    try:
        inFile = open(inFileName, 'r')
    except:
	print 'Cannot open input file: ' + inFileName
	return 1

    try:
        annotFile = open(annotFileName, 'w')
    except:
	print 'Cannot open annotation file for writing: ' + annotFileName
	return 1

    try:
        errorFile = open(errorFileName, 'w')
    except:
	print 'Cannot open error file for writing: ' + errorFileName
	return 1

    #
    # list of markers type 'gene'
    #
    results = db.sql('''select a.accID
              from MRK_Marker m, ACC_Accession a
              where m._Marker_Type_key = 1
	      and m._Marker_key = a._Object_key
	      and a._MGIType_key = 2
	      and a._LogicalDB_key = 1
	      and a.preferred = 1
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
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\n' 

    for line in inFile.readlines():

        if line[0] == '!':
            continue

        tokens = string.split(line[:-1],'\t')

	#
        # field 1: Database ID (MGI)
        # field 2: MGI ids
        # field 4: Qualifier
        # field 5: GO ID
        # field 6: MGI:MGI:#### (reference) (ignore)
        # field 7: Evidence code (always ISS)
        # field 8: With (inferred from)
        # field 14: Modification Date
        # field 15: Assigned By
        #

	databaseID = tokens[0]
	mgiID = tokens[1]
	qualifier = tokens[3]
	goID = tokens[4]
	evidenceCode = tokens[6]
	modDate = tokens[13]
	createdBy = tokens[14]

	# inferred-from may contain '|' or ','
	allInferredFrom = tokens[7].split('\||,')

	#
	# skip if qualifier = "NOT"
	#

        if qualifier in ['NOT']:
	    continue

	#
	# skip if mgiID is not an MGI id
	#

        if mgiID.find('MGI:') < 0:
	    continue

	#
	# skip if mgiID is not of type 'gene'
	#

	if mgiID not in markerList:
	    continue

	#
	# skip if evidenceCode is not valid
	#

	if evidenceCode not in evidenceCodeList:
	    print 'Invalid Evidence Code:  ', evidenceCode
	    continue

	#
	# only interested in:
	#
	#	Panther IDs (PANTHER:PTHR24316_AN0)
	#

	inferredFrom = []
	for i in allInferredFrom:
            if i.find('PANTHER:') >= 0:
	        # split once more to remove the _A### stuff
		pthID = i.split('_')
                inferredFrom.append(pthID[0])

	#
	# TR10339/new evidence codes added/remove default 'ISS'
	# convert all evidence codes to ISS
	# (orignally: IMR, IRD, IAS -> ISS)
	#if evidenceCode in ('IMR', 'IRD', 'IAS'):
	#evidenceCode = 'ISS'
	#

	# write data to the annotation file
	# note that the annotation load will qc duplicate annotations itself
	# (mgiID, goID, evidenceCode, jnumID)

	annotFile.write(annotLine % (goID, mgiID, jnumID, evidenceCode, \
		   '|'.join(inferredFrom), qualifier, createdBy, modDate))

    return 0

#
# Purpose: Close files
#
def closeFiles():

    inFile.close()
    annotFile.close()
    errorFile.close()

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

