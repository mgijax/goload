'''
#
# gomousenoctua.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#       ${MGIINFILE_NAME_GPAD}     the MGI GPAD file
#       ${PRINFILE_NAME_GPAD}      the PR GPAD file
#
#       The GPAD file contains:
#               field 1:  Database ID ('MGI')
#		field 2:  DB Object ID
#               field 3:  Qualifier
#               field 4:  GO ID
#               field 5:  References (PMIDs)
#               field 6:  Evidence code
#               field 7:  Inferred From  (With)
#		field 8 : Interacting taxon ID
#		field 9 : Date (yyymmdd)
#		field 10: Assigned By (NOCTUA_, MGI, other)
#		field 11: Annotation Extension
#		field 12: Annotation Properties
#
# Outputs/Report:
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
#       pubmed.error
#               file of unique PubMed IDs that are not in MGI
#
# Usage:
#       gomousenoctua.py
#
# History:
#
# lec	03/28/2018
#	TR12834/Noctua changes
#
# lec   06/09/2016
#       TR12345/load Noctua GPAD file
#
'''

import sys 
import os
import db
import reportlib

goloadpath = os.environ['GOLOAD'] + '/lib'
sys.path.insert(0, goloadpath)
import ecolib
import uberonlib

# GPAD files from the dataloads directory
mgiInFileName = None
prInFileName = None
# GPAD file pointer
mgiInFile = None
prInFile = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# error formatted file
errorFileName = None
# error file pointer
errorFile = None

# pubmed ids
pubmedErrorFile = None

# lookup file of mgi ids or pubmed ids -> J:
# mgi id:jnum id
# pubmed id:jnum id
mgiRefLookup = {}

#
# use gpi file to build gpiLookup of object:MGI:xxxx relationship
#
gpiSet = ['PR', 'EMBL', 'ENSEMBL', 'RefSeq']
gpiFileName = None
gpiFile = None
gpiLookup = {}

# lookup file of Evidence Code Ontology (_vocab_key = 111)
# to GO Evidence Code (_vocab_key = 3)
ecoLookupByEco = {}
ecoLookupByEvidence = {}

# lookup file of Uberon to EMAPA
uberonLookup = {}

# mapping of load reference J: to GO_REF IDs
# see _LogicalDB_key = 185 (GO_REF)
goRefLookup = {}

# mapping of load reference J: to PubMed IDs
pubmedLookup = {}

#
# mgi.gpad/col 3
#
goqualifiersLookup = [
'enables', 
'part_of', 
'acts_upstream_of_or_within',
'acts_upstream_of_or_within_positive_effect',
'acts_upstream_of_or_within_negative_effect',
'acts_upstream_of',
'acts_upstream_of_positive_effect',
'acts_upstream_of_negative_effect',
'involved_in',
'located_in',
'is_active_in'
]

#
# Purpose: Initialization
#
def initialize():

    global mgiInFileName, mgiInFile
    global prInFileName, prInFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global pubmedErrorFile 
    global mgiRefLookup
    global gpiFileName, gpiFile, gpiLookup
    global ecoLookupByEco
    global ecoLookupByEvidence
    global uberonLookup
    global goRefLookup
    global pubmedLookup

    #
    # open files
    #

    mgiInFileName = os.environ['MGIINFILE_NAME_GPAD']
    prInFileName = os.environ['PRINFILE_NAME_GPAD']
    gpiFileName = os.environ['GPIFILE']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']

    mgiInFile = open(mgiInFileName, 'r')
    prInFile = open(prInFileName, 'r')
    gpiFile = open(gpiFileName, 'r')
    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')

    pubmedErrorFile = reportlib.init('pubmed', outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    #
    # lookup file of mgi ids or pubmed ids -> J:
    # mgi id:jnum id
    # pubmed id:jnum id
    #

    print('reading mgi id/pubmed id -> J: translation...')

    results = db.sql('select mgiID, pubmedID, jnumID from BIB_Citation_Cache where jnumID is not null', 'auto')
    for r in results:
        mgiRefLookup[r['mgiID']] = r['jnumID']
        if r['pubmedID'] != '':
            mgiRefLookup[r['pubmedID']] = r['jnumID']
    #print(mgiRefLookup['14321840'])

    #
    # read/store object-to-Marker info
    #

    print('reading object -> marker translation using gpi file...')

    for line in gpiFile.readlines():
        if line[:1] == '!':
            continue
        tokens = line[:-1].split('\t')
        tokens2 = tokens[0].split(':')
        if tokens2[0] in gpiSet:
            key = tokens[0]
            value = tokens[6].replace('MGI:MGI:', 'MGI:')
            if key not in gpiLookup:
                gpiLookup[key] = []
            gpiLookup[key].append(value)
    #print(gpiLookup)

    #
    # lookup file of Evidence Code Ontology using ecolib.py library
    #
    print('reading eco -> go evidence translation...')
    ecoLookupByEco, ecoLookupByEvidence = ecolib.processECO()

    #
    # read/store UBERON-to-EMAPA info
    #
    print('reading uberon -> emapa translation file...')
    uberonLookup = uberonlib.processUberon() 

    #
    # lookup file of GO_REF->J:
    #
    results = db.sql('''select a1.accID as goref, a2.accID as jnum
        from ACC_Accession a1, ACC_Accession a2
        where a1._MGIType_key = 1
        and a1._LogicalDB_key = 185
        and a1._Object_key = a2._Object_key
        and a2._MGIType_key = 1
        and a2._LogicalDB_key = 1
        and a2.prefixPart = 'J:'
        ''', 'auto')

    for r in results:
        key = r['goref']
        value = r['jnum']
        goRefLookup[key] = value
    #print(goRefLookup)

    #
    # lookup file of Pubmed->J:
    #
    results = db.sql('''select pubmedid, jnumid
        from BIB_Citation_Cache
        where pubmedid is not null
        and jnumid is not null
        ''', 'auto')

    for r in results:
        key = r['pubmedid']
        value = r['jnumid']
        pubmedLookup[key] = value
    #print(pubmedLookup)

    return 0

#
# Purpose: Read MGI GPAD file and generate Annotation file
#
def readGPAD(gpadInFile):
    global pubmedErrorFile

    #
    #	for each row in the GPAD file (MGIINFILE_NAME_GPAD, PRINFILE_NAME_GPAD):
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
    # field 10: Assigned By (NOCTUA_)
    # field 11: Annotation Extension
    # field 12: Annotation Properties

    # see annotload/annotload.py for format
    # field 6:  Qualifier : null
    # field 9 : Notes : none
    # field 10: logicalDB : MGI
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\tMGI\t%s\n' 

    print('reading MGI GPAD...')

    for line in gpadInFile.readlines():

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
        inferredFrom = tokens[6].replace('MGI:MGI:', 'MGI:')
        taxID = tokens[7]
        modDate = tokens[8]
        createdBy = tokens[9]
        extensions = tokens[10].replace('MGI:MGI:', 'MGI:')
        properties = tokens[11]

        #
        # skip if the GO id is a root term:  GO:0003674, GO:0008150, GO:0005575
        #

        #if goID in ('GO:0003674','GO:0008150', 'GO:0005575'):
        #    errorFile.write('Root Id is used : %s\n%s\n****\n' % (goID, line))
        #    continue

        #
        # skip if the databaseID is not MGI or PR
        #

        if databaseID != 'MGI' and databaseID not in gpiSet:
            errorFile.write('column 1 is not valid: %s\n%s\n****\n' % (databaseID, line))
            continue

        #
        # if non-MGI object, then add as Marker annotation and use 'gene prodcut' as a property
        #

        if databaseID in gpiSet:
            #print tokens
            dbobjectID = databaseID + ':' + dbobjectID
            properties = 'gene product=' + dbobjectID + '|' + properties

            if dbobjectID in gpiLookup:
                dbobjectID = gpiLookup[dbobjectID][0]
            else:
                errorFile.write('object is not in GPI file: %s\n%s\n****\n' % (dbobjectID, line))
                continue

        # translate references (MGI/PMID) to J numbers (J:)
        # use the first J: match that we find

        print(references)
        jnumID = ""
        jnumIDFound = 0
        referencesTokens = references.split('|')
        #print(referencesTokens)
        for r in referencesTokens:
            refID = r.replace('MGI:MGI:', 'MGI:')

            if jnumIDFound == 1:
                break

            if refID in mgiRefLookup:
                jnumID = mgiRefLookup[refID]
                jnumIDFound = 1
                 
            elif refID in goRefLookup:
                jnumID = goRefLookup[refID]
                jnumIDFound = 1

        # if reference does not exist...skip it
        if jnumIDFound == 0:
            errorFile.write('Invalid Reference/either no pubmed id or no jnum: %s\n%s\n****\n' % (references, line))
            continue

        if evidenceCode in ecoLookupByEco:
            #goEvidenceCode = ecoLookupByEco[evidenceCode][0]
            goEvidenceCode = ecoLookupByEco[evidenceCode]
        else:
            errorFile.write('Invalid ECO id : cannot find valid GO Evidence Code : %s\n%s\n****\n' % (evidenceCode, line))
            continue

        #
        # "extensions" contain things like "occurs_in", "part_of", etc.
        # and are added to "properties" for forwarding to the annotation loader
        #
        if len(extensions) > 0:

            # to translate uberon ids to emapa
            extensions, errors = uberonlib.convertExtensions(extensions, uberonLookup)
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
        # if qualifier in goqualifiersLookup:
        #
        #	a) store as annotload/column 11/Property
        #
        #	b) append to 'properties'
        #
        #	for example:
        #		go_qualifier=part_of
        #		go_qualifier=enables
        #		go_qualifier=involved_in
        #
        # else:
        #	a) store as annotload/column 6/Qualifier
        #
        goqualifiers = []
        for g in qualifier.split('|'):
            if g in goqualifiersLookup:
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

        # attached prefix
        createdBy = 'NOCTUA_' + createdBy

        annotFile.write(annotLine % (goID, dbobjectID, jnumID, goEvidenceCode, inferredFrom, \
                '|'.join(goqualifiers), createdBy, modDate, properties))

    return 0

#
# Purpose: Close files
#
def closeFiles():

    mgiInFile.close()
    prInFile.close()
    annotFile.close()
    errorFile.close()
    reportlib.finish_nonps(pubmedErrorFile)

    return 0

#
# main
#

if initialize() != 0:
    sys.exit(1)

if readGPAD(mgiInFile) != 0:
    sys.exit(1)

if readGPAD(prInFile) != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)
