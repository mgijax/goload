#!/bin/sh
#
#  gocfp.sh
###########################################################################
#
#  Purpose:
#       This script creates a GO/CFP annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=gocfp.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GO/CFP load configuration file - gocfp.config
#      - input file - see python script header
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG}, ${LOG_CUR} and ${LOG_VAL}
#      - Input file: GAF Interontology (CFP)
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

COMMON_CONFIG=${GOLOAD}/gocfp/gocfp.config

USAGE="Usage: gocfp.sh"

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

# copy new file from ${DATADOWNLOADS}; not a gz file; no need to unzip
cd ${INPUTDIR}
cp ${INFILE_NAME_GZ} ${INPUTDIR}

cd ${OUTPUTDIR}

#
# create input file
#
echo 'Running gocfp.py' >> ${LOG}
${GOLOAD}/gocfp/gocfp.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/gocfp/gocfp.py"

#
# run annotation load
#
COMMON_CONFIG_CSH=${GOLOAD}/gocfp/go.csh.config
echo "Running gocfp annotation load" >> ${LOG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG}
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
echo "Running gocfp inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.gocfpload >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.gocfpload"

#
# run postload cleanup and email logs
#
shutDown

