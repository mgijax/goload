#!/bin/sh
#
#  go.sh
#
#  Run all GOA loads from loadadmin/sundaytasks.csh
#

cd `dirname $0`

#
# Initialize the log file.
#
LOG=${LOG_FILE}
rm -rf ${LOG}
touch ${LOG}

echo 'Run GOA Load' | tee -a ${LOG}
${GOLOAD}/goamouse/goamouse.sh

echo 'Run GO/Rat Load' | tee -a ${LOG}
${GOLOAD}/goarat/goarat.sh

echo 'Run GO/PAINT Load' | tee -a ${LOG}
${GOLOAD}/goarefgen/goarefgen.sh

echo 'Run GOA/Human Load' | tee -a ${LOG}
${GOLOAD}/goahuman/goahuman.sh

echo 'Run GO/CFP Load' | tee -a ${LOG}
${GOLOAD}/goacfp/goacfp.sh

