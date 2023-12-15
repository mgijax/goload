#!/bin/sh
#
#  goload.sh
###########################################################################
#
#  Purpose:
# 	This script creates a GO annotation load input file 
#       and invokes the annotload using that input file.
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
# There should be a "lastrun" file in the input directory that was created
# the last time the load was run for this input file. If this file exists
# and is more recent than the input file, the load does not need to be run.
#
#LASTRUN_FILE=${INPUTDIR/lastrun
#if [ -f ${LASTRUN_FILE} ]
#then
#    if test ${LASTRUN_FILE} -nt ${FROM_MGIINFILE_NAME_GZ}
#    then
#        echo "Input file has not been updated - skipping load" | tee -a ${GOLOG}
#        echo 'shutting down'
#        exit 0
#    fi
#fi

#
# gunzip the gz file
#
#cp ${FROM_MGIINFILE_NAME_GZ} ${MGIINFILE_NAME_GZ}
#cd ${INPUTDIR}
#gunzip ${MGIINFILE_NAME_GZ}

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

# 
# this proisoform/marker annotations are used by the reports_db/daily/GO_gpi.py
#
echo "Runnning proisoformload"
${PROISOFORMLOAD}/bin/proisoform.sh
STAT=$?
checkStatus ${STAT} "proisoformload process"

echo "Generate ${PUBREPORTDIR}/output/mgi.gpi"
REPORTOUTPUTDIR=${PUBREPORTDIR}/output;export REPORTOUTPUTDIR
${PYTHON} ${PUBRPTS}/daily/GO_gpi.py
STAT=$?
checkStatus ${STAT} "create ${PUBREPORTDIR}/output/mgi.gpi file"

#
# copy new file from ${DATADOWNLOADS} and unzip
#
echo "Copying new file from ${FROM_MGIINFILE_NAME_GZ} to ${INPUTDIR}" >> ${LOG}
cd ${INPUTDIR}
cp ${FROM_MGIINFILE_NAME_GZ} ${INPUTDIR}
rm -rf ${MGIINFILE_NAME_GPAD}
gunzip ${MGIINFILE_NAME_GZ}

#
# pre-process
#
echo "Running pre-processing pmid" >> ${LOG}
cd ${INPUTDIR}
rm -rf ${INFILE_NAME_PMID}
cut -f5 ${MGIINFILE_NAME_GPAD} | sort | uniq | grep '^PMID' | cut -f2 -d":" > ${INFILE_NAME_PMID}
${PYTHON} ${GOLOAD}/bin/preprocessrefs.py ${INFILE_NAME_PMID} >> ${LOG}
STAT=$?
checkStatus ${STAT} "preprocessrefs.py ${INFILE_NAME_PMID}"

# move to the ${OUTPUTDIR}
cd ${OUTPUTDIR}

#
# run annotation load with an empty file to remove previous data
# not needed right now
#
echo "Running annotation load to delete existing data (_annottype_key = 1000)" >> ${LOG}
rm -rf ${INPUTDIR}/goload.annot
touch ${INPUTDIR}/goload.annot
COMMON_CONFIG_CSH=${GOLOAD}/goannotdelete.config
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG}
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# create input file
#
echo "Running goload.py" >> ${LOG}
${PYTHON} ${GOLOAD}/bin/goload.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/bin/goload.py"
rm -rf ${PUBMED_ERROR}.sort
sort ${PUBMED_ERROR} | uniq > ${PUBMED_ERROR}.sort
mv ${PUBMED_ERROR}.sort ${PUBMED_ERROR}

#
# run annotation load with new annotations
#
COMMON_CONFIG_CSH=${GOLOAD}/goannot.config
echo "Running GO annotation load" >> ${LOG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
echo "Running GO inferred-from cache load" >> ${LOG}
${GOLOAD}/bin/inferredfrom.sh >> ${LOG} 
STAT=$?
checkStatus ${STAT} "inferredfrom.sh"

#
# run eco check
# comment out unless we keep finding ECO issues
#
#echo "Running GO ecocheck.sh" >> ${LOG}
#${GOLOAD}/bin/ecocheck.sh >> ${LOG}
#STAT=$?
#checkStatus ${STAT} "${GOLOAD}/bin/echocheck.sh"

#
# run go_annot_extensions_display.sh
#
echo "Running go_annot_extensions_display.sh" >> ${LOG}
${GOLOAD}/bin/go_annot_extensions_display.sh
STAT=$?
checkStatus ${STAT} "${GOLOAD}/go_annot_extensions_display.sh"

#
# run go_isoforms_display.sh
#
echo "Running go_isoforms_display.sh" >> ${LOG}
${GOLOAD}/bin/go_isoforms_display.sh 
STAT=$?
checkStatus ${STAT} "${GOLOAD}/go_isoforms_display.sh"

#
# run BIB_updateWFStatusGO()
#
echo "Running BIB_updateWFStatusGO" >> ${LOG}
cat - <<EOSQL | ${PG_DBUTILS}/bin/doisql.csh $0
select BIB_updateWFStatusGO();
EOSQL

#
# set new LASTRUN_FILE 
#
touch ${LASTRUN_FILE}

#
# run postload cleanup and email logs
#
shutDown

