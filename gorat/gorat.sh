#!/bin/sh
#
#  gorat.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GO/Rat annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=gorat.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GO/Rat load configuration file - gorat.config
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

COMMON_CONFIG=${GOLOAD}/gorat/gorat.config

USAGE="Usage: gorat.sh"

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
cp ${INFILE_NAME_GZ} ${INPUTDIR}
rm -rf ${INFILE_NAME_GAF}
gunzip ${INFILE_NAME_GAF} >> ${LOG}

cd ${OUTPUTDIR}

#
# create input file
#
echo 'Running gorat.py' >> ${LOG}
${GOLOAD}/gorat/gorat.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/gorat/gorat.py"

#
# run annotation load
#
COMMON_CONFIG_CSH=${GOLOAD}/gorat/go.csh.config
echo "Running GO/RAT annotation load" >> ${LOG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gorat >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gorat"

#
# run inferred-from cache
#
echo "Running GO/RAT inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.goratload >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.goratload"

#
# run postload cleanup and email logs
#
shutDown

