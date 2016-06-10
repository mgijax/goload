#!/usr/local/bin/python

'''
#
# goamousenoctua.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload_overview
#
# Inputs:
#
#       ${INFILE_NAME_GAF}      the GAF file
#
#       The GAF file contains:
#
#               field 1:  Database ID ('MGI')
#		field 2:  DB Object ID
#               field 3:  Qualifier
#               field 4:  GO ID
#               field 5:  References (PMIDs)
#               field 6:  Evidence code
#               field 7:  Inferred From  (With)
#		field 8 : Interacting taxon ID
#		field 9 : Date (yyymmdd)
#		field 10: Assigned By (GO_Noctua)
#		field 11: Annotation Extension
#		field 12: Annotation Properties
#
# Outputs/Report:
#
# 	The annotation loader format has the following columns:
#
#	A tab-delimited file in the format:
#		field 1: Accession ID of Vocabulary Term being Annotated to
#		field 2: ID of MGI Object being Annotated (ex. MGI ID)
#		field 3: J: (J:#####)
#		field 4: Evidence Code Abbreviation (max length 5)
#		field 5: Inferred From 
#		field 6: Qualifier 
#		field 7: Editor (max length 30)
#		field 8: Date (MM/DD/YYYY)
#		field 9: Notes 
#		field 10: Logical DB Name of Object (leave null)
#		field 11: Properties
#
# Usage:
#       goamousenoctua.py
#
# History:
#
# lec   06/09/2016
#       TR12345/load GO_Noctua GPAD file
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

# error formatted file
errorFileName = None
# error file pointer
errorFile = None

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

    # field 1:  Database ID ('MGI')
    # field 2:  DB Object ID
    # field 3:  Qualifier
    # field 4:  GO ID
    # field 5:  References (PMIDs)
    # field 6:  Evidence code
    # field 7:  Inferred From  (With)
    # field 8 : Interacting taxon ID
    # field 9 : Date (yyymmdd)
    # field 10: Assigned By (GO_Noctua)
    # field 11: Annotation Extension
    # field 12: Annotation Properties

    # see annotload/annotload.py for format
    # field 6:  Qualifier : null
    # field 9 : Notes : none
    # field 10: logicalDB : MGI
    annotLine = '%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t\tMGI\t%s\n' 

    for line in inFile.readlines():

	if line[0] == '!':
	    continue

	tokens = string.split(line[:-1], '\t')

        databaseID = tokens[0]		# should always be 'MGI'
	dbobjectID = tokens[1]
        qualifier = tokens[2]
        goID = tokens[3]
        references = tokens[4]
        evidenceCode = tokens[5]
        inferredFrom = tokens[6]
        taxID = tokens[7]
        modDate = tokens[8]
        createdBy = tokens[9]
        extensions = tokens[10]
        properties = tokens[11]

	jnumIDFound = 0

	# translate references (MGI/PMID) to J numbers (J:)
	# use the first J: match that we find
	referencesTokens = references.split('|')
	for r in referencesTokens:

	    refID = string.replace(r, 'MGI:MGI:', 'MGI:')
	    refID = string.replace(refID, 'PMID:', '')

	    if refID in mgiRefLookup:
		jnumID = mgiRefLookup[refID]
		jnumIDFound = 1
		 
	# if reference does not exist...skip it

	if not jnumIDFound:
	    errorFile.write('Invalid Refeference:  %s, %s\n' % (dbobjectID, references))
	    continue

	#
	# for qualifier:
	#	a) store as 'null' in MGI-Qualifier field (see annotLine/field 3)
	#	b) append to 'properties' as:
	#		go_qualifier=part_of
	#		go_qualifier=enables
	#		go_qualifier=involved_in
	#
	properties = properties + '|go_qualifier=' + qualifier

        # for evidence:
	#	a) store as translated ECO->MGI->Evidence Code field
	#	b) append to 'properties' as:
	#		evidence=ECO:xxxx
        #
	properties = properties + '|evidence=' + evidenceCode

        # re-format to mgi-property format
        #
        properties = properties.replace('=', '&=&')
        properties = properties.replace('|', '&==&')

	# write data to the annotation file
	# note that the annotation load will qc duplicate annotations itself
	# (dbobjectID, goID, evidenceCode, jnumID)

	# temporary
	evidenceCode = 'IDA'
	annotFile.write(annotLine % (goID, dbobjectID, jnumID, evidenceCode, inferredFrom, \
		createdBy, modDate, properties))

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

