================================================================================
DUMMYBOX2 - EXECUTION GUIDE
================================================================================

This document provides ready-to-use commands for running DummyBox2 across
different execution environments: local workstations (Docker/Apptainer) and
HPC cluster environments (Singularity/Mamba with OpenPBS).

--------------------------------------------------------------------------------
TABLE OF CONTENTS
--------------------------------------------------------------------------------
1. DEMO RUNS (Fast Verification - Single Command Default Run)
   1.1 Local PC (Docker)
   1.2 Local PC (Apptainer)
   1.3 HPC Cluster / OpenPBS (Singularity Pure Container)

2. SMALL PROJECT / TESTING (Custom Dataset & Config)
   2.1 Local PC (Docker)
   2.2 Local PC (Apptainer)

3. HPC PRODUCTION (Big Data)
   3.1 Singularity Container Flow (Recommended)
   3.2 Native Mamba Environment Flow (Developer Mode)

================================================================================
1. DEMO RUNS (Fast Verification - Single Command Default Run)
================================================================================

1.1 Local PC (Docker)
---------------------
docker run --rm -v "$(pwd)/demo/output":/app/demo/output ghcr.io/jiriqapil/dummybox2:v2.0.0


1.2 Local PC (Apptainer)
------------------------
mkdir -p demo/output 
apptainer exec --pwd /app --writable-tmpfs -B "$(pwd)/demo/output":/app/demo/output docker://ghcr.io/jiriqapil/dummybox2:v2.0.0 python3 /app/run.py

#install aptainer (ubuntu)
sudo add-apt-repository -y ppa:apptainer/ppa
sudo apt update
sudo apt install -y apptainer


1.3 HPC Cluster / OpenPBS (Singularity Pure Container)
------------------------------------------------------
# 1. Initialize workspace and extract container image payload
singularity pull dummybox2.sif docker://ghcr.io/jiriqapil/dummybox2:v2.0.0
singularity exec dummybox2.sif cp -r /app/. .

# 2. Set working environment variables
export HOST_PWD=$(pwd)

# 3. Edit config.env in working directory
sed -i "s|\./|${HOST_PWD}/|g" config.env
sed -i 's/SUBMIT_MODE=.*/SUBMIT_MODE=hpc/g' config.env

# 4. Run Orchestrator Container
singularity exec --pwd /app --writable-tmpfs \
  -B /storage:/storage \
  -B "$(pwd)":/app \
  dummybox2.sif python3 /app/run.py

# 5. Patch container paths to host absolute storage paths in generated PBS scripts
sed -i "s|/app/|$(pwd)/|g" batch_execution/batch_*/submit_batch_*.pbs 2>/dev/null || true
sed -i "s|/app/|$(pwd)/|g" batch_execution/spool_queue.sh

# 6. Dispatch PBS batch jobs to OpenPBS queue
bash batch_execution/spool_queue.sh


================================================================================
2. SMALL PROJECT / TESTING (Custom Dataset & User Config)
================================================================================

2.1 Local PC (Docker)
---------------------
# 1. Prepare workspace and download template codebase
rm -rf DummyBox2_Test && mkdir -p DummyBox2_Test && cd DummyBox2_Test
docker run --rm -v "$(pwd)":/app/out ghcr.io/jiriqapil/dummybox2:v2.0.0 cp -r /app/. /app/out/

# 2. Edit config.env in working directory (Set custom paths, inputs, and parameters)
export HOST_PWD=$(pwd)
sed -i "s|\./|${HOST_PWD}/|g" config.env
sed -i 's/SUBMIT_MODE=.*/SUBMIT_MODE=pcmono/g' config.env
sed -i 's|INPUT_DIR=.*|INPUT_DIR=/path/to/your/custom_input|g' config.env
sed -i 's|OUTPUT_DIR=.*|OUTPUT_DIR=/path/to/your/custom_output|g' config.env

# 3. Execute processing with custom config mounted
docker run --rm -v "$(pwd)":/app ghcr.io/jiriqapil/dummybox2:v2.0.0 python3 /app/run.py


2.2 Local PC (Apptainer)
------------------------
# 1. Prepare workspace and pull container
rm -rf DummyBox2_Test && mkdir -p DummyBox2_Test && cd DummyBox2_Test
apptainer pull dummybox2.sif docker://ghcr.io/jiriqapil/dummybox2:v2.0.0
apptainer exec dummybox2.sif cp -r /app/. .

# 2. Edit config.env in working directory (Set custom paths, inputs, and parameters)
export HOST_PWD=$(pwd)
sed -i "s|\./|${HOST_PWD}/|g" config.env
sed -i 's/SUBMIT_MODE=.*/SUBMIT_MODE=pcmono/g' config.env
sed -i 's|INPUT_DIR=.*|INPUT_DIR=/path/to/your/custom_input|g' config.env
sed -i 's|OUTPUT_DIR=.*|OUTPUT_DIR=/path/to/your/custom_output|g' config.env

# 3. Execute processing with custom config mounted
apptainer exec --pwd /app --writable-tmpfs -B "$(pwd)":/app dummybox2.sif python3 /app/run.py


================================================================================
3. HPC PRODUCTION (Big Data)
================================================================================

3.1 Singularity Container Flow (Recommended)
---------------------------------------------------
# 1. Initialize workspace and fetch full codebase + SIF container
rm -rf DummyBox2_Prod && mkdir -p DummyBox2_Prod && cd DummyBox2_Prod
singularity pull dummybox2.sif docker://ghcr.io/jiriqapil/dummybox2:v2.0.0
singularity exec dummybox2.sif cp -r /app/. .

# 2. Set working environment variables
export HOST_PWD=$(pwd)

# 3. Edit config.env in working directory for production workload
sed -i "s|\./|${HOST_PWD}/|g" config.env
sed -i 's/SUBMIT_MODE=.*/SUBMIT_MODE=hpc/g' config.env
sed -i 's/NTASKS_IN_BATCH=.*/NTASKS_IN_BATCH=1000/g' config.env

# 4. Generate batch templates via Container Orchestrator
singularity exec --pwd /app --writable-tmpfs \
  -B /storage:/storage \
  -B "$(pwd)":/app \
  dummybox2.sif python3 /app/run.py

# 5. Patch container paths in generated PBS submit scripts
sed -i "s|/app/|$(pwd)/|g" batch_execution/batch_*/submit_batch_*.pbs 2>/dev/null || true
sed -i "s|/app/|$(pwd)/|g" batch_execution/spool_queue.sh

# 6. Dispatch all job arrays to the OpenPBS scheduler
bash batch_execution/spool_queue.sh


3.2 Native Mamba Environment Flow (Developer Mode)
------------------------------------------
# 1. Initialize workspace and fetch codebase from GitHub repository
rm -rf DummyBox2_Prod_Native && mkdir -p DummyBox2_Prod_Native && cd DummyBox2_Prod_Native
wget -qO- https://github.com/jiriqapil/DummyBox2/archive/refs/heads/main.tar.gz | tar -xz --strip-components=1

# 2. Activate Mamba environment
module add mambaforge || true
source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null || true

# (Optional: Build environment from requirements.txt if not created yet)
# mamba create -n dummybox-mamba-env --file requirements.txt -y
mamba activate dummybox-mamba-env

# 3. Set working environment variables
export HOST_PWD=$(pwd)

# 4. Edit config.env in working directory for production workload
sed -i "s|\./|${HOST_PWD}/|g" config.env
sed -i 's/SUBMIT_MODE=.*/SUBMIT_MODE=hpc/g' config.env
sed -i 's/NTASKS_IN_BATCH=.*/NTASKS_IN_BATCH=1000/g' config.env

# 5. Run Orchestrator natively (Auto-generates batches and submits PBS jobs via hpc.sh)
python3 run.py

================================================================================
