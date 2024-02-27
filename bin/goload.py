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
#               3:  Relation Ontology (RO) -> GO Property (roLookup)
#               4:  Ontology_Class_ID
#               5:  References (PMIDs) -> Jnum ID (mgiRefLookup)
#               6:  Evidence_Type/ECO -> GO evidence (ecoLookupByEco)
#               7:  With_Or_From
#		8:  Interacting_Taxon_ID
#		9:  Annotation_Date (yyymmdd)
#		10: Assigned_By (GO_Central, etc.)
#		11: Annotation_Extensions (RO, BFO) -> GO Property, (roLookup) (UBERON) -> EMAPA (uberonLookup)
#		12: Annotation_Properties -> GO Property, things like contributor, model-state, noctua-model-id, etc.
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
# lec	11/2023
#       wts2-1155/GOC taking over GOA mouse, GOA human, etc.
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
gpadInFileName = None
# GPAD file pointer
gpadInFile = None

# annotation formatted file
annotFileName = None
# annotation file pointer
annotFile = None

# error formatted file
errorFileName = None
pubmedFileName = None
# error file pointer
errorFile = None
pubmedFile = None
hasError = 0

#
# use gpi file to build gpiLookup of object:MGI:xxxx relationship
#
databaseIDSet = ['MGI', 'PR', 'EMBL', 'ENSEMBL', 'RefSeq']
gpiSet = ['PR', 'EMBL', 'ENSEMBL', 'RefSeq']
gpiFileName = None
gpiFile = None
gpiLookup = {}

# lookup file of mgi ids or pubmed ids -> J:
# mgi id:jnum id
# pubmed id:jnum id
mgiRefLookup = {}

# lookup file of reference J: -> GO_REF IDs
# see _LogicalDB_key = 185 (GO_REF)
goRefLookup = {}

# lookup file of Evidence Code Ontology (_vocab_key = 111)
# to GO Evidence Code (_vocab_key = 3)
ecoLookupByEco = {}      # used
ecoLookupByEvidence = {} # not used, but is returned by ecolib

# lookup file of Uberon -> EMAPA
uberonLookup = {}

# lookup file of go-relation ontology (RO/BFO) -> GO Property
roLookup = {}

# lookup file of assignedBy -> MGI User/login
userLookup = []

#
# Purpose: Initialization
#
def initialize():

    global gpadInFileName, gpadInFile
    global annotFileName, annotFile
    global errorFileName, errorFile
    global pubmedFileName, pubmedFile
    global gpiFileName, gpiFile, gpiLookup
    global mgiRefLookup
    global goRefLookup
    global ecoLookupByEco
    global ecoLookupByEvidence
    global uberonLookup
    global roLookup
    global userLookup

    #
    # open files
    #

    gpadInFileName = os.environ['MGIINFILE_NAME_GPAD']
    gpiFileName = os.environ['GPIFILE']
    annotFileName = os.environ['INFILE_NAME']
    errorFileName = os.environ['INFILE_NAME_ERROR']
    pubmedFileName = os.environ['PUBMED_ERROR']

    gpadInFile = open(gpadInFileName, 'r')
    gpiFile = open(gpiFileName, 'r')
    annotFile = open(annotFileName, 'w')
    errorFile = open(errorFileName, 'w')
    pubmedFile = open(pubmedFileName, 'w')

    #
    # lookup file of mgi ids or pubmed ids -> J:
    # mgi id:jnum id
    # pubmed id:jnum id
    #

    print('reading mgi id/pubmed id -> J: translation')
    results = db.sql('select mgiID, pubmedID, jnumID from BIB_Citation_Cache where jnumID is not null', 'auto')
    for r in results:
        mgiRefLookup[r['mgiID']] = r['jnumID']
        if r['pubmedID'] != '':
            mgiRefLookup[r['pubmedID']] = r['jnumID']
    #print(mgiRefLookup['14321840'])

    #
    # read/store object-to-Marker info
    #
    print('reading object -> marker translation using gpi file')
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
    print('reading eco -> go evidence translation')
    ecoLookupByEco, ecoLookupByEvidence = ecolib.processECO()

    #
    # read/store UBERON-to-EMAPA info
    #
    print('reading uberon -> emapa translation file')
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
        if key not in roLookup:
            roLookup[key] = []
        roLookup[key].append(value)
    #print(roLookup)

    #
    # read/store MGI_User used for GO (GO_)
    #
    print('reading mgi_user GO_')
    results = db.sql('''select login from MGI_User where login like 'GO_%' ''', 'auto')
    for r in results:
        userLookup.append(r['login'])
    #print(userLookup)

    return 0

#
# Purpose: Read MGI GPAD file and generate Annotation file
#
def readGPAD(gpadInFile):
    #
    #	for each row in the GPAD file (MGIINFILE_NAME_GPAD):
    #
    #           if the reference does not exist in MGI (using mgiRefLookup)
    #                   write the record to the error file (INFILE_NAME_ERROR)
    #                   skip the row
    #
    #           write the record to the annotation file (INFILE_NAME)
    #

    global hasError
    global userLookup

    # see annotload/annotload.py for format
    # 6:  Qualifier : null
    # 9:  Notes : none
    # 10: logicalDB : MGI
    annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\tMGI\t%s\n' 

    print('reading MGI GPAD')

    for line in gpadInFile.readlines():

        if line[0] == '!':
            continue

        hasError = 0
        tokens = line[:-1].split('\t')

        # 1:  DB_Object_ID : without extra MGI:
        # expect:  MGI:, PR:
        dbobjectID = tokens[0].replace('MGI:MGI:', 'MGI:')

        # 1:  DB_Object_ID with fill MGI:MGI:
        gpiobjectID = tokens[0]

        # 2:  Negation
        negation = tokens[1]

        # 3:  Relation Ontology (RO) -> GO Property (roLookup)
        qualifier = tokens[2]

        # 4:  Ontology_Class_ID
        goID = tokens[3]

        # 5:  References (PMIDs) -> Jnum ID (mgiRefLookup)
        references = tokens[4]
        references = references.replace('MGI:MGI:', 'MGI:')
        references = references.replace('PMID:', '')

        # 6:  Evidence_Type/ECO -> GO evidence (ecoLookupByEco)
        evidenceCode = tokens[5]

        # 7:  With_Or_From
        inferredFrom = tokens[6]
        inferredFrom = inferredFrom.replace('MGI:MGI:', 'MGI:')
        inferredFrom = inferredFrom.replace(',', '|')
        # unexpected : inconsisten uniprotkb names; remove when fixed in mgi.gpad file
        inferredFrom = inferredFrom.replace('UniprotkB', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UniprotKB', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UniProtKb', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UniPRotKB', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UniPROtKB', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UNiProtKB', 'UniProtKB')
        inferredFrom = inferredFrom.replace('UnIProtKB', 'UniProtKB')

        # 8:  Interacting_Taxon_ID
        taxID = tokens[7]

        # 9:  Annotation_Date (yyymmdd)
        annotDate = tokens[8]

        # 10: Assigned_By (GO_Central, etc.)
        assignedBy = tokens[9]

        # 11: Annotation_Extensions (RO, BFO) -> GO Property, (roLookup) (UBERON) -> EMAPA (uberonLookup)
        extensions = tokens[10].replace('MGI:MGI:', 'MGI:')

        # 12: Annotation_Properties
        properties = tokens[11].replace('"','')

        #
        # if non-MGI object, then add as Marker annotation and use 'gene product' as a property
        # these are considered "isoforms" of the mouse gene
        # grab marker from gpiLookup
        # example: PR:Q9QWY8-2 -> MGI:1342335
        #       properties = 'gene product=PR:Q9QWY8-2'
        #       dbobjectID = 'MGI:1342335'
        #
        #print(dbobjectID)
        databaseID, databaseTerm = dbobjectID.split(':')
        if databaseID in gpiSet:
            if gpiobjectID in gpiLookup:
                properties = 'gene product=' + dbobjectID + '|' + properties
                dbobjectID = gpiLookup[gpiobjectID][0]
            else:
                errorFile.write('Invalid Object not in GPI file (1:DB_Object_ID): %s\n%s\n****\n' % (gpiobjectID, line))
                hasError += 1
                continue
        if databaseID not in databaseIDSet:
                errorFile.write('Invalid ool1/databaseID not expected (1:DB_Object_ID): %s\n%s\n****\n' % (databaseID, line))
                hasError += 1
                continue

        # start: references
        # translate references (MGI/PMID) to J numbers (J:)
        # use the first J: match that we find

        #print(references)
        jnumID = ""
        jnumIDFound = 0
        referencesTokens = references.split('|')
        #print(referencesTokens)

        for r in referencesTokens:

            if r in mgiRefLookup:
                jnumID = mgiRefLookup[r]
                jnumIDFound = 1
                 
            if r in goRefLookup:
                jnumID = goRefLookup[r]
                jnumIDFound = 1

        # if reference does not exist...skip it
        # exclude Reactome references from pubmedFile/QC
        if jnumIDFound == 0:
            errorFile.write('Invalid Reference/either no GO_REF, no pubmed id or no jnum (5:References): %s\n%s\n****\n' % (references, line))
            if not references.startswith('Reactome'):
                pubmedFile.write(references + '\n')
            hasError += 1
            continue

        if evidenceCode in ecoLookupByEco:
            goEvidenceCode = ecoLookupByEco[evidenceCode]
        else:
            errorFile.write('Invalid ECO id : cannot find valid GO Evidence Code (6:Evidence_Type): %s\n%s\n****\n' % (evidenceCode, line))
            hasError += 1
            continue

        # end: references

        # start: extensions/properties
        # for MGI, we merge the extensions & properties into MGI-properties
        #

        #
        # extensions contain things like RO/BFO which need to be translated to "occurs_in", "part_of", etc.
        # and are added to "properties" for forwarding to the annotation loader
        #
        if len(extensions) > 0:

            # to translate uberon ids to emapa
            extensions, errors = uberonlib.convertExtensions(extensions, uberonLookup)
            if errors:
                for error in errors:
                    errorFile.write('%s\n%s\n****\n' % (error, line))
                    hasError += 1

            # unexpected quote; remove it
            extensions = extensions.replace('"','')
            # different delimiters; make them all the same ","
            extensions = extensions.replace('|',',')

            # translate extensions to roLookup terms
            s1 = extensions.split(",")
            for s in s1:
                s2 = s.split("(")
                roTerm = s2[0]
                if roTerm in roLookup:
                    extensions = extensions.replace(roTerm, roLookup[roTerm][0])
                else:
                    errorFile.write('Invalid Relation in GO-Property (11:Annotation_Extensions,12:Annotation_Properties): cannot find RO:,BFO: id: %s\n%s\n****\n' % (roTerm, line))
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
            if g in roLookup:
                if len(properties) > 0:
                    properties = properties + '|'
                properties = properties + 'go_qualifier_id=' + g
                properties = properties + '|go_qualifier_term=' + roLookup[g][0]
            else:
                errorFile.write('Invalid Relation in GO-Property (3:Relation Ontology): cannot find RO:,BFO: id: %s\n%s\n****\n' % (g, line))
                hasError += 1

        if len(assignedBy) == 0:
                errorFile.write('Missing Assigned By (10): \n****%s\n' % (line))
                hasError += 1

        if hasError > 0:
                continue

        # for evidence:
        #	a) store as translated ECO->MGI->Evidence Code field
        #	b) append to 'properties' as: evidence=ECO:xxxx
        #
        if len(properties) > 0:
             properties = properties + '|'
        properties = properties + 'evidence=' + evidenceCode

        # for taxID : append to "properties' as: Interacting taxon ID=xxxx
        if len(taxID) > 0:
                if len(properties) > 0:
                        properties = properties + '|'
                properties = properties + 'Interacting taxon ID=' + taxID

        #
        # re-format to mgi-property format
        #
        properties = properties.replace('"', '')
        properties = properties.replace('=', '&=&')
        properties = properties.replace('|', '&==&')
        properties = properties.replace('&==&&==&', '&==&')

        # end: extensions/properties

        #
        # start:  assigned by
        #
        # if assignedBy does not exist in MGI_User, then add it
        # for MGI, convert assignedBy -> 'GO_' + assignedBy
        # example:  SynGO -> GO_SynGO, UniProt -> GO_UniProt 
        # use the prefix "GO_" to the MGI_User.login/name, so that we can find the GO annotations more easily
        #
        if assignedBy != 'GO_Central':
                assignedBy = 'GO_' + assignedBy
        if assignedBy not in userLookup:
            addSQL = '''
                insert into MGI_User values (
                (select max(_User_key) + 1 from MGI_User), 316353, 316350, '%s', '%s', null, null, 1000, 1000, now(), now()
                )''' % (assignedBy, assignedBy)
            print('adding new MGI_User:' + str(addSQL))
            db.sql(addSQL, 'auto')
            db.commit()
            userLookup.append(assignedBy)

        # end:  assigned by

        # write data to the annotation file
        # note that the annotation load will qc duplicate annotations itself
        # (dbobjectID, goID, goEvidenceCode, jnumID, properties, inferred-from)
        annotFile.write(annotLine % (goID, dbobjectID, jnumID, goEvidenceCode, inferredFrom, negation, assignedBy, annotDate, properties))

    return 0

#
# Purpose: Close files
#
def closeFiles():

    gpadInFile.close()
    annotFile.close()
    errorFile.close()
    pubmedFile.close()

    return 0

#
# main
#

if initialize() != 0:
    sys.exit(1)

if readGPAD(gpadInFile) != 0:
    sys.exit(1)

closeFiles()
sys.exit(0)

