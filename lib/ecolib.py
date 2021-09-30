'''
#
# ecolib.py
#
# Input:
#
# ${ECOFILE} : which is the gaf-eco-mapping-derived.txt file provided by evidenceontology
#
# Output:
#
# a python dictionary of ecoId -> GO evidence code, and GO evidence code -> ecoId (default)
#
# to call from gomousenoctua.py:  
#	python dictionary = processECO()
#
# to call from command line (output will be sent to standard out)
#	ecolib.py
#    
# What it will do:
#	read eco file
#	ecoLookupByEco : ecoId -> evidence
#	ecoLookupByEvidence : evidence -> ecoId (the default ecoId of the evidence)
#
# g//s//\r/g (CTL-V, CTL-M)
#
'''

import sys 
import os

ecoLookupByEvidence = {}
ecoLookupByEco = {}

#
# Purpose: Reads the eco.obo file and returns a dictionary of:
#	ecoLookupByEco : ecoId -> evidence
#	ecoLookupByEvidence : evidence -> ecoId (the default ecoId of the evidence)
#
def processECO():
    global ecoLookupByEvidence
    global ecoLookupByEco

    oboFileName = os.environ['DATADOWNLOADS'] + \
        '/raw.githubusercontent.com/evidenceontology/evidenceontology/master/gaf-eco-mapping-derived.txt'

    oboFile = open(oboFileName, 'r')

    for line in oboFile.readlines():

        if line[0] == '#':
            continue
        if line[0] == '$':
            continue

        line = line.strip()
        tokens = line.split('\t')
        ecoId = tokens[0]
        evidence = tokens[1]
        try:
                isDefault = tokens[2].lower()
        except:
                isDefault = ''
        
        if isDefault == 'default':
            ecoLookupByEvidence[evidence] = ecoId

        ecoLookupByEco[ecoId] = evidence

    oboFile.close()

    return ecoLookupByEco, ecoLookupByEvidence

if __name__ == '__main__':

    ecoLookupByEco, ecoLookupByEvidence = processECO()

    print('rows:', len(ecoLookupByEco))
    print('rows:', len(ecoLookupByEvidence))

    for e in ecoLookupByEco:
        print(e, ecoLookupByEco[e])

    for e in ecoLookupByEvidence:
        print(e, ecoLookupByEvidence[e])
