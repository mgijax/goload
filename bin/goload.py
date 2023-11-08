'''
#
# goload.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#       ${MGIINFILE_NAME_GPAD}     the MGI GPAD file
#
#       The GPAD 2.0 file contains:
#		1:  DB_Object_ID
#               2:  Negation
#               3:  Relation Ontology (RO)
#               4:  Ontology_Class_ID
#               5:  References (PMIDs)
#               6:  Evidence_Type
#               7:  With_Or_From
#		8:  Interacting_Taxon_ID
#		9:  Annotation_Date (yyymmdd)
#		10: Assigned_By (GO_Central)
#		11: Annotation_Extensions
#		12: Annotation_Properties
#
# Outputs/Report:
#
# 	The annotation loader format has the following columns:
#
#	A tab-delimited file in the format:
#		1:  Accession ID of Vocabulary Term being Annotated to
#		2:  ID of MGI Object being Annotated (ex. MGI ID)
#		3:  J: (J:#####)
#		4:  Evidence Code Abbreviation (max length 5)
#		5:  Inferred From 
#    		6:  Qualifier  (from Negation)
#		7:  Editor (max length 30)
#		8:  Date (MM/DD/YYYY)
#		9:  Notes 
#		10: Logical DB Name of Object (leave null)
#		11: Properties (from Relation/Qualifier)
#
# Usage:
#       goload.py
#
# History:
#
# lec	08/2023
#       wts2-1155/fl2-394/Test Rat/Human (gorat, goahuman)
#
'''

import sys 
import os
import db

goloadpath = os.environ['GOLOAD'] + '/lib'
sys.path.insert(0, goloadpath)
import ecolib
import uberonlib

# GPAD files from the dataloads directory
mgiInFileName = None
# GPAD file pointer
mgiInFile = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# error formatted file
errorFileName = None
# error file pointer
errorFile = None
hasError = 0

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

# go-relation ontology lookup (RO/etc. id, term)
goROLookup = {}

#
# Purpose: Initialization
#
def initialize():

    global mgiInFileName, mgiInFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global mgiRefLookup
    global gpiFileName, gpiFile, gpiLookup
    global ecoLookupByEco
    global ecoLookupByEvidence
    global uberonLookup
    global goRefLookup
    global pubmedLookup
    global goROLookup

    #
    # open files
    #

    mgiInFileName = os.environ['MGIINFILE_NAME_GPAD']
    gpiFileName = os.environ['GPIFILE']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']

    mgiInFile = open(mgiInFileName, 'r')
    gpiFile = open(gpiFileName, 'r')
    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')

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
    results = db.sql('''
        select pubmedid, jnumid
        from BIB_Citation_Cache
        where pubmedid is not null
        and jnumid is not null
        ''', 'auto')

    for r in results:
        key = r['pubmedid']
        value = r['jnumid']
        pubmedLookup[key] = value
    #print(pubmedLookup)

    #
    # note contains the go-property id RO:, etc.
    # will need to note (id) and the term itself
    #
    results = db.sql('''
        select t.term, t.note
        from VOC_Term t
        where t._vocab_key = 82
        and (t.note like 'RO:%' or t.note like 'BFO%')
        ''', 'auto')
    for r in results:
        key = r['note']
        value = r['term']
        if key not in goROLookup:
            goROLookup[key] = []
        goROLookup[key].append(value)
    #print(goROLookup)

    return 0

#
# Purpose: Read MGI GPAD file and generate Annotation file
#
def readGPAD(gpadInFile):
    #
    #	for each row in the GPAD file (MGIINFILE_NAME_GPAD, PRINFILE_NAME_GPAD):
    #
    #           if the reference does not exist in MGI (using mgiRefLookup)
    #                   write the record to the error file (INFILE_NAME_ERROR)
    #                   skip the row
    #
    #           write the record to the annotation file (INFILE_NAME)
    #

    global hasError

    # see annotload/annotload.py for format
    # 6:  Qualifier : null
    # 9:  Notes : none
    # 10: logicalDB : MGI
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\tMGI\t%s\n' 

    print('reading MGI GPAD...')

    for line in gpadInFile.readlines():

        if line[0] == '!':
            continue

        hasError = 0
        tokens = line[:-1].split('\t')

        dbobjectID = tokens[0].replace('MGI:MGI:', 'MGI:')
        gpiobjectID = tokens[0]
        negation = tokens[1]
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
        # skip if the dbobjectID is not MGI or PR
        #
        if dbobjectID.startswith('MGI:') == False and dbobjectID.startswith('PR:') == False:
            errorFile.write('column 1 is not valid: %s\n%s\n****\n' % (databaseID, line))
            hasError += 1
            continue

        #
        # if non-MGI object, then add as Marker annotation and use 'gene prodcut' as a property
        # grab marker from gpiLookup
        # example: PR:Q9QWY8-2 -> MGI:1342335
        #       properties = 'gene product=PR:Q9QWY8-2'
        #       dbobjectID = 'MGI:1342335'
        #
        databaseID, databaseTerm = dbobjectID.split(':')
        if databaseID in gpiSet:
            if gpiobjectID in gpiLookup:
                properties = 'gene product=' + dbobjectID + '|' + properties
                dbobjectID = gpiLookup[gpiobjectID][0]
            else:
                errorFile.write('object is not in GPI file: %s\n%s\n****\n' % (gpiobjectID, line))
                hasError += 1
                continue

        # translate references (MGI/PMID) to J numbers (J:)
        # use the first J: match that we find

        #print(references)
        jnumID = ""
        jnumIDFound = 0
        referencesTokens = references.split('|')
        #print(referencesTokens)

        for r in referencesTokens:

            refID = r.replace('MGI:MGI:', 'MGI:')
            refID = refID.replace('PMID:', '')

            if refID in mgiRefLookup:
                jnumID = mgiRefLookup[refID]
                jnumIDFound = 1
                 
            if refID in goRefLookup:
                jnumID = goRefLookup[refID]
                jnumIDFound = 1

        # if reference does not exist...skip it
        if jnumIDFound == 0:
            errorFile.write('Invalid Reference/either no pubmed id or no jnum (5): %s\n%s\n****\n' % (references, line))
            hasError += 1
            continue

        if evidenceCode in ecoLookupByEco:
            #goEvidenceCode = ecoLookupByEco[evidenceCode][0]
            goEvidenceCode = ecoLookupByEco[evidenceCode]
        else:
            errorFile.write('Invalid ECO id : cannot find valid GO Evidence Code (6): %s\n%s\n****\n' % (evidenceCode, line))
            hasError += 1
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
                    hasError += 1

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
        # if qualifier in goproperytLookup:
        #
        #	a) store as annotload/column 11/Property
        #
        #	b) append to 'properties'
        #
        #	for example:
        #		go_qualifier_id=BFO:0000050
        #		go_qualifier_term=part_of
        #		go_qualifier_id=RO:0002327
        #		go_qualifier_term=enables
        #		go_qualifier_id=RO:0002331
        #		go_qualifier_term=involved_in
        #
        for g in qualifier.split('|'):
            if g in goROLookup:
                if len(properties) > 0:
                    properties = properties + '|'
                properties = properties + 'go_qualifier_id=' + g
                properties = properties + '|go_qualifier_term=' + goROLookup[g][0]
            else:
                errorFile.write('Invalid Relation in GOProperty (3): cannot find RO:,etc id: %s\n%s\n****\n' % (g, line))
                hasError += 1

        if hasError > 0:
                continue

        # for evidence:
        #	a) store as translated ECO->MGI->Evidence Code field
        #	b) append to 'properties' as:
        #		evidence=ECO:xxxx
        #
        if len(properties) > 0:
             properties = properties + '|'
        properties = properties + 'evidence=' + evidenceCode

        # re-format to mgi-property format
        #
        properties = properties.replace('=', '&=&')
        properties = properties.replace('|', '&==&')
        properties = properties.replace('&==&&==&', '&==&')

        # write data to the annotation file
        # note that the annotation load will qc duplicate annotations itself
        # (dbobjectID, goID, goEvidenceCode, jnumID)
        annotFile.write(annotLine % (goID, dbobjectID, jnumID, goEvidenceCode, inferredFrom, negation, createdBy, modDate, properties))

    return 0

#
# Purpose: Close files
#
def closeFiles():

    mgiInFile.close()
    annotFile.close()
    errorFile.close()

    return 0

#
# main
#

if initialize() != 0:
    sys.exit(1)

if readGPAD(mgiInFile) != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)

