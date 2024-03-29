'''
#
# uberonlib.py
#
# Input:
#
# ${UBERONFILE} : which is the uberon.obo file installed in ${DATADOWNLOADS} directory
#
# Output:
#
# convert UBERON ids in extensions/properties from gpad/gaf file to EMAPA
#
# from a gpad file, column 11 (extensions)
# from a gaf file, colum 16 (properties)
#
# 	UBERON: -> EMAPA:
#    
'''

import sys 
import os
import db

# uberon formatted file
uberonFileName = None
# uberon file pointer
uberonFile = None

# uberon text formatted file
uberonTextFileName = None
# uberon text file pointer
uberonTextFile = None

uberonLookup = {}

UBERON_MAPPING_MULTIPLES_ERROR = "uberon id has > 1 emapa : %s\t%s"
UBERON_MAPPING_MISSING_ERROR = "uberon id not found or missing emapa id: %s" 

def processUberon():

    uberonFileName = os.environ['UBERONFILE']
    uberonTextFileName = os.environ['UBERONTEXTFILE']
    uberonFile = open(uberonFileName, 'r')
    uberonTextFile = open(uberonTextFileName, 'w')

    #
    # read/store UBERON-to-EMAPA info
    #

    print('reading uberon -> emapa translation file')

    #
    # read/store list of primary EMAPA ids
    #
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

    idValue = 'id: '
    uberonIdValue = 'id: UBERON:'
    emapaXrefValue = 'xref: EMAPA:'
    foundUberon = 0

    for line in uberonFile.readlines():

        # find [Term]
        # find xref: EMAPA:

        if line == '[Term]':
            foundUberon = 0

        elif line[:11] == uberonIdValue:
            uberonId = line[4:-1]
            foundUberon = 1

        elif foundUberon and line[:12] == emapaXrefValue:

            emapaId = line[6:-1]

            # only convert to primary EMAPA
            if emapaId not in primaryEmapa:
                continue

            if uberonId not in uberonLookup:
                uberonLookup[uberonId] = []
            uberonLookup[uberonId].append(emapaId)

        else:
            continue

    for u in uberonLookup:
        uberonTextFile.write(u + '\n')

    uberonFile.close()
    uberonTextFile.close()

    return uberonLookup

#
# Purpose: Converts extensions : UBERON: -> EMAPA
#
def convertExtensions(extensions, uberonLookup={}):
    #
    # Converts extensions ids
    #
    # 	UBERON: -> EMAPA:
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

if __name__ == '__main__':

    uberonLookup = processUberon()

    print('rows:', len(uberonLookup))

    for u in uberonLookup:
        print(u, uberonLookup[u])
