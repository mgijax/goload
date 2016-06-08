#!/usr/local/bin/python

'''
#
# goacfp.py
#
# Inputs:
#
#       ${INFILE_NAME_GAF}	the GO GAF file in the downloads directory
#	${INFILE_NAME}		the GO GAF file in the input directory (a copy of GOCGAF)
#	${INPUTDIR}		the input directory
#
# 	The GAF file contains:
#
#		field 1: Database ID (MGI)
#		field 2: MGI ID (MGI:###)
#		field 4: Qualifier
#		field 5: GO ID
#		field 6: MGI:MGI:#### (reference)
#	        field 7: Evidence code
#	        field 8: With (inferred from)
#		field 14: Modification Date
#
# Outputs:
#
#	${INFILE_NAME}	        the file that will be used to load the annotations
#	${INFILE_NAME_ERROR}	error file for reporting invalid references
#
# 	The annotation loader format has the following columns:
#
#	A tab-delimited file in the format:
#		field 1: GO ID 		GAF field 5
#		field 2: MGI ID 	GAF field 2
#		field 3: J:157226
#		field 4: Evidence Code 	GAF field 7 (IC)
#		field 5: Inferred From	GAF field 8
#		field 6: Qualifier 	GAF field 4
#		field 7: Editor 	GAF field 15
#		field 8: Date 		GAF field 14
#		field 9: none
#
# Report:
#	TR 10011
#
#	Copy the GAF download file (INFILE_NAME_GAF) into the input directory (INPUTDIR)
#
#       Create a lookup of all MGI ids/PubMed ids/J: (mgiRefLookup)
#
#	for each row in the GAF file (INFILE_NAME_GAF):
#
#           if the reference does not exist in MGI (using mgiRefLookup)
#                   write the record to the error file (INFILE_NAME_ERROR)
#                   skip the row
#
#	    note that the annotation loader checks for duplciates
#	    (mgiID, goID, evidence code, jnumID)
#
#           write the record to the annotation file (INFILE_NAME)
#    
# Usage:
#       goacfp.py
#
# History:
#
# lec   01/14/2014
#	- TR11570/11571/qualifier contains "_" in both input and MGI
#
# lec   03/02/2010
#       - created
#
'''

import sys 
import os
import string
import db

db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

# GOC GAF file from the dataloads directory
inFileName = None
# GOC GAF file pointer
inFile = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# GAF references that are PMID/but not in MGI
# or are not PMID references at all
# or duplicates (existing annotations)
errorFileName = None
# error file pointer
errorFile = None

# created-by name for these annotations
createdBy = "GOC"

# lookup file of mgi ids or pubmed ids -> J:
# mgi id:jnum id
# pubmed id:jnum id
mgiRefLookup = {}

#
# Purpose: Initialization
# Returns: 1 if file does not exist or is not readable, else 0
# Assumes: Nothing
# Effects: Copies & opens files
# Throws: Nothing
#
def initialize():

    global inFileName, inFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global mgiRefLookup

    #
    # open files
    #

    inFileName = os.environ['INFILE_NAME_GAF']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']

    inFile = open(inFileName, 'r')
    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')

    #
    # lookup file of mgi ids or pubmed ids -> J:
    # mgi id:jnum id
    # pubmed id:jnum id
    #

    results = db.sql('''select mgiID, pubmedID, jnumID 
			from BIB_Citation_Cache 
		     ''', 'auto')
    for r in results:
	mgiRefLookup[r['mgiID']] = r['jnumID']

	if r['pubmedID'] != '':
	    mgiRefLookup[r['pubmedID']] = r['jnumID']

#
# Purpose: Read GAF file and generate Annotation file
# Returns: 1 if file can be read/processed correctly, else 0
# Assumes: Nothing
# Effects: Reads input file and creates output annotation file
# Throws: Nothing
#
def readGAF():

    #
    #	for each row in the GAF file (INFILE_NAME_GAF):
    #
    #           if the reference does not exist in MGI (using mgiRefLookup)
    #                   write the record to the error file (INFILE_NAME_ERROR)
    #                   skip the row
    #
    #           write the record to the annotation file (INFILE_NAME)
    #

    # see annotload/annotload.py for format
    annotLine = '%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t\n' 

    for line in inFile.readlines():

	if line[0] == '!':
	    continue

	tokens = string.split(line[:-1], '\t')

	#
	# field 1: Database ID (MGI)
	# field 2: MGI ID (MGI:###)
	# field 4: Qualifier
	# field 5: GO ID
	# field 6: MGI:MGI:#### (reference)
	# field 7: Evidence code
	# field 8: With (inferred from)
	# field 14: Modification Date
	#

	databaseID = tokens[0]
	mgiID = tokens[1]
	qualifier = tokens[3]
	goID = tokens[4]
	references = string.split(tokens[5], '|')
	evidenceCode = tokens[6]
	inferredFrom = string.replace(tokens[7], 'MGI:MGI:', 'MGI:')
	modDate = tokens[13]

	# don't use this field
	#createdBy = tokens[14]

	jnumIDFound = 0

	# translate references (MGI/PMID) to J numbers (J:)
	# use the first J: match that we find
	for r in references:

	    refID = string.replace(r, 'MGI:MGI:', 'MGI:')
	    refID = string.replace(refID, 'PMID:', '')

	    if mgiRefLookup.has_key(refID):
		jnumID = mgiRefLookup[refID]
		jnumIDFound = 1
		 
	# if reference does not exist...skip it

	if not jnumIDFound:
	    errorFile.write('Invalid Refeference:  %s, %s\n' % (mgiID, references))
	    continue

	# write data to the annotation file
	# note that the annotation load will qc duplicate annotations itself
	# (mgiID, goID, evidenceCode, jnumID)

	annotFile.write(annotLine % (goID, mgiID, jnumID, evidenceCode, inferredFrom, createdBy, modDate))

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
    errorFile.close()

#
# main
#

initialize()
readGAF()

closeFiles()

