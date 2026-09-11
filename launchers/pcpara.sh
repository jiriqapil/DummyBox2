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

RAW_OUT="${OUTPUT_DIR:-./demo/output}"
if [[ "$RAW_OUT" = /* ]]; then
    BASE_OUTPUT_REAL="$RAW_OUT"
else
    CLEAN_OUT="${RAW_OUT#./}"
    BASE_OUTPUT_REAL="${ROOT_DIR}/${CLEAN_OUT}"
fi

echo "=== Executing Pipeline (PC Parallel Mode) ==="
echo "Log File: ${MASTER_LOG}"
echo "Master Output Destination: ${BASE_OUTPUT_REAL}"
echo "----------------------------------------"

PIDS=()

if [ -d "${ROOT_DIR}/batch_execution" ]; then
    for batch_dir in "${ROOT_DIR}/batch_execution"/batch_*; do
        if [ -d "$batch_dir" ]; then
            BATCH_NAME=$(basename "$batch_dir")
            echo "Launching process worker for ${BATCH_NAME}..."

            (
                START_TIME=$SECONDS
                TMP_OUT="${batch_dir}/tmp_output"
                LOG_DIR="${TMP_OUT}/LOG"
                mkdir -p "${LOG_DIR}"

                cd "$batch_dir"

                # Capture ONLY lines starting with [TASK_RESULT] into the task execution log
                # 'sed' strips out the tag so your final log file contains just the clean table content
                python3 -B -m dummy2 2>&1 \
                    | grep "^\[TASK_RESULT\]" \
                    | sed 's/\[TASK_RESULT\] //' \
                    > "${LOG_DIR}/task_execution_${TIMESTAMP}.log"

                cd "${ROOT_DIR}"

                BATCH_DEST="${BASE_OUTPUT_REAL}/${BATCH_NAME}"
                mkdir -p "${BATCH_DEST}"
                cp -r "${TMP_OUT}/"* "${BATCH_DEST}/"

                rm -rf "${TMP_OUT}"

                DURATION=$((SECONDS - START_TIME))

                echo "${BATCH_NAME} finished in ${DURATION}s"
            ) & 

            PIDS+=($!)
        fi
    done
fi

echo "----------------------------------------"
echo "All workers initialized. Waiting for task completion..."

for pid in "${PIDS[@]}"; do
    wait "$pid"
done

echo "----------------------------------------"
echo "=== PC Parallel execution completed successfully ==="
