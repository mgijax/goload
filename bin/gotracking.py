'''
#
# gotracking.py
#
#       The purpose of this script is to:
#               add GO_Tracking record for Marker if one does not exist
#
# History:
#
# lec   12/21/2023
#       wts2-1155/GOC taking over GOA mouse, GOA human, etc.
#
'''

import sys 
import os
import db

db.setTrace()

# create new go_trackin records

results = db.sql('''
        select distinct m._marker_key, m.symbol
        from mrk_marker m, voc_annot a
        where m._marker_key = a._object_key
        and a._annottype_key = 1000
        and not exists (select 1 from go_tracking g where m._marker_key = g._marker_key)
        order by m.symbol
        ''', 'auto')

updateSQL = ''
for r in results:
        key = r['_marker_key']
        updateSQL += 'insert into GO_Tracking values(%s,0,null,1001,1001,null,now(),now());\n' % (key)

if len(updateSQL) > 0:
        #print(updateSQL)
        db.sql(updateSQL, None)
        db.commit()

# delete go_tracking records
results = db.sql('''
        select m._marker_key, m.symbol, g.*
        from mrk_marker m, go_tracking g
        where m._marker_key = g._marker_key
        and not exists (select 1 from voc_annot a
                where m._marker_key = a._object_key
                and a._annottype_key = 1000
        )
        ''', 'auto')

deleteSQL = ''
for r in results:
        key = r['_marker_key']
        deleteSQL += 'delete from go_tracking where _marker_key = %s;\n' % (key)

if len(deleteSQL) > 0:
        #print(deleteSQL)
        db.sql(deleteSQL, None)
        db.commit()


