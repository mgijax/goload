#!/bin/sh
#
#  gorefgen.sh
###########################################################################
#
#  Purpose:
#       This script creates a GO/PAINT annotation load
#       input file and invokes the annotload using that input file.
#
#  Usage=gorefgen.sh
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#               /usr/local/mgi/live/mgiconfig/master.config.sh
#      - GO/PAINT load configuration file - gorefgen.config
#      - input file - see python script header
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG}, ${LOG_CUR} and ${LOG_VAL}
#      - Input file: GO-GAF RefGen
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
# lec	03/03/2010 - TR9962
#

cd `dirname $0`

COMMON_CONFIG=${GOLOAD}/gorefgen/gorefgen.config

USAGE="Usage: gorefgen.sh"

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
# Verify the time stamp on the current data download file vs. the file in the input directory
# If the current input file exists and is more recent than the downloaded file, 
# the load does not need to be run.
#
#LASTFILE=${INFILE_NAME}
#if [ -f ${LASTFILE} ]
#then
#    if /usr/local/bin/test ${LASTFILE} -nt ${INFILE_NAME_GOREFGENGAF}
#    then
#        echo "The most recent GO/RefGen download file has been copied - skipping load" >> ${LOG}
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
echo 'Running gorefgen.py' >> ${LOG}
${PYTHON} ${GOLOAD}/gorefgen/gorefgen.py >> ${LOG}
STAT=$?
checkStatus ${STAT} "${GOLOAD}/gorefgen/gorefgen.py"

#
# run annotation load
#
COMMON_CONFIG_CSH=${GOLOAD}/gorefgen/go.csh.config
echo "Running gorefgen annotation load" >> ${LOG}
${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go >> ${LOG}
STAT=$?
checkStatus ${STAT} "${ANNOTLOADER_CSH} ${COMMON_CONFIG_CSH} go"

#
# run inferred-from cache
#
echo "Running gorefgen inferred-from cache load" >> ${LOG}
${MGICACHELOAD}/inferredfrom.gorefgenload >> ${LOG} 
STAT=$?
checkStatus ${STAT} "${MGICACHELOAD}/inferredfrom.gorefgenload"

#
# run postload cleanup and email logs
#
shutDown

