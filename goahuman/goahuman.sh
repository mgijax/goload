#!/bin/sh
#
#  goahuman.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GOA/Human annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=goahuman.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GOA/Human load configuration file - goahuman.config
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

COMMON_CONFIG=${GOLOAD}/goahuman/goahuman.config

USAGE="Usage: goahuman.sh"

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
echo 'Running goahuman.py' >> ${LOG}
${GOLOAD}/goahuman/goahuman.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/goahuman/goahuman.py"

#
# run annotation load
#
COMMON_CONFIG_CSH=${GOLOAD}/goahuman/goa.csh.config
echo "Running GOA/Human annotation load" >> ${LOG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} goahuman >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
echo "Running GOA/Human inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.goahumanload >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.goahumanload"

#
# run postload cleanup and email logs
#
shutDown

