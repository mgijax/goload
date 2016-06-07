#!/bin/sh
#
#  go.sh
#
#  Run all GOA loads from loadadmin/sundaytasks.csh
#

cd `dirname $0`

#
# Make sure the common configuration file exists and source it.
#
if [ -f ../${COMMON_CONFIG} ]
then
    . ../${COMMON_CONFIG}
else
    echo "Missing configuration file: ${COMMON_CONFIG}"
    exit 1
fi

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

#echo 'Run GO/CFP Load' | tee -a ${LOG}
#${GOLOAD}/goacfp/goacfp.sh

