#!/bin/sh
#
#  goamouse.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GOA/Mouse annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=goamouse.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GOA/Mouse load configuration file - goamouse.config
#      - input file - see python script header
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG}, ${LOG_CUR} and ${LOG_VAL}
#      - Input file for annotload
#      - see annotload outputs
#      - Records written to the database tables
#      - Exceptions written to standard error
#      - Configuration and initialization errors are written to a log file
#        for the shell script
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal error occurred
#      2:  Non-fatal error occurred
#
#  Assumes:  Nothing
#
# History:
#
# lec	02/16/2010 - TR10035
#

cd `dirname $0`

COMMON_CONFIG=${GOLOAD}/goamouse/goamouse.config

USAGE="Usage: goamouse.sh"

#
# Make sure the common configuration file exists and source it.
#
if [ -f ${COMMON_CONFIG} ]
then
    . ${COMMON_CONFIG}
else
    echo "Missing configuration file: ${COMMON_CONFIG}"
    exit 1
fi

#
# Initialize the log file.
#
LOG=${LOG_DIAG}
rm -rf ${LOG}
touch ${LOG}

#
# Source the DLA library functions.
#
if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}" | tee -a ${LOG}
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined." | tee -a ${LOG}
    exit 1
fi

#####################################
#
# Main
#
#####################################

#
# createArchive including OUTPUTDIR, startLog, getConfigEnv
# sets "JOBKEY"
#
preload ${OUTPUTDIR}

# copy new file from ${DATADOWNLOADS} and unzip
cd ${INPUTDIR}

#
# important to sort the files so we can collapse "duplicate" lines
#

cp ${PROTEIN_GZ} ${INPUTDIR}
rm -rf ${PROTEIN_GAF}
gunzip ${PROTEIN_GAF} >> ${LOG}
rm -rf ${PROTEIN_SORTED} >> ${LOG}
sort -k2,7 ${PROTEIN_GAF} > ${PROTEIN_SORTED}

cp ${ISOFORM_GZ} ${INPUTDIR}
rm -rf ${ISOFORM_GAF}
gunzip ${ISOFORM_GAF} >> ${LOG}
rm -rf ${ISOFORM_SORTED} >> ${LOG}
sort -k2,7 ${ISOFORM_GAF} > ${ISOFORM_SORTED}

cd ${OUTPUTDIR}

#
# run annotation load with an empty file to remove previous data
#
echo "Running GOA/Mouse annotation load (previous data)" >> ${LOG}
rm -rf ${ANNOTINPUTFILE}
touch ${ANNOTINPUTFILE}
COMMON_CONFIG_CSH=${GOLOAD}/goamouse/goadelete.csh.config
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse"

#
# create input file
#
echo 'Running goamouse.py' >> ${LOG}
${GOLOAD}/goamouse/goamouse.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/goamouse/goamouse.py"

#
# run annotation load with new annotations
#
COMMON_CONFIG_CSH=${GOLOAD}/goamouse/goa.csh.config
echo "Running GOA/Mouse annotation load" >> ${LOG}
echo ${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG} 
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse"

#
# run inferred-from cache
#
echo "Running GOA/Mouse inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.goaload >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.goamouse"

#
# run postload cleanup and email logs
#
shutDown

