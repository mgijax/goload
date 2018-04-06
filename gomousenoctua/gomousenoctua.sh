#!/bin/sh
#
#  gomousenoctua.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GO/Mouse annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=gomousenoctua.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GO/Mouse load configuration file - gomousenoctua.config
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

COMMON_CONFIG=${GOLOAD}/gomousenoctua/gomousenoctua.config

USAGE="Usage: gomousenoctua.sh"

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
cp ${MGIINFILE_NAME_GZ} ${INPUTDIR}
cp ${PRINFILE_NAME_GZ} ${INPUTDIR}

# temporary fix
# TR12664/rename lego-model-id to noctua-model-id 
# remove when noctua-model-id goes live
mv mgi.gpad mgi.gpad.orig
sed 's/lego-model-id/noctua-model-id/g' mgi.gpad.orig > mgi.gpad

cd ${OUTPUTDIR}

#
# run annotation load with an empty file to remove previous data
# not needed right now
#
#echo "Running GOA/Mouse annotation load (previous data)" >> ${LOG}
#rm -rf ${ANNOTINPUTFILE}
#touch ${ANNOTINPUTFILE}
#COMMON_CONFIG_CSH=${GOLOAD}/gomousenoctua/godelete.csh.config
#${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gomousenoctua >> ${LOG} 
#STAT=$?
#checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gomousenoctua"

#
# create input file
#
echo 'Running gomousenoctua.py' >> ${LOG}
${GOLOAD}/gomousenoctua/gomousenoctua.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/gomousenoctua/gomousenoctua.py"

#
# run annotation load with new annotations
#
COMMON_CONFIG_CSH=${GOLOAD}/gomousenoctua/go.csh.config
echo "Running GO/Mouse/Noctua annotation load" >> ${LOG}
echo ${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gomousenoctua >> ${LOG} 
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gomousenoctua >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} gomousenoctua"

#
# run inferred-from cache
#
echo "Running GO/Mouse/Noctua inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.gomousenoctua >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.gomousenoctua"

#
# run eco check
#
echo "Running GO/Mouse/Noctua ecocheck.sh" >> ${LOG}
${GOLOAD}/gomousenoctua/ecocheck.sh >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/gomousenoctua/echocheck.sh"

#
# run postload cleanup and email logs
#
shutDown

