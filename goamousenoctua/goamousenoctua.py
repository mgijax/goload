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
# gpi file
#
gpiFileName = None
gpiFile = None
gpiLookup = {}

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
    global uberonFileName, uberonFile, uberonLookup
    global uberonTextFileName, uberonTextFile
    global gpiFileName, gpiFile, gpiLookup

    #
    # open files
    #

    inFileName = os.environ['INFILE_NAME_GPAD']
    uberonFileName = os.environ['UBERONFILE']
    gpiFileName = os.environ['GPIFILE']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']
    uberonTextFileName = os.environ['UBERONTEXTFILE']

    inFile = open(inFileName, 'r')
    uberonFile = open(uberonFileName, 'r')
    gpiFile = open(gpiFileName, 'r')
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

    primaryEmapa = []
    results = db.sql('''select a.accID 
    		from ACC_Accession a, VOC_Term t
		where a._MGIType_key = 13
		and a.preferred = 1
		and a._Object_key = t._Term_key
		and t._Vocab_key = 90
		''', 'auto')
    for r in results:
        primaryEmapa.append(r['accID'])

    uberonIdValue = 'id: UBERON:'
    emapaXrefValue = 'xref: EMAPA:'

    for line in uberonFile.readlines():
        # find [Term]
        # find xref: EMAPA:
        if line[:11] == uberonIdValue:
            uberonId = line[4:-1]
        elif line[:12] == emapaXrefValue:
            emapaId = line[6:-1]
	    if emapaId not in primaryEmapa:
	        continue
            if uberonId not in uberonLookup:
                uberonLookup[uberonId] = []
            uberonLookup[uberonId].append(emapaId)
        else:
            continue

    for u in uberonLookup:
        uberonTextFile.write(u + '\n')

    #
    # read/store object-to-Marker info
    #

    print 'reading object -> marker translation using gpi file...'

    for line in gpiFile.readlines():
        if line[:1] == '!':
	    continue
        tokens = line[:-1].split('\t')
	if tokens[0] in ('PR', 'EMBL', 'ENSEMBL', 'RefSeq', 'VEGA'):
	    key = tokens[0] + ':' + tokens[1]
	    value = tokens[7].replace('MGI:MGI:', 'MGI:')
            if key not in gpiLookup:
                gpiLookup[key] = []
            gpiLookup[key].append(value)

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
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\tMGI\t%s\n' 

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

        if createdBy == 'GO_Noctua' and goID in ('GO:0003674','GO:0008150', 'GO:0005575'):
            errorFile.write('Root Id is used : %s\n%s\n****\n' % (goID, line))
            continue

        #
        # skip if the databaseID is not MGI or PR
        #

	if databaseID not in ('MGI', 'PR', 'EMBL', 'ENSEMBL', 'RefSeq', 'VEGA'):
            errorFile.write('column 1 is not valid: %s\n%s\n****\n' % (databaseID, line))
            continue

	#
	# if non-MGI object, then add as Marker annotation and use 'gene prodcut' as a property
	#

	if databaseID in ('PR', 'EMBL', 'ENSEMBL', 'RefSeq', 'VEGA'):
	    #print tokens
	    dbobjectID = databaseID + ':' + dbobjectID
	    properties = 'gene product=' + dbobjectID

	    if dbobjectID in gpiLookup:
	        dbobjectID = gpiLookup[dbobjectID][0]
            else:
	        errorFile.write('object is not in object lookup(gpi file): %s\n%s\n****\n' % (dbobjectID, line))
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
	    # (which will then be re-formated to mgi-property format)
	    extensions = extensions.replace('(', '=')
	    extensions = extensions.replace(')', '')
	    extensions = extensions.replace(',', '|')
	    if len(properties) > 0:
	        properties = extensions + '|' + properties
	    else:
	        properties = extensions

	#
	# for qualifier:
	#
	# if qualifier in ('part_of', 'enables', 'involves_in':
	#	a) store as annotload/column 11/Property
	#	b) append to 'properties' as:
	#		go_qualifier=part_of
	#		go_qualifier=enables
	#		go_qualifier=involved_in
	#
	# else:
	#	a) store as annotload/column 6/Qualifier
	#
	goqualifiers = []
	for g in qualifier.split('|'):
	    if g in ('part_of', 'enables', 'involved_in'):
	        if len(properties) > 0:
	            properties = properties + '|'
	    	properties = properties + 'go_qualifier=' + g
	    else:
	        goqualifiers.append(g)

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

	# if using mgd-generated GPAD to run a test, then set createdBy = 'GO_Noctua'
	# or else the createdBy in the input file will generate errors.
	createdBy = 'GO_Noctua'

	annotFile.write(annotLine % (goID, dbobjectID, jnumID, goEvidenceCode, inferredFrom, \
		'|'.join(goqualifiers), createdBy, modDate, properties))

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

