#!/usr/local/bin/python

'''
#
# goamousenoctua.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#       ${INFILE_NAME_GPAD}      the GPAD file
#
#       The GPAD file contains:
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
import db
import ecolib

db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

# GPAD file from the dataloads directory
inFileName = None
# GPAD file pointer
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

# lookup file of Evidence Code Ontology (_vocab_key = 111)
# to GO Evidence Code (_vocab_key = 3)
ecoLookupByEco = {}
ecoLookupByEvidence = {}

# uberson stuff

# uberson formatted file
uberonFileName = None
# uberson file pointer
uberonFile = None

# uberson text formatted file
uberonTextFileName = None
# uberson text file pointer
uberonTextFile = None

uberonLookup = {}

UBERON_MAPPING_MULTIPLES_ERROR = "uberon id has > 1 emapa : %s\t%s"
UBERON_MAPPING_MISSING_ERROR = "uberon id not found or missing emapa id: %s" 
# end uberson stuff

#
# Purpose: Initialization
#
def initialize():

    global inFileName, inFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global mgiRefLookup
    global ecoLookupByEco
    global ecoLookupByEvidence
    global uberonLookup
    global uberonFileName, uberonFile
    global uberonTextFileName, uberonTextFile

    #
    # open files
    #

    inFileName = os.environ['INFILE_NAME_GPAD']
    uberonFileName = os.environ['UBERONFILE']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']
    uberonTextFileName = os.environ['UBERONTEXTFILE']

    inFile = open(inFileName, 'r')
    uberonFile = open(uberonFileName, 'r')
    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')
    uberonTextFile = open(uberonTextFileName, 'w')

    #
    # lookup file of mgi ids or pubmed ids -> J:
    # mgi id:jnum id
    # pubmed id:jnum id
    #

    print 'reading mgi id/pubmed id -> J: translation...'

    results = db.sql('select mgiID, pubmedID, jnumID from BIB_Citation_Cache', 'auto')
    for r in results:
	mgiRefLookup[r['mgiID']] = r['jnumID']
	if r['pubmedID'] != '':
	    mgiRefLookup[r['pubmedID']] = r['jnumID']

    # lookup file of Evidence Code Ontology using ecolib.py library

    print 'reading eco -> go evidence translation...'
    ecoLookupByEco, ecoLookupByEvidence = ecolib.processECO()

    #
    # read/store UBERON-to-EMAPA info
    #

    print 'reading uberon -> emapa translation file...'

    uberonIdValue = 'id: UBERON:'
    emapaXrefValue = 'xref: EMAPA:'

    for line in uberonFile.readlines():
        # find [Term]
        # find xref: EMAPA:
        if line[:11] == uberonIdValue:
            uberonId = line[4:-1]
        elif line[:12] == emapaXrefValue:
            emapaId = line[6:-1]
            if uberonId not in uberonLookup:
                uberonLookup[uberonId] = []
            uberonLookup[uberonId].append(emapaId)
        else:
            continue

    for u in uberonLookup:
        uberonTextFile.write(u + '\n')

    return

#
# Purpose: Converts extensions ids (column 11)
#
def convertExtensionsIds(extensions, uberonLookup={}):
    #
    # Converts extensions ids (column 11):
    #
    # 	UBERON: -> EMAPA:, uberonLookup
    # 
    #   Returns converted extensions
    #   Returns list of error messages []
    #

    uberonPrefix = 'UBERON:'
    
    errors = []
    print extensions

    pStart = extensions.split('(')
    for p in pStart:

	pEnd = p.split(')')

	for e in pEnd:

	    # found uberon id
	    if e.find(uberonPrefix) >= 0:
		if e in uberonLookup:
		    u = uberonLookup[e]
		    # found > 1 emapa
		    if len(u) > 1:
			errors.append(UBERON_MAPPING_MULTIPLES_ERROR % (e, str(u)))
		    # replace UBERON id with EMAPA id
		    else:
			extensions = extensions.replace(e, u[0])
		# did not find uberon id
		else:
		    errors.append(UBERON_MAPPING_MISSING_ERROR % (e))

	    # else, do nothing

    return extensions, errors

#
# Purpose: Read GPAD file and generate Annotation file
#
def readGPAD():

    #
    #	for each row in the GPAD file (INFILE_NAME_GPAD):
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

    print 'reading GPAD...'

    for line in inFile.readlines():

	if line[0] == '!':
	    continue

	line = line[:-1]
	tokens = line.split('\t')

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

        #
        # skip if the GO id is a root term:  GO:0003674, GO:0008150, GO:0005575
        #

        if goID in ('GO:0003674','GO:0008150', 'GO:0005575'):
            errorFile.write('Root Id is used : %s\n%s\n****\n' % (goID, line))
            continue

	#
	# skip if not MGI:
	# only loading genes at the moment...
	#

	if not dbobjectID.find('MGI:') >= 0:
	    errorFile.write('dbobjectID is not an MGI:xxxx id : %s\n%s\n****\n' % (dbobjectID, line))
	    continue

	# translate references (MGI/PMID) to J numbers (J:)
	# use the first J: match that we find

	jnumIDFound = 0
	referencesTokens = references.split('|')
	for r in referencesTokens:

	    refID = r.replace('MGI:MGI:', 'MGI:')
	    refID = refID.replace('PMID:', '')

	    if refID in mgiRefLookup:
		jnumID = mgiRefLookup[refID]
		jnumIDFound = 1
		 
	# if reference does not exist...skip it

	if not jnumIDFound:
	    errorFile.write('Invalid Refeference: %s\n%s\n****\n' % (references, line))
	    continue

	if evidenceCode in ecoLookupByEco:
	    goEvidenceCode = ecoLookupByEco[evidenceCode][0]
	else:
	    errorFile.write('Invalid ECO id : cannot find valid GO Evidence Code : %s\n%s\n****\n' % (evidenceCode, line))
	    continue

	# for testing old gpad
	#extensions = extensions.replace(evidenceCode,'')
	#properties = properties.replace(goEvidenceCode,'')

	#
	# "extensions" contain things like "occurs_in", "part_of", etc.
	# and are added to "properties" for forwarding to the annotation loader
	#
	if len(extensions) > 0:

	    # to translate uberon ids to emapa
	    extensions, errors = convertExtensionsIds(extensions, uberonLookup)
	    if errors:
	        for error in errors:
	            errorFile.write('%s\n%s\n****\n' % (error, line))

	    # re-format to use 'properties' format
	    # (which will then be re-formated tomgi-property format)
	    extensions = extensions.replace('(', '=')
	    extensions = extensions.replace(')', '')
	    extensions = extensions.replace(',', '|')
	    properties = extensions + '|' + properties

	#
	# for qualifier:
	#	a) store as 'null' in MGI-Qualifier field (see annotLine/field 3)
	#	b) append to 'properties' as:
	#		go_qualifier=part_of
	#		go_qualifier=enables
	#		go_qualifier=involved_in
	#
	if len(properties) > 0:
	    properties = properties + '|'
	properties = properties + 'go_qualifier=' + qualifier

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
	# (dbobjectID, goID, goEvidenceCode, jnumID)

	# temporary
	annotFile.write(annotLine % (goID, dbobjectID, jnumID, goEvidenceCode, inferredFrom, \
		createdBy, modDate, properties))

#
# Purpose: Close files
#
def closeFiles():

    inFile.close()
    uberonFile.close()
    annotFile.close()
    errorFile.close()
    uberonTextFile.close()

#
# main
#

initialize()
readGPAD()
closeFiles()

