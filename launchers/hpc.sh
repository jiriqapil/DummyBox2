#!/usr/bin/env bash
set -e

export PYTHONDONTWRITEBYTECODE=1

TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MASTER_LOG="${ROOT_DIR}/run_${TIMESTAMP}.log"
exec > >(tee -a "${MASTER_LOG}") 2>&1

if [ -f "${ROOT_DIR}/config.env" ]; then
    set -a
    source "${ROOT_DIR}/config.env"
    set +a
fi

# Resolve output destination path
RAW_OUT="${OUTPUT_DIR:-./demo/output}"
if [[ "$RAW_OUT" = /* ]]; then
    BASE_OUTPUT_REAL="$RAW_OUT"
else
    CLEAN_OUT="${RAW_OUT#./}"
    BASE_OUTPUT_REAL="${ROOT_DIR}/${CLEAN_OUT}"
fi

# HPC Resource Defaults - INCREASED DEFAULT MEMORY TO 4GB TO PREVENT OOM KILL
CPUS_HPC="${CPUS_HPC:-1}"
MEMORY="${MEMORY:-4gb}"
WALLTIME="${WALLTIME:-00:30:00}"

# Resolve source input path
RAW_IN="${INPUT_DIR:-./demo/input}"
if [[ "$RAW_IN" = /* ]]; then
    INPUT_SRC_REAL="$RAW_IN"
else
    CLEAN_IN="${RAW_IN#./}"
    INPUT_SRC_REAL="${ROOT_DIR}/${CLEAN_IN}"
fi

echo "=== Executing Pipeline (HPC Cluster PBS Mode) ==="
echo "Log File: ${MASTER_LOG}"
echo "Master Output Destination: ${BASE_OUTPUT_REAL}"
echo "----------------------------------------"

# Detect if running inside a container session
INSIDE_CONTAINER=false
if [ -n "$SINGULARITY_CONTAINER" ] || [ -f /.singularitybase ] || [ -f /.dockerenv ] || grep -q "docker" /proc/1/cgroup 2>/dev/null; then
    INSIDE_CONTAINER=true
fi

SPOOL_FILE="${ROOT_DIR}/batch_execution/spool_queue.sh"
rm -f "${SPOOL_FILE}"

if [ -d "${ROOT_DIR}/batch_execution" ]; then
    for batch_dir in "${ROOT_DIR}/batch_execution"/batch_*; do
        if [ -d "$batch_dir" ]; then
            BATCH_NAME=$(basename "$batch_dir")
            ABS_BATCH_DIR=$(cd "$batch_dir" && pwd)
            JOB_SCRIPT="${ABS_BATCH_DIR}/submit_${BATCH_NAME}.pbs"

            # Generate PBS submission script per batch
            cat <<EOT > "${JOB_SCRIPT}"
#!/bin/bash
#PBS -N ${BATCH_NAME}
#PBS -l select=1:ncpus=${CPUS_HPC}:mem=${MEMORY}:scratch_local=10gb
#PBS -l walltime=${WALLTIME}
#PBS -j oe
#PBS -o ${ABS_BATCH_DIR}/hpc_execution.log

set -e
export PYTHONDONTWRITEBYTECODE=1

# --- Activate Mamba Environment via Direct Absolute Path ---
module add mambaforge || true
source "\$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true
mamba activate /storage/plzen1/home/kvapij02/.conda/envs/dummybox-mamba-env

# Ensure local scratch directory exists
if [ -z "\$SCRATCHDIR" ]; then
    SCRATCHDIR=\$(mktemp -d /tmp/scratch_${BATCH_NAME}_XXXXXX)
    TRAP_CLEANUP=true
else
    TRAP_CLEANUP=false
fi

# Clean up scratch folder automatically upon exit
cleanup() {
    if [ "\$TRAP_CLEANUP" = true ]; then
        rm -rf "\$SCRATCHDIR"
    fi
}
trap cleanup EXIT

echo "\$PBS_JOBID is running on node \$(hostname -f) in scratch directory \$SCRATCHDIR"

START_TIME=\$(date +%s)

# 1. Hardcopy inputs and worker code into scratch environment
mkdir -p "\$SCRATCHDIR/demo/input"
cp -r "${INPUT_SRC_REAL}/"* "\$SCRATCHDIR/demo/input/"

cp -r "${ABS_BATCH_DIR}/helpers" "\$SCRATCHDIR/"
cp -r "${ABS_BATCH_DIR}/dummy2" "\$SCRATCHDIR/"
cp "${ABS_BATCH_DIR}/batch_manifest.txt" "\$SCRATCHDIR/"

# 2. Change directory to scratch
cd "\$SCRATCHDIR"

# Explicitly bind TASK_LIST to the isolated batch_manifest.txt in scratch
export TASK_LIST="\$SCRATCHDIR/batch_manifest.txt"
export INPUT_DIR="\$SCRATCHDIR/demo/input"
export STATIONS_PATH="\$SCRATCHDIR/demo/input/META/stations.csv"
export MSEED_PATH="\$SCRATCHDIR/demo/input/MSEED"
export ETOPO_NC="\$SCRATCHDIR/demo/input/META/ETOPO/ETOPO1_Ice_g_gmt4_cropEU.nc"
export QGIS_DIR="\$SCRATCHDIR/demo/input/META/QGIS"

TMP_OUT="\$SCRATCHDIR/tmp_output"
LOG_DIR="\$TMP_OUT/LOG"
mkdir -p "\$LOG_DIR"

python3 -B -m dummy2 2>&1 | tee "\$LOG_DIR/execution_${TIMESTAMP}.log"

# 3. Create uncompressed tar archive of outputs
TAR_NAME="${BATCH_NAME}.tar"
cd "\$TMP_OUT"
tar -cf "\$SCRATCHDIR/\${TAR_NAME}" .

# 4. Copy tar archive and stdout execution logs back to mounted target storage
BATCH_DEST="${BASE_OUTPUT_REAL}/${BATCH_NAME}"
mkdir -p "\${BATCH_DEST}"
cp "\$SCRATCHDIR/\${TAR_NAME}" "\${BATCH_DEST}/"
cp "${ABS_BATCH_DIR}/hpc_execution.log" "\${BATCH_DEST}/" 2>/dev/null || true

END_TIME=\$(date +%s)
RUNTIME=\$(( END_TIME - START_TIME ))

# 5. Log completion to master log file
echo "${BATCH_NAME},\${RUNTIME}" >> "${MASTER_LOG}"
EOT

            chmod +x "${JOB_SCRIPT}"

            if [ "$INSIDE_CONTAINER" = true ]; then
                echo "qsub ${JOB_SCRIPT}" >> "${SPOOL_FILE}"
                echo "Spooled PBS template: ${BATCH_NAME}"
            else
                qsub "${JOB_SCRIPT}"
                echo "Submitted PBS job: ${BATCH_NAME}"
            fi
        fi
    done
fi

if [ "$INSIDE_CONTAINER" = true ] && [ -f "${SPOOL_FILE}" ]; then
    chmod +x "${SPOOL_FILE}"
    echo "------------------------------------------------------------------"
    echo "CONTAINER ENVIRONMENT DETECTED:"
    echo "Batch job scripts prepared and spooled to batch_execution/spool_queue.sh."
    echo ""
    echo "To dispatch all jobs to the cluster scheduler, run on host login node:"
    echo "bash batch_execution/spool_queue.sh"
    echo "------------------------------------------------------------------"
fi

echo "=== HPC batch preparation completed ==="
