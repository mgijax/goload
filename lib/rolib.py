'''
#
# rolib.py
#
# Input:
#
# RO file
#
# Output:
#
# a python dictionary of roName, roId
#
# to call from reports_db/daily/GO_gene_association_2.0.py
#	rolib.py
#    
# What it will do:
#	read ro file
#	roLookupByRO : roId -> name
#	roLookupByName : name -> roId
#
'''

import sys 
import os

roLookupByName = {}
roLookupByRO = {}

#
# Purpose: Reads the ro.obo file and returns a dictionary of:
#	roLookupByRO : roId -> name
#	roLookupByName : name -> roId (the default roId of the name)
#
def processRO():
    global roLookupByName
    global roLookupByRO

    oboFileName = os.environ['DATADOWNLOADS'] + '/purl.obolibrary.org/obo/ro.obo'

    oboFile = open(oboFileName, 'r')
    idValue = 'id: '
    roIdValue = 'id: RO:'
    roNameValue = 'name:'
    foundRO = 0

    for line in oboFile.readlines():

        # find [Term]
        # find id: RO:
        # find name

        if line == '[Term]':
            foundRO = 0

        elif line.find(roIdValue) >= 0:
            roId = line[4:-1]
            foundRO = 1

        elif foundRO and line.find(roNameValue) >= 0:

            roName = line[6:-1]

            if roId not in roLookupByRO:
                roLookupByRO[roId] = []
            roLookupByRO[roId].append(roName)

            if roName not in roLookupByName:
                roLookupByName[roName] = []
            roLookupByName[roName].append(roId)

        else:
            continue

    oboFile.close()

    return roLookupByRO, roLookupByName

if __name__ == '__main__':

    roLookupByRO, roLookupByName = processRO()

    print('rows:', len(roLookupByRO))
    print('rows:', len(roLookupByName))

    for e in roLookupByRO:
        print(e, roLookupByRO[e])

    for e in roLookupByName:
        print(e, roLookupByName[e])
