#!/usr/local/bin/python

'''
#
# goamouse.py
#
#       See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#       ${PROTEIN_SORTED}      the sorted GAF file
#       ${ISOFORM_SORTED}      the sorted GAF file
#
#       The GAF file contains:
#
#               field 1:  Database ID ('MGI')
#               field 2:  GOA ID
#               field 3:  Symbol
#               field 4:  Qualifier value
#               field 5:  GO ID
#               field 6:  References (PMIDs)
#               field 7:  Evidence code
#               field 8:  Inferred From 
#		field 10: GOA Name
#		field 11: Synonyms
#		field 12: Marker Type
#		field 13: Taxom ID
#               field 14: Modification Date
#               field 15: Assigned By
#
# Outputs/Report:
#
#	TR 7904/7926
#
#	Takes the GOA file ${PROTEIN_SORTED} and generates
#
#		mgi.error
#			file of GOA annotations that originated from MGI
#
#		unresolvedA.error
#			file of GOA annotations where UniProtID resolves to more than one MGI Marker
#	
#		unresolvedB.error
#			file of GOA annotations where UniProtID don't resolve to a MGI Marker
#
#		unresolvedC.error
#			file of GOA annotations where GO id is a root id (GO:0003674, GO:0008150, GO:0005575)
#
#		duplicates.error
#		   	file of GOA annotations that are duplicates to those in MGI
#
#		pubmedannot.error
#			file of GOA annotations of those PubMed IDs that are not in MGI
#
#		pubmed.error
#			file of unique PubMed IDs that are not in MGI
#
#		pubmedevi.error
#			file of Evidence Codes + count of Annotations for those with PubMed IDs that are not in MGI
#
#		goamouse.gaf
#			file of GOA annotations that can be appended to MGI GO association file
#
#		goa.annot
#			file of GOA annotations that can be loaded into MGI via the Annotation loader
#
#               uberon.txt
#                       file of all UBERON->EMAPA translations
#
#               properties.error
#                       file of bad UBERON -> EMAPA translations
#                       file of invalid properties ids : ENSEMBL, NCBI_Gene
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
#       goamouse.py
#
# History:
#
# lec	07/27/2016
#	- TR12378/isoforms are now in their own file : see config/ISOFORM
#
# lec   11/05/2015
#       - TR12070/properties translations:
#	a) UBERON -> EMAPA
#	b) ENSEMBL -> MGI (ldb=60)
#	c) NCBI_Gene -> MGI (ldb=55)
#
# lec   01/13/2014
#       - TR11570/11571/qualifier contains "_" in both input and MGI
#
# lec	01/06/2014
#	- TR 11528/collect all column 16 "properties"
#
# lec   09/07/2011
#	- TR 9960; attach column 17 (isoform)
#
# lec	03/10/2010
#	- TR 10112; "!" version information in GOA/GAF file 
#
# lec	01/05/2010
#	- TR 9228; replace goaID O35740-1 with O35740
#
# lec	05/07/2008
#	- TR 8997/lowercase the marker type
#
# lec   10/02/2006
#       - created
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

#db.setTrace()
db.setAutoTranslate(False)
db.setAutoTranslateBE(False)

#### Constants ###
UBERON_MAPPING_MULTIPLES_ERROR = "uberon id has > 1 emapa : %s\t%s"
UBERON_MAPPING_MISSING_ERROR = "uberon id not found or missing emapa id: %s" 
PROPERTIES_ACCID_INVALID_ERROR = "accession id is not associated with mouse marker: %s"

gafLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t\n'
gpadLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t\n'
annotLine = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\t\t%s\n' 

# list of evidence codes that are skipped; that is, not loaded into MGI
skipEvidenceCodes = ['IEP']

### Globals ###

inFileName = None
goaPrefix = None
unresolvedAErrorFile = None
unresolvedBErrorFile = None
unresolvedCErrorFile = None
mgiErrorFile = None
nopubmedFile = None
pubmedAnnotFile = None
pubmedErrorFile = None
pubmedeviErrorFile = None
dupErrorFile = None
gafFile = None
gpadFile = None
annotFile = None
uberonTextFile = None
propertiesErrorFile = None

assoc = {}	# dictionary of GOA ID:Marker MGI ID
marker = {}	# dictionary of MGI Marker ID:Marker data
mgiannot = {}	# dictionary of existing annotations:  Marker key, GO ID, Evidence Code, Pub Med ID
newannot = {}	# dictionary of new annotations: Marker key, GO ID, Evidence Code, Pub Med ID
goids = {}      # dictionary of secondary GO ID:primary GO ID

annotByGOID = []	# go annotation by go ids
annotByRef = []		# go annotation by pub med ids
pubmed = {}		# dictionary of pubmed->J:
pubmedUnique = []	# list of unique pubmedids that are not in MGI
pubmedEvidence = {}	# evidence code:count for those annotations with pubmedids that are not in MGI
uberonLookup = {}	# uberon -> emapa lookup

# gpad file
# translate dag to qualifier (col 3)
dagQualifier = {'C':'part_of', 'P':'involved_in', 'F':'enables'}
ecoLookupByEco = {} 
ecoLookupByEvidence = {} 

#
# Initialize input/output files
#
def initialize():
    global goaPrefix 
    global unresolvedAErrorFile 
    global unresolvedBErrorFile 
    global unresolvedCErrorFile 
    global mgiErrorFile 
    global nopubmedFile 
    global pubmedAnnotFile 
    global pubmedErrorFile 
    global pubmedeviErrorFile 
    global dupErrorFile 
    global gafFile 
    global gpadFile 
    global annotFile 
    global uberonTextFile
    global propertiesErrorFile 

    global assoc
    global marker
    global mgiannot
    global newannot
    global goids
    global annotByGOID
    global annotByRef
    global pubmed
    global pubmedUnique
    global pubmedEvidence
    global uberonLookup
    global ecoLookupByEco, ecoLookupByEvidence

    #
    # open files
    #

    goaPrefix = os.environ['DELETEUSER']

    unresolvedAErrorFile = reportlib.init('unresolvedA', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    unresolvedBErrorFile = reportlib.init('unresolvedB', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    unresolvedCErrorFile = reportlib.init('unresolvedC', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    mgiErrorFile = reportlib.init('mgi', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    nopubmedFile = reportlib.init('nopubmed', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    pubmedAnnotFile = reportlib.init('pubmedannot', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    pubmedErrorFile = reportlib.init('pubmed', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    pubmedeviErrorFile = reportlib.init('pubmedevi', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    dupErrorFile = reportlib.init('duplicates', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    gafFile = reportlib.init('goamouse', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.gaf')

    gpadFile = reportlib.init('goamouse', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.gpad')

    annotFile = reportlib.init('goamouse', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.annot')

    uberonTextFile = reportlib.init('uberon', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.txt')

    propertiesErrorFile = reportlib.init('properties', \
    	outputdir = os.environ['OUTPUTDIR'], printHeading = None, fileExt = '.error')

    #
    # Mouse Markers
    # only include markers of type 'gene' (1)
    #

    print 'reading marker data...'
    db.sql('''
	select a.accID as mgiID, m._Marker_key, m.symbol, m.name, lower(t.name) as markerType 
	into temporary table markers 
	from ACC_Accession a, MRK_Marker m, MRK_Types t 
	where m._Organism_key = 1 
	and m._Marker_Type_key = 1 
	and m._Marker_key = a._Object_key 
	and a._MGIType_key = 2 
	and a._LogicalDB_key = 1 
	and a.prefixPart = 'MGI:' 
	and a.preferred = 1 
	and m._Marker_Type_key = t._Marker_Type_key
	''', None)
    db.sql('create index markers_idx1 on markers(_Marker_key)', None)

    results = db.sql('select * from markers', 'auto')
    for r in results:
        marker[r['mgiID']] = r

    #
    # Secondary GO Ids mapped to Primary GO Ids
    #

    print 'reading accession ids...'
    results = db.sql('''
	select a1.accID as paccid, a2.accID as saccid 
	from ACC_Accession a1, ACC_Accession a2 
	where a1._MGIType_key = 13 
	and a1.prefixPart = 'GO:' 
	and a1.preferred = 1 
	and a1._Object_key = a2._Object_key 
	and a1._MGIType_key = 13 
	and a1.prefixPart = 'GO:' 
	and a1.preferred = 0 
	''', 'auto')
    for r in results:
        goids[r['saccid']] = r['paccid']

    #
    # Mouse Markers annotated to...
    #
    # SwissProt (13)
    # TrEMBL (41)
    # RefSeq (27)
    # ENSEMBL (60)
    # VEGA (85)
    #

    print 'reading mouse markers annotatined to SwissProt/TrEMBL/RefSeq, etc....'
    results = db.sql('''
	select m._Marker_key, m.mgiID, a.accID as goaID 
	from markers m, ACC_Accession a 
	where m._Marker_key = a._Object_key 
	and a._LogicalDB_key in (13, 41, 27, 60, 85) 
	and a._MGIType_key = 2 
	''', 'auto')
    for r in results:
        key = r['goaID']
        value = r['mgiID']
        if key not in assoc:
	    assoc[key] = []
        assoc[key].append(value)

    #
    # existing GO annotations that have pub med ids
    # to detect duplicate annotations
    #

    print 'reading existing GO annotations that have pub med ids....'
    results = db.sql('''
	select a.accID as goID, t._Object_key, ec.abbreviation, 'PMID:' || r.accID as refID 
	from VOC_Annot t, ACC_Accession a, VOC_Evidence e, VOC_Term ec, ACC_Accession r 
	where t._AnnotType_key = 1000 
	and t._Term_key = a._Object_key 
	and a._MGIType_key = 13 
	and a.preferred = 1 
	and t._Annot_key = e._Annot_key 
	and e._EvidenceTerm_key = ec._Term_key 
	and e._Refs_key = r._Object_key 
	and r._MGIType_key = 1 
	and r._LogicalDB_key = 29
	''', 'auto')
    for r in results:

        key = r['_Object_key']

        if key not in mgiannot:
	    mgiannot[key] = []
        mgiannot[key].append((r['goID'], r['abbreviation'], r['refID']))

        if r['goID'] not in annotByGOID:
            annotByGOID.append(r['goID'])

    if r['refID'] not in annotByRef:
        annotByRef.append(r['refID'])

    #
    # existing IEA GO annotations
    # J:72247 interpro
    # J:60000 swissprot
    # J:72245
    #

    print 'reading existing IEA GO annotations....'
    results = db.sql('''
	select a.accID as goID, t._Object_key, ec.abbreviation, a.accID as refID 
	from VOC_Annot t, ACC_Accession a, VOC_Evidence e, VOC_Term ec, ACC_Accession r 
	where t._AnnotType_key = 1000 
	and t._Term_key = a._Object_key 
	and a._MGIType_key = 13 
	and a.preferred = 1 
	and t._Annot_key = e._Annot_key 
	and e._EvidenceTerm_key = ec._Term_key 
	and e._Refs_key in (61933,73197,73199) 
	and e._Refs_key = r._Object_key 
	and r._MGIType_key = 1 
	and r._LogicalDB_key = 1 
	and r.prefixPart= 'J:'
	''', 'auto')
    for r in results:

        key = r['_Object_key']

        if key not in mgiannot:
	    mgiannot[key] = []
        mgiannot[key].append((r['goID'], r['abbreviation'], r['refID']))

        if r['goID'] not in annotByGOID:
            annotByGOID.append(r['goID'])

        if r['refID'] not in annotByRef:
            annotByRef.append(r['refID'])

    #
    # existing pubmed->j: relationships
    #

    print 'reading existing pubmed->J: relationships....'
    results = db.sql('''
	select a1.accID as jnumID, 'PMID:' || a2.accID as pubmedID 
	from ACC_Accession a1, ACC_Accession a2 
	where a1._MGIType_key = 1 
	and a1._LogicalDB_key = 1 
	and a1.prefixPart = 'J:' 
	and a1.preferred = 1 
	and a1._Object_key = a2._Object_key 
	and a2._MGIType_key = 1 
	and a2._LogicalDB_key = 29 
	and a2.preferred = 1 
	''', 'auto')
    for r in results:
        key = r['pubmedID']
        value = r['jnumID']
        pubmed[key] = value

    #
    # use goload/lib/uberonlib to lookup uberon
    #
    print 'reading uberon/emapa obo file...'
    uberonLookup = uberonlib.processUberon()
    for u in uberonLookup:
        uberonTextFile.write(u + '\n')

    # use goload/lib/ecolib to lookup eco using evidence
    print 'reading eco obo file...'
    ecoLookupByEco, ecoLookupByEvidence = ecolib.processECO()

    return 0

#
# Purpose : Read GAF file and generate Annotation file
#
def readGAF(inFile):

    for line in inFile.readlines():

        if line[0] == '!':
	    continue

        # load this annotation into MGI?
        loadMGI = 1

        tokens = line[:-1].split('\t')
    #    databaseID = tokens[0]
        databaseID = 'MGI'
        goaID = tokens[1]		# translate to MGI value
        goaSymbol = tokens[2]		# translate to MGI value
        qualifierValue = tokens[3]
        goID = tokens[4]
        refID = tokens[5]		# translate to MGI value
        checkrefID = refID
        evidence = tokens[6]
        inferredFrom = tokens[7].replace('MGI:MGI:', 'MGI:')
        dag = tokens[8]
        goaName = tokens[9]		# translate to MGI value
        synonyms = tokens[10]
        markerType = tokens[11]	# translate to MGI value
        taxID = tokens[12]
        modDate = tokens[13]
        assignedBy = tokens[14]
        properties = tokens[15]
        isoformValue = tokens[16]	# isoform id (UniProtKB:Q9Z2D8-1)

        # leave 'GOC' as-is (do not add 'GOA_' prefix)
        if assignedBy not in ('GOC'):
    	    mgiassignedBy = goaPrefix + assignedBy
        else:
    	    mgiassignedBy = assignedBy

        # skip it if it's assigned by MGI; that means it came from us to begin with
        # skip it if it's assigned by GOC; shouldn't be in here at all

        if assignedBy in ('MGI', 'GOC'):
	    mgiErrorFile.write(line)
	    continue

        # skip it if there is not PubMed ID

        if refID[0:5] != 'PMID:':
	    nopubmedFile.write(line)
	    continue

        #
        # skip if the GO id is a root term:  GO:0003674, GO:0008150, GO:0005575
        #

        if goID in ('GO:0003674','GO:0008150', 'GO:0005575'):
	    unresolvedCErrorFile.write(line)
	    continue

        #
        # translate GOA "Refs" to MGI J: so we can check for duplicates
        #

        if refID == 'GOA:interpro':
	    checkrefID = 'J:72247'

        if refID == 'GOA:spkw':
	    checkrefID = 'J:60000'

        if refID == 'GOA:spec':
	    checkrefID = 'J:72245'

        # error if GOA id is not found in MGI

        s = goaID.find('-')
        if s >= 0:
	    goaIDstrip = goaID[:s]
        else:
	    goaIDstrip = goaID

        if goaIDstrip not in assoc:
	    unresolvedBErrorFile.write(line)
	    continue
        else:
            # error if GOA id maps to more than one MGI Marker
    
            if len(assoc[goaIDstrip]) > 1:
	        unresolvedAErrorFile.write(line)
	        continue

            mgiID = assoc[goaIDstrip][0]

        m = marker[mgiID]
        markerKey = m['_Marker_key']

        # translate secondary GO ids to primary
        if goID in goids:
	    goID = goids[goID]

        # duplicate error if the annotation already exists in MGI

        if markerKey in mgiannot:
            goaAnnot = (goID, evidence, checkrefID)
            if goaAnnot in mgiannot[markerKey]:
	        dupErrorFile.write(line)
	        continue

        # resolve pubmed ID to MGI J:

        if refID not in pubmed:

	    # pubmed id not in MGI
	    # don't load this annotation into MGI

	    loadMGI = 0

            if refID.find('PMID:') >= 0:
	        if refID not in pubmedUnique:
		    # cache unique list of pubmed ids
		    pubmedUnique.append(refID)

		    # store counts by evidence code
		    if evidence not in pubmedEvidence:
		        pubmedEvidence[evidence] = 0
                    else:
		        pubmedEvidence[evidence] = pubmedEvidence[evidence] + 1

		    # write annotation to error file
		    pubmedAnnotFile.write(line)

        else:
	    jnumID = pubmed[refID]

        # if evidence code is in "skipped" list, don't load this annotation into MGI
        if evidence in skipEvidenceCodes:
	    loadMGI = 0

        # if this annotation is not loaded into MGI, then write it to the "to-append" file and continue

        if not loadMGI:

	    # for gafFile

            gafFile.write(gafLine % (databaseID, mgiID, m['symbol'], qualifierValue, goID, refID, evidence, inferredFrom,\
	        dag, m['name'], synonyms, m['markerType'], taxID, modDate, assignedBy))

	    # for gpadFile, translate 'qualiferValue' and 'evidence'

	    gpadQualifier = dagQualifier[dag]
            if len(qualifierValue) > 0:
                gpadQualifier = gpadQualifier + '|' + qualifierValue.strip()

	    if evidence in ecoLookupByEvidence:
	        gpadEvidence = ecoLookupByEvidence[evidence]
	    else:
	        gpadEvidence = 'error:cannot find ECO equivalent:%' % (evidence)

	    #print evidence, gpadEvidence
            gpadFile.write(gpadLine % (databaseID, mgiID, gpadQualifier, goID, refID, gpadEvidence, inferredFrom,\
	        taxID, modDate, assignedBy))

	    continue

        #
        # collect all annotations, collapsing the same annotation of different inferredFrom into one record
        #

        if len(isoformValue) > 0:
	    mgiproperties = 'gene product&=&' + isoformValue
        else:
	    mgiproperties = ''

        #
        # start : column 16 (properties)
        #
	
	properties, errors = convertPropertiesIds(properties, uberonLookup)

	if errors:
	    for error in errors:
		propertiesErrorFile.write(error + '\n')
		propertiesErrorFile.write(line + '*****\n')

        #
        # re-format to mgi-property format
        #
        properties = properties.replace('(', '&=&')
        properties = properties.replace(')', '')
        properties = properties.replace(',', '&==&')
        properties = properties.replace('|', '&===&')

        #
        # end : column 16
        #

        if len(mgiproperties) > 0 and len(properties) > 0:
	    mgiproperties = mgiproperties + '&==&' + properties
        else:
    	    mgiproperties = properties

        n = (goID, mgiID, jnumID, evidence, qualifierValue, mgiassignedBy, modDate, mgiproperties)

        if n not in newannot:
	    newannot[n] = []
        if len(inferredFrom) > 0:
            newannot[n].append(inferredFrom)

    inFile.close()

    return 0

#
# write error files and close all files
#
def closeFiles():

    # write out all annotations
    for n in newannot.keys():
        inferredFrom = '|'.join(newannot[n])
        annotFile.write(annotLine % (n[0], n[1], n[2], n[3], inferredFrom, n[4], n[5], n[6], n[7]))

    # write out unique pubmed ids that are not found in MGI
    for p in pubmedUnique:
        pubmedErrorFile.write(p + '\n')

    # write out evidence code counts for unique pubmed ids that are not found in MGI
    for p in pubmedEvidence.keys():
        pubmedeviErrorFile.write(p + ':\t' + str(pubmedEvidence[p]) + '\n')

    reportlib.finish_nonps(unresolvedAErrorFile)
    reportlib.finish_nonps(unresolvedBErrorFile)
    reportlib.finish_nonps(unresolvedCErrorFile)
    reportlib.finish_nonps(mgiErrorFile)
    reportlib.finish_nonps(nopubmedFile)
    reportlib.finish_nonps(pubmedAnnotFile)
    reportlib.finish_nonps(pubmedErrorFile)
    reportlib.finish_nonps(pubmedeviErrorFile)
    reportlib.finish_nonps(dupErrorFile)
    reportlib.finish_nonps(gafFile)
    reportlib.finish_nonps(gpadFile)
    reportlib.finish_nonps(annotFile)
    reportlib.finish_nonps(uberonTextFile)
    reportlib.finish_nonps(propertiesErrorFile)

    return 0

### Helper functions ###

def queryMouseAccId(logicalDBKey, id):
    #
    # Queries mouse marker accession id of given accession id/logicalDBKey
    # 	returns list of MGI IDs
    #

    queryMouseAccIdSQL = ''' 
    	select a2.accID
    	from acc_accession a1, acc_accession a2
    	where a1._logicaldb_key = %s
    	and a1.accid = '%s'
    	and a1._object_key = a2._object_key
    	and a2._mgitype_key = 2 
    	and a2._logicaldb_key = 1 
    	and a2.prefixPart = 'MGI:'
    	and a2.preferred = 1 
    	'''

    return [r['accid'] for r in db.sql( queryMouseAccIdSQL % (logicalDBKey, id) , 'auto')]

def queryNonMouseAccId(logicalDBKey, id):
    #
    # Queries non-mouse marker of given accession id/logicalDBKey
    # 	returns marker symbol, organism
    #

    queryNonMouseAccIdSQL = ''' 
    	select m.symbol || ',' || o.commonname as symbol
    	from acc_accession a1, mrk_marker m, mgi_organism o
    	where a1._logicaldb_key = %s
    	and a1.accid = '%s'
    	and a1._object_key = m._marker_key
    	and m._organism_key != 1
    	and m._organism_key = o._organism_key
    	'''

    return [r['symbol'] for r in db.sql( queryNonMouseAccIdSQL % (logicalDBKey, id) , 'auto')]

def convertPropertiesIds(properties, uberonLookup={}):
    #
    # Converts properties ids (column 16):
    #
    # 	UBERON: -> EMAPA:, uberonLookup
    # 	ENSEMBL: -> MGI:, queryMouseAccId()
    # 	NCBI_Gene: -> MGI:, queryMouseAccId()
    # 
    #   Returns converted properties
    #   Returns list of error messages []
    #

    ensemblPrefix = 'ENSEMBL:'
    ncbiPrefix = 'NCBI_Gene:'
    uberonPrefix = 'UBERON:'
    ensembl_ldb = 60
    ncbi_ldb = 55
    
    errors = []

    pStart = properties.split('(')
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
			properties = properties.replace(e, u[0])
		# did not find uberon id
		else:
		    errors.append(UBERON_MAPPING_MISSING_ERROR % (e))

	    # found ensembl id
	    if e.find(ensemblPrefix) >= 0:
		id = e.replace(ensemblPrefix, '')
		mgiIds = queryMouseAccId(ensembl_ldb, id)
		if len(mgiIds) != 1:
		    errors.append(PROPERTIES_ACCID_INVALID_ERROR % (e))
		else:
		    properties = properties.replace(e, mgiIds[0])

	    # found ncbi id
	    elif e.find(ncbiPrefix) >= 0:
		id = e.replace(ncbiPrefix, '')
		mgiIds = queryMouseAccId(ncbi_ldb, id)
		if len(mgiIds) != 1:
		    symbol = queryNonMouseAccId(ncbi_ldb, id)
		    if len(symbol) > 0:
		        e = e + ',' + symbol[0]
		    errors.append(PROPERTIES_ACCID_INVALID_ERROR % (e))
		else:
		    properties = properties.replace(e, mgiIds[0])

	    # else, do nothing

    return properties, errors

#
# main
#

if initialize() != 0:
    sys.exit(1)

for inFileName in (os.environ['PROTEIN_SORTED'], \
	os.environ['ISOFORM_SORTED']):
    inFile = open(inFileName, 'r')
    #print inFile
    if readGAF(inFile) != 0:
        sys.exit(1)

#os.environ['COMPLEX_SORTED']
#os.environ['RNA_SORTED']

closeFiles()
sys.exit(0)
