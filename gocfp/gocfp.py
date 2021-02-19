'''
#
# gocfp.py
#
#	See http://prodwww.informatics.jax.org/wiki/index.php/sw:Goload
#
# Inputs:
#
#       ${INFILE_NAME_GAF}	the GAF file
#
# 	The GAF file contains:
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
#	${INFILE_NAME}	        the file that will be used to load the annotations
#	${INFILE_NAME_ERROR}	error file for reporting invalid references
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
#	TR 10011
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
#       gocfp.py
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
import db

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

    results = db.sql('''select mgiID, pubmedID, jnumID from BIB_Citation_Cache ''', 'auto')
    for r in results:
        mgiRefLookup[r['mgiID']] = r['jnumID']

        if r['pubmedID'] != '':
            mgiRefLookup[r['pubmedID']] = r['jnumID']

    return 0

#
# Purpose: Read GAF file and generate Annotation file
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
    annotLine = '%s\t%s\t%s\t%s\t%s\t\t%s\t%s\t\t\t\n' 

    for line in inFile.readlines():

        if line[0] == '!':
            continue

        tokens = str.split(line[:-1], '\t')

        databaseID = tokens[0]
        mgiID = tokens[1]
        goID = tokens[4]
        references = str.split(tokens[5], '|')
        evidenceCode = tokens[6]
        inferredFrom = str.replace(tokens[7], 'MGI:MGI:', 'MGI:')
        modDate = tokens[13]

        # don't use this field
        #createdBy = tokens[14]

        jnumIDFound = 0

        # translate references (MGI/PMID) to J numbers (J:)
        # use the first J: match that we find
        for r in references:

            refID = str.replace(r, 'MGI:MGI:', 'MGI:')
            refID = str.replace(refID, 'PMID:', '')

            if refID in mgiRefLookup:
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
