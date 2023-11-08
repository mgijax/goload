#!/bin/sh
#
#  goload.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GO annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=goload.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GO load configuration file - gomload.config
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

COMMON_CONFIG=${GOLOAD}/goload.config

USAGE="Usage: goload.sh"

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
cp ${FROM_MGIINFILE_NAME_GZ} ${INPUTDIR}
rm -rf ${MGIINFILE_NAME_GPAD}
gunzip ${MGIINFILE_NAME_GZ}

#
# pre-process
#
cd ${INPUTDIR}
rm -rf ${INFILE_NAME_PMID}
cut -f5 ${MGIINFILE_NAME_GPAD} | sort | uniq | grep '^PMID' | cut -f2 -d":" > ${INFILE_NAME_PMID}
echo "Running pre-processing pmid" >> ${LOG}
${PYTHON} ${GOLOAD}/bin/preprocessrefs.py ${INFILE_NAME_PMID} >> ${LOG}
STAT=$?
checkStatus ${STAT} "preprocessrefs.py ${INFILE_NAME_PMID}"

cd ${OUTPUTDIR}

#
# run annotation load with an empty file to remove previous data
# not needed right now
#
echo "Running annotation load to delete existing data (GO_Central)" >> ${LOG}
rm -rf ${DATALOADSOUTPUT}/go/input/goload.annot
touch ${DATALOADSOUTPUT}/go/input/goload.annot
COMMON_CONFIG_CSH=${GOLOAD}/goannotdelete.config
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG}
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# create input file
#
echo 'Running goload.py' >> ${LOG}
${PYTHON} ${GOLOAD}/bin/goload.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/bin/goload.py"

#
# run annotation load with new annotations
#
#COMMON_CONFIG_CSH=${GOLOAD}/goannot.config
#echo "Running GO annotation load" >> ${LOG}
#echo ${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG} 
#${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG} 
#STAT=$?
#checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
#echo "Running GO inferred-from cache load" >> ${LOG}
#${MGICACHELOAD}/inferredfrom.go >> ${LOG} 
#STAT=$?
#checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.go"

#
# run eco check
#
#echo "Running GO ecocheck.sh" >> ${LOG}
#${GOLOAD}/bin/ecocheck.sh >> ${LOG}
#STAT=$?
#checkStatus ${STAT} "${GOLOAD}/bin/echocheck.sh"

#
# run postload cleanup and email logs
#
shutDown

#
# invalid reference format
#
#cd ${OUTPUTDIR}
#rm -rf pubmed.error
#grep "Invalid Reference" ${INFILE_NAME_ERROR} | grep MGI | cut -f2,3,4 -d":" | sort | uniq > pubmed.error
#grep "Invalid Reference" ${INFILE_NAME_ERROR} | grep PMID | cut -f2,3 -d":" | sort | uniq >> pubmed.error
