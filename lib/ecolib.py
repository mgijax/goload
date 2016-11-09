#!/usr/local/bin/python

'''
#
# ecolib.py
#
# Input:
#
# ${ECOFILE} : which is the eco.obo file installed in ${DATADOWNLOADS} directory
#
# Output:
#
# a python dictionary of eco ID -> GO evidence code
#
# to call from gomousenoctua.py:  
#	python dictionary = processECO()
#
# to call from command line (output will be sent to standard out)
#	ecolib.py
#    
# What it will do:
#	read eco.obo file
#	find the GO evidence code for each top-level ECO id
#	find the parent (is_a) of each ECO id
#	find the associated GO evidence code of each ECO id 
#		by recursively iterating thru ECO id parent(s)
#
# What it will not do:
#	does not store the ECO ids in the vocabulary tables
#	does not store the ECO DAG in the DAG tables
# 
'''

import sys 
import os

#
# class to store the node information
#
class Node:
    def __init__ (self, ecoId):
        self.ecoId = ecoId
	self.name = ''
	self.evidence = []
	self.parentId = []
		
    def toString (self):
        return '%s|%s|%s|%s\n' % (self.ecoId, self.evidence, self.parentId, self.name)

#
# the nodes of interest from the obo file
#
nodeLookup = {}

#
# hard-coding the default evidence->eco
# hard-coding the default eco->evidence
#
# only using the eco.obo file to handle the onotology/dag
#
ecoLookupByEvidence = {
'EXP': 'ECO:0000269',
'IBA': 'ECO:0000318',
'IBD': 'ECO:0000319',
'IC':  'ECO:0000305',
'IDA': 'ECO:0000314',
'IEA': 'ECO:0000501',
'IEP': 'ECO:0000270',
'IGC': 'ECO:0000317',
'IGI': 'ECO:0000316',
'IKR': 'ECO:0000320',
'IMP': 'ECO:0000315',
'IMR': 'ECO:0000320',
'IPI': 'ECO:0000353',
'IRD': 'ECO:0000321',
'ISA': 'ECO:0000247',
'ISM': 'ECO:0000255',
'ISO': 'ECO:0000266',
'ISS': 'ECO:0000250',
'NAS': 'ECO:0000303',
'ND':  'ECO:0000307',
'RCA': 'ECO:0000245',
'TAS': 'ECO:0000304'
}

ecoLookupByEco = {
'ECO:0000269':['EXP'],
'ECO:0000318':['IBA'],
'ECO:0000319':['IBD'],
'ECO:0000305':['IC'],
'ECO:0000314':['IDA'],
'ECO:0000501':['IEA'],
'ECO:0000270':['IEP'],
'ECO:0000317':['IGC'],
'ECO:0000316':['IGI'],
'ECO:0000320':['IKR'],
'ECO:0000315':['IMP'],
'ECO:0000320':['IMR'],
'ECO:0000353':['IPI'],
'ECO:0000321':['IRD'],
'ECO:0000247':['ISA'],
'ECO:0000255':['ISM'],
'ECO:0000266':['ISO'],
'ECO:0000250':['ISS'],
'ECO:0000303':['NAS'],
'ECO:0000307':['ND'],
'ECO:0000245':['RCA'],
'ECO:0000304':['TAS']
}

#
# Purpose: Reads the eco.obo file and returns a dictionary of:
#	ecoLookupByEco : ecoId -> evidence
#	ecoLookupByEvidence : evidence -> ecoId (the default ecoId of the evidence)
#
def processECO():

    oboFileName = os.environ['DATADOWNLOADS'] + '/purl.obolibrary.org/obo/eco/eco.obo'
    oboFile = open(oboFileName, 'r')

    startTag = '[Term]'
    endTag = ''
    ecoTag = 'id: ECO:'
    idTag = 'id: '

    startTerm = 0
    foundTerm = 0
    addToLookup = 0

    #
    # load terms into nodeLookup
    #

    for line in oboFile.readlines():

	line = line.strip()

	# 
	# start of term
	#
	if line.find(startTag) == 0:
	    startTerm = 1
	    foundTerm = 0
            addToLookup = 0
	    continue

	#
	# end of term
	#
	if startTerm and len(line) == 0:

	    #
	    # if nodeLookup already exist for this term, then use it
	    #
	    try:
		if foundTerm and addToLookup:
	            nodeLookup[n.ecoId] = n
	    except:
	    	pass

	    startTerm = 0
	    foundTerm = 0
            addToLookup = 0
	    continue

	if not startTerm:
		continue

 	if line.find(ecoTag) == 0:

	    ignoreit, ecoId = line.split(idTag)

	    #
	    # ecoId may be in both obo files
	    #
	    if ecoId in nodeLookup:
	        n = nodeLookup[ecoId]
	    else:
	        n = Node(ecoId)
                n.ecoId = ecoId

	    # if ecoId like 'xxxx-1', then attach 'xxxx' as parent
	    try:
	    	nodeParent, ignoreit = ecoId.split('-')
		if nodeParent not in n.parentId:
    	            n.parentId.append(nodeParent)
	    except:
	        pass

	    foundTerm = 1
	    continue

	#
	# could not find Term
	#
	if not foundTerm:
	    continue

	#
	# continue adding info into nodeLookup...
	#

        if line.find('name:') == 0:
            n.name = line[6:]

        #
        # xref: GOECO:xxxx "xxxx"
        #
        elif line.find('xref: GOECO:') == 0:
            tokens = line.split(' ')
            evidence = tokens[1].replace('GOECO:', '')
            n.evidence.append(evidence)
	    addToLookup = 1
	    #print n.ecoId, line


        elif line.find('synonym:') == 0:
            if line.find('EXACT [GO:') >= 0:
                tokens = line.split('[GO:')
                evidence = tokens[1].replace(']', '')
                n.evidence.append(evidence)
                addToLookup = 1 
                #print n.ecoId, line

        #
	# list of typs of "tags" that need to be included in nodeLookup
	#
	# is_a
	# union_of : ignore, do not use these, they are circular
	#
	elif line.find('is_a: ECO:') == 0:
	    tokens = line.split(' ')
	    parentId = tokens[1]

	    if parentId not in n.parentId:
    	        n.parentId.append(parentId)

	    addToLookup = 1

	#
	# if obsolete, do not add to lookup
	#
	elif line.find('is_obsolete: true') >= 0:
	    addToLookup = 0

    # last record
    try:
	if addToLookup:
	    nodeLookup[n.ecoId] = n
    except:
        pass

    oboFile.close()

    return generateLookup()

#
# Purpose: Recursive function that iterates thru parentId
#          until it finds a parent that contains an evidence
#
def findEvidenceByParent(n):

    evidence = ''

    # for each parentId in the node

    for p1 in n.parentId:

	# get the node of the parentId
	if p1 not in nodeLookup:
	    continue

	p2 = nodeLookup[p1]

	# does the node contain an evidence?
	# if not, keep looking

	if len(p2.evidence) == 0:
	    evidence = findEvidenceByParent(p2)

	# else, we are done
	else:
	    evidence = p2.evidence
            return evidence

    return evidence

#
# Purpose: To return a dictionary of:
#	ecoLookupByEco : ecoId -> evidence
#	ecoLookupByEvidence : evidence -> ecoId (the default ecoId of the evidence)
#
def generateLookup():
    global ecoLookupByEvidence
    global ecoLookupByEco

    for r in nodeLookup:

	n = nodeLookup[r]

	# only add if we find a "new" evidence in the obo file
	# which should not happen
	for evidence in n.evidence:
	    if len(evidence) > 0:
	        if evidence not in ecoLookupByEvidence:
	            ecoLookupByEvidence[evidence] = n.ecoId
	            ecoLookupByEco[n.ecoId] = evidence

	#
	# use the ontology/dag to find the evidence
	# for eco ids that are not the defaults
	#
	evidence = findEvidenceByParent(n)

	if len(evidence) > 0:
	    if n.ecoId not in ecoLookupByEco:
	        ecoLookupByEco[n.ecoId] = evidence

    return ecoLookupByEco, ecoLookupByEvidence

if __name__ == '__main__':

    ecoLookupByEco, ecoLookupByEvidence = processECO()

    print 'rows:', len(ecoLookupByEco)
    print 'rows:', len(ecoLookupByEvidence)

    for e in ecoLookupByEco:
        print e, ecoLookupByEco[e][0]

    for e in ecoLookupByEvidence:
        print ecoLookupByEvidence[e], e

