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
RAW_OUT="${OUTPUT_DIR:-./output}"
if [[ "$RAW_OUT" = /* ]]; then
    BASE_OUTPUT_REAL="$RAW_OUT"
else
    CLEAN_OUT="${RAW_OUT#./}"
    BASE_OUTPUT_REAL="${ROOT_DIR}/${CLEAN_OUT}"
fi

# HPC Resource Defaults
CPUS_HPC="${CPUS_HPC:-1}"
MEMORY="${MEMORY:-4gb}"
WALLTIME="${WALLTIME:-00:30:00}"

# Resolve explicit input paths from config or default relative to ROOT_DIR
RAW_IN="${INPUT_DIR:-./input}"
if [[ "$RAW_IN" = /* ]]; then
    INPUT_SRC_REAL="$RAW_IN"
else
    CLEAN_IN="${RAW_IN#./}"
    INPUT_SRC_REAL="${ROOT_DIR}/${CLEAN_IN}"
fi

RAW_MSEED="${MSEED_PATH:-${INPUT_SRC_REAL}/MSEED}"
if [[ "$RAW_MSEED" = /* ]]; then
    MSEED_SRC_REAL="$RAW_MSEED"
else
    CLEAN_MSEED="${RAW_MSEED#./}"
    MSEED_SRC_REAL="${ROOT_DIR}/${CLEAN_MSEED}"
fi

RAW_STATIONS="${STATIONS_PATH:-${INPUT_SRC_REAL}/META/stations.csv}"
if [[ "$RAW_STATIONS" = /* ]]; then
    STATIONS_SRC_REAL="$RAW_STATIONS"
else
    CLEAN_STATIONS="${RAW_STATIONS#./}"
    STATIONS_SRC_REAL="${ROOT_DIR}/${CLEAN_STATIONS}"
fi

# Capture Active Frontend Host Python & PATH for Native Execution Mode
ACTIVE_PATH="${PATH}"
ACTIVE_PYTHON="$(command -v python3 || command -v python || echo "python3")"

# Resolve SIF Image Name dynamically from PACKAGE_NAME or locate any *.sif file
SIF_NAME="${PACKAGE_NAME:-dummybox2}.sif"
if [ -f "${ROOT_DIR}/${SIF_NAME}" ]; then
    SIF_IMAGE="${ROOT_DIR}/${SIF_NAME}"
else
    # Fallback: Pick the first .sif file found in ROOT_DIR
    SIF_IMAGE=$(find "${ROOT_DIR}" -maxdepth 1 -name "*.sif" | head -n 1)
fi

if [ -n "${SIF_IMAGE}" ] && [ -f "${SIF_IMAGE}" ]; then
    EXEC_MODE="SINGULARITY"
    echo "=== Executing Pipeline (HPC Cluster PBS Pure Container Mode) ==="
    echo "SIF Image Found: ${SIF_IMAGE}"
else
    EXEC_MODE="NATIVE"
    echo "=== Executing Pipeline (HPC Cluster PBS Native Python Mode) ==="
    echo "Inherited Python Binary: ${ACTIVE_PYTHON}"
fi

echo "Log File: ${MASTER_LOG}"
echo "Master Output Destination: ${BASE_OUTPUT_REAL}"
echo "MSEED Source Target: ${MSEED_SRC_REAL}"
echo "----------------------------------------"

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
            BATCH_LOG="${ABS_BATCH_DIR}/hpc_execution.log"

            # Copy active config.env directly into batch sandbox directory
            if [ -f "${ROOT_DIR}/config.env" ]; then
                cp "${ROOT_DIR}/config.env" "${ABS_BATCH_DIR}/config.env"
            fi

            # ------------------------------------------------------------------
            # Generate Execution Command Block
            # ------------------------------------------------------------------
            if [ "$EXEC_MODE" = "SINGULARITY" ]; then
                EXEC_COMMAND_BLOCK=$(cat <<EOF
export TASK_LIST="/app/batch_manifest.txt"
export INPUT_DIR="\$SCRATCHDIR/input"
export STATIONS_PATH="\$SCRATCHDIR/input/stations.csv"
export MSEED_PATH="\$SCRATCHDIR/input/MSEED"

singularity exec --pwd /app --writable-tmpfs \\
  -B "\$SCRATCHDIR":/app \\
  "${SIF_IMAGE}" python3 -B -m dispiner 2>&1 \\
  | grep --line-buffered "^\[TASK_RESULT\]" \\
  | sed -u 's/\[TASK_RESULT\] //'
EOF
)
            else
                EXEC_COMMAND_BLOCK=$(cat <<EOF
# Inherit active frontend Python PATH environment
export PATH="${ACTIVE_PATH}:\$PATH"

export TASK_LIST="\$SCRATCHDIR/batch_manifest.txt"
export INPUT_DIR="\$SCRATCHDIR/input"
export STATIONS_PATH="\$SCRATCHDIR/input/stations.csv"
export MSEED_PATH="\$SCRATCHDIR/input/MSEED"

"${ACTIVE_PYTHON}" -B -m dispiner 2>&1 \\
  | grep --line-buffered "^\[TASK_RESULT\]" \\
  | sed -u 's/\[TASK_RESULT\] //'
EOF
)
            fi

            # ------------------------------------------------------------------
            # Write PBS Script Template
            # ------------------------------------------------------------------
            cat <<EOT > "${JOB_SCRIPT}"
#!/bin/bash
#PBS -N ${BATCH_NAME}
#PBS -l select=1:ncpus=${CPUS_HPC}:mem=${MEMORY}:scratch_local=10gb
#PBS -l walltime=${WALLTIME}
#PBS -j oe

set -e
export PYTHONDONTWRITEBYTECODE=1

JOB_LOG="${BATCH_LOG}"
MASTER_LOG="${MASTER_LOG}"

exec > >(tee -a "\${JOB_LOG}") 2>&1

if [ -z "\$SCRATCHDIR" ]; then
    SCRATCHDIR=\$(mktemp -d /tmp/scratch_${BATCH_NAME}_XXXXXX)
    TRAP_CLEANUP=true
else
    TRAP_CLEANUP=false
fi

cleanup() {
    if [ "\$TRAP_CLEANUP" = true ]; then
        rm -rf "\$SCRATCHDIR"
    fi
}
trap cleanup EXIT

echo "\$PBS_JOBID is running on node \$(hostname -f) in scratch directory \$SCRATCHDIR"

START_TIME=\$(date +%s)

# 1. Setup isolated scratch input directory directly
mkdir -p "\$SCRATCHDIR/input/MSEED"

# Copy stations metadata if provided
if [ -f "${STATIONS_SRC_REAL}" ]; then
    cp "${STATIONS_SRC_REAL}" "\$SCRATCHDIR/input/stations.csv"
fi

# 2. Extract or copy MSEED inputs (.tar vs folder)
MSEED_SRC="${MSEED_SRC_REAL}"

if [[ "\${MSEED_SRC}" == *.tar ]]; then
    tar -xf "\${MSEED_SRC}" -C "\$SCRATCHDIR/input/"
else
    MANIFEST="${ABS_BATCH_DIR}/batch_manifest.txt"
    if [ -f "\${MANIFEST}" ]; then
        PAIR_COL=\$(awk -F',' 'NR==1 {for(i=1;i<=NF;i++) if(\$i=="pair") print i}' "\${MANIFEST}")
        if [ -n "\${PAIR_COL}" ]; then
            awk -F',' -v col="\${PAIR_COL}" 'NR>1 {print \$col}' "\${MANIFEST}" | while read -r pair; do
                pair_clean=\$(echo "\${pair}" | tr -d '\r\n')
                if [ -n "\${pair_clean}" ] && [ -f "\${MSEED_SRC}/\${pair_clean}.mseed" ]; then
                    cp "\${MSEED_SRC}/\${pair_clean}.mseed" "\$SCRATCHDIR/input/MSEED/"
                fi
            done
        fi
    fi
fi

# Copy workspace Python dependencies and config.env to scratch
cp -r "${ABS_BATCH_DIR}/helpers" "\$SCRATCHDIR/"
cp -r "${ABS_BATCH_DIR}/dispiner" "\$SCRATCHDIR/"
cp "${ABS_BATCH_DIR}/batch_manifest.txt" "\$SCRATCHDIR/"
if [ -f "${ABS_BATCH_DIR}/config.env" ]; then
    cp "${ABS_BATCH_DIR}/config.env" "\$SCRATCHDIR/"
fi

# 3. Change directory to scratch and export all config.env variables
cd "\$SCRATCHDIR"

if [ -f "config.env" ]; then
    set -a
    source config.env
    set +a
fi

TMP_OUT="\$SCRATCHDIR/tmp_output"
LOG_DIR="\$TMP_OUT/LOG"
mkdir -p "\$LOG_DIR"

# 4. Dynamic Execution
${EXEC_COMMAND_BLOCK}

# 5. Archive generated outputs (PNG, CSV, LOG) directly
TAR_NAME="${BATCH_NAME}.tar"
cd "\$TMP_OUT"
tar -cf "\$SCRATCHDIR/\${TAR_NAME}" .

# 6. Save archive directly to OUTDIR/batch_xxx.tar
mkdir -p "${BASE_OUTPUT_REAL}"
cp "\$SCRATCHDIR/\${TAR_NAME}" "${BASE_OUTPUT_REAL}/${BATCH_NAME}.tar"

END_TIME=\$(date +%s)
RUNTIME=\$(( END_TIME - START_TIME ))

# 7. clean the SCRATCH directory
clean_scratch

echo "${BATCH_NAME} finished in \${RUNTIME}s" >> "\${MASTER_LOG}"
EOT

            chmod +x "${JOB_SCRIPT}"

            if [ "$INSIDE_CONTAINER" = true ]; then
                echo "cd \"${ABS_BATCH_DIR}\" && qsub \"${JOB_SCRIPT}\"" >> "${SPOOL_FILE}"
                echo "Spooled PBS template: ${BATCH_NAME}"
            else
                (cd "${ABS_BATCH_DIR}" && qsub "${JOB_SCRIPT}")
            fi
        fi
    done
fi

if [ "$INSIDE_CONTAINER" = true ] && [ -f "${SPOOL_FILE}" ]; then
    echo "----------------------------------------"
    echo "CONTAINER ENVIRONMENT DETECTED:"
    echo "Batch job scripts prepared and spooled to batch_execution/spool_queue.sh."
    echo ""
    echo "To dispatch all jobs to the cluster scheduler, run on host login node:"
    echo "bash batch_execution/spool_queue.sh"
    echo "----------------------------------------"
fi

echo "=== HPC batch preparation completed ==="
