#!/bin/sh
#
#  goarat.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GORAT annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=goarat.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GORAT load configuration file - goarat.config
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

COMMON_CONFIG=goarat.config

USAGE="Usage: goarat.sh"

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

#
# commenting out 8/19/2010 to force the run
# Verify the time stamp on the current data download file vs. the unzipped file
# If the current unzipped file exists and is more recent than the downloaded file, 
# the load does not need to be run.
#
#LASTUNZIP_FILE=${INPUTDIR}/${INFILE_NAME_RATGAF}
#if [ -f ${LASTUNZIP_FILE} ]
#then
#    if /usr/local/bin/test ${LASTUNZIP_FILE} -nt ${INFILE_NAME_GZ}
#    then
#        echo "The most recent GO/Rat download file has been unzipped - skipping load" >> ${LOG}
#	exit 1
#    fi
#fi

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

cd ${OUTPUTDIR}

#
#
# create input file
#
echo 'Running goarat.py' >> ${LOG_DIAG}
${GOLOAD}/goarat/goarat.py >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/goarat/goarat.py"

#
# run annotation load
#

COMMON_CONFIG_CSH=${GOLOAD}/goa.csh.config
echo "Running GO/RAT annotation load" >> ${LOG_DIAG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goarat >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goarat"

#
# run inferred-from cache
#

echo "Running GO/RAT inferred-from cache load" >> ${LOG_DIAG}
${MGICACHELOAD}/inferredfrom.goaratload >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.goaratload"

#
# run postload cleanup and email logs
#
shutDown

