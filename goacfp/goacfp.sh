#!/bin/sh
#
#  goacfp.sh
###########################################################################
#
#  Purpose:
#       This script creates a GOA/CFP annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=goacfp.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GOA/CFP load configuration file - goacfp.config
#      - input file - see python script header
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG_DIAG}, ${LOG_CUR} and ${LOG_VAL}
#      - Input file: GAF Interontology (GOA/CFP)
#      - Output file: annotload
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
# lec	03/03/2010 - TR10011
#

cd `dirname $0`

COMMON_CONFIG=${GOLOAD}/goacfp/goacfp.config

USAGE="Usage: goacfp.sh"

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

# copy new file from ${DATADOWNLOADS}; not a gz file; no need to unzip
cd ${INPUTDIR}
cp ${INFILE_NAME_GZ} ${INPUTDIR}

cd ${OUTPUTDIR}

#
# create input file
#
echo 'Running goacfp.py' >> ${LOG_DIAG}
${GOLOAD}/goacfp/goacfp.py >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/goacfp/goacfp.py"

#
# run annotation load
#
COMMON_CONFIG_CSH=${GOLOAD}/goacfp/goa.csh.config
echo "Running goacfp annotation load" >> ${LOG_DIAG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG_DIAG}
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
echo "Running goacfp inferred-from cache load" >> ${LOG_DIAG}
${MGICACHELOAD}/inferredfrom.gocfpload >> ${LOG_DIAG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.gocfpload"

#
# run postload cleanup and email logs
#
shutDown

