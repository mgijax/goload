#!/bin/sh
#
#  goamouse.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GOAHUMAN annotation load
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
#      - GOAHUMAN load configuration file - goamouse.config
#      - input file - see python script header
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG_DIAG}, ${LOG_CUR} and ${LOG_VAL}
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

COMMON_CONFIG=goamouse.config

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
LOG=${LOG_FILE}
rm -rf ${LOG}
touch ${LOG}

#
#  Source the DLA library functions.
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
preload ${OUTPUTDIR}

# remove old files
rm -rf ${INFILE_NAME_GOAGAF}

# copy new file from ${DATADOWNLOADS} and unzip
cd ${INPUTDIR}
cp ${INFILE_NAME_GZ} ${INPUTDIR}
rm -rf ${INFILE_NAME_GOAGAF}
gunzip ${INFILE_NAME_GOAGAF} >> ${LOG_DIAG}
rm -rf ${INFILE_NAME_GOASORTED} >> ${LOG_DIAG}
# important to sort the file so we can collapse "duplicate" lines
sort -k2,7 ${INFILE_NAME_GOAGAF} > ${INFILE_NAME_GOASORTED}

cd ${OUTPUTDIR}

#
# run annotation load with an empty file to remove previous data
#
echo "Running GOA/Mouse annotation load (previous data)" >> ${LOG_DIAG}
rm -rf ${ANNOTINPUTFILE}
touch ${ANNOTINPUTFILE}
COMMON_CONFIG_CSH=${GOLOAD}/goamouse/goadelete.csh.config
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse"

#
# create input file
#
echo 'Running goamouse.py' >> ${LOG_DIAG}
${GOLOAD}/goamouse/goamouse.py >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/goamouse/goamouse.py"

#
# run annotation load with new annotations
#
COMMON_CONFIG_CSH=${GOLOAD}/goamouse/goa.csh.config
echo "Running GOA/Mouse annotation load" >> ${LOG_DIAG}
echo ${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG_DIAG} 
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goamouse"

#
# run inferred-from cache
#
echo "Running GOA/Mouse inferred-from cache load" >> ${LOG_DIAG}
${MGICACHELOAD}/inferredfrom.goaload >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.goamouse"

#
# run postload cleanup and email logs
#
shutDown

