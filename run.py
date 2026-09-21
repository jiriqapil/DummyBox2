import sys
import os
import shutil
import csv
import math
import subprocess
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "helpers"))

def detect_container_metadata():
    """Dynamically discover PACKAGE_NAME and PACKAGE_TAG from .sif symlink, environment, or inspect."""
    pkg_name = None
    pkg_tag = None

    # 1. Check for .sif file in PROJECT_ROOT (HPC Singularity Mode)
    sif_files = list(PROJECT_ROOT.glob("*.sif"))
    if sif_files:
        sif_path = sif_files[0]
        # Extract filename without extension (e.g., 'dummybox2.sif' -> 'dummybox2')
        pkg_name = sif_path.stem

        # Try to inspect the .sif image labels for a version tag
        try:
            res = subprocess.run(
                ["singularity", "inspect", "--labels", str(sif_path)],
                capture_output=True, text=True, timeout=5
            )
            for line in res.stdout.splitlines():
                line_lower = line.lower()
                if "version" in line_lower or "tag" in line_lower:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        pkg_tag = parts[1].strip()
                        break
        except Exception:
            pass  # Failproof fallback if singularity binary isn't in PATH or inspect fails

    # 2. Check Environment / Docker / Mamba / GitHub VM fallbacks
    if not pkg_name:
        pkg_name = os.getenv("PACKAGE_NAME") or os.getenv("CONTAINER_NAME") or "dispiner"

    if not pkg_tag:
        pkg_tag = os.getenv("PACKAGE_TAG") or os.getenv("CONTAINER_TAG") or ""

    return pkg_name, pkg_tag


def load_config_env():
    """Load config.env into os.environ before setup_params evaluation."""
    env_file = PROJECT_ROOT / "config.env"

    # Dynamically detect image metadata based on runtime context
    detected_name, detected_tag = detect_container_metadata()

    # 1. Safely prepend missing package variables to config.env if file is writable
    try:
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            missing_lines = []
            if "PACKAGE_NAME=" not in content:
                missing_lines.append(f"PACKAGE_NAME={detected_name}")
            if "PACKAGE_TAG=" not in content:
                missing_lines.append(f"PACKAGE_TAG={detected_tag}")

            if missing_lines:
                new_content = "\n".join(missing_lines) + "\n" + content
                env_file.write_text(new_content, encoding="utf-8")
        else:
            default_block = f"PACKAGE_NAME={detected_name}\nPACKAGE_TAG={detected_tag}\n"
            env_file.write_text(default_block, encoding="utf-8")
    except Exception:
        # Failproof: ignore write errors if running in read-only environment
        pass

    # 2. Set default environment variables in memory as baseline fallback
    os.environ.setdefault("PACKAGE_NAME", detected_name)
    os.environ.setdefault("PACKAGE_TAG", detected_tag)

    # 3. Preserve original config.env parsing logic
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    val = val.split("#", 1)[0].strip()
                    os.environ[key.strip()] = val
        except Exception:
            pass

load_config_env()
from helpers.defs4process import setup_params

def filter_active_tasks(task_list_path):
    """Filter task CSV retaining only active rows where 'use' or 'process' is Y/Yes/y/yes."""
    active_tasks = []
    header = None
    
    if not os.path.exists(task_list_path):
        print(f"[Error] Task manifest not found at: {task_list_path}")
        sys.exit(1)

    with open(task_list_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("[Warning] Task list file is empty.")
            return [], []

        target_idx = -1
        valid_colnames = {"USE", "PROCESS"}
        for idx, col in enumerate(header):
            if col.strip().upper() in valid_colnames:
                target_idx = idx
                break

        if target_idx == -1:
            print("[Warning] Neither 'use' nor 'process' column found in CSV header. Including all rows.")
            for row in reader:
                if row and any(field.strip() for field in row):
                    active_tasks.append(row)
        else:
            valid_yes = {"Y", "YES"}
            for row in reader:
                if row and len(row) > target_idx:
                    status = row[target_idx].strip().upper()
                    if status in valid_yes:
                        active_tasks.append(row)

    return header, active_tasks

def calculate_tasks_per_batch(cfg, total_active):
    """Determine task distribution based on submit_mode."""
    mode = cfg["submit_mode"]
    
    if mode == "pcpara":
        raw_cpus = str(cfg.get("cpus_pc", "1")).strip().upper()
        if raw_cpus == "MAX":
            detected_cpus = os.cpu_count() or 4
            num_cpus = max(1, detected_cpus - 1)
            print(f"[Orchestrator] 'MAX' selected: Using {num_cpus} workers (1 core reserved for system safety).")
        else:
            try:
                num_cpus = int(raw_cpus)
            except ValueError:
                num_cpus = 1
            num_cpus = max(1, num_cpus)

        tasks_per_batch = math.ceil(total_active / num_cpus)
        print(f"[Orchestrator] PCPARA Mode: Distributing workload across {num_cpus} parallel workers ({tasks_per_batch} tasks/batch).")
        return max(1, tasks_per_batch)
    else:
        # pcmono and hpc modes use static NTASKS_IN_BATCH config
        return max(1, cfg["ntasks_in_batch"])

def prepare_batch_workspaces(cfg):
    task_list_path = cfg["task_list"]
    header, active_tasks = filter_active_tasks(task_list_path)

    total_active = len(active_tasks)
    print(f"[Orchestrator] Active tasks selected for processing: {total_active}")

    if total_active == 0:
        print("[Orchestrator] No active tasks to process. Exiting.")
        sys.exit(0)

    # Re-initialize clean batch_execution directory
    batch_exec_dir = PROJECT_ROOT / "batch_execution"
    if batch_exec_dir.exists():
        shutil.rmtree(batch_exec_dir)
    batch_exec_dir.mkdir(parents=True, exist_ok=True)

    # Resolve input path to link inside batch sandboxes
    raw_input_dir = os.getenv("INPUT_DIR", "./demo/input")
    input_source = Path(raw_input_dir)
    if not input_source.is_absolute():
        input_source = (PROJECT_ROOT / input_source).resolve()

    tasks_per_batch = calculate_tasks_per_batch(cfg, total_active)
    batch_idx = 0

    for i in range(0, total_active, tasks_per_batch):
        batch_subset = active_tasks[i : i + tasks_per_batch]
        batch_folder_name = f"batch_{batch_idx:03d}"
        batch_path = batch_exec_dir / batch_folder_name
        batch_path.mkdir(parents=True, exist_ok=True)

        # 1. Create symlink for input assets (used in PC modes; copied to SCRATCHDIR in HPC)
        sandbox_demo_input = batch_path / "demo" / "input"
        sandbox_demo_input.parent.mkdir(parents=True, exist_ok=True)
        if input_source.exists():
            sandbox_demo_input.symlink_to(input_source, target_is_directory=True)

        # 2. Write isolated batch manifest
        manifest_path = batch_path / "batch_manifest.txt"
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
            writer.writerows(batch_subset)

        # 3. Copy application execution packages
        shutil.copytree(PROJECT_ROOT / "helpers", batch_path / "helpers")
        shutil.copytree(PROJECT_ROOT / "dispiner", batch_path / "dispiner")

        # 4. Bake runtime parameters into sandbox
        defs_path = batch_path / "helpers" / "defs4process.py"
        with open(defs_path, "r", encoding="utf-8") as f:
            code = f.read()

        code = code.replace("BAKED_BATCH = None", f"BAKED_BATCH = {batch_idx}")
        code = code.replace("BAKED_NTASKS = None", f"BAKED_NTASKS = {len(batch_subset)}")

        with open(defs_path, "w", encoding="utf-8") as f:
            f.write(code)

        print(f" -> Created {batch_folder_name} ({len(batch_subset)} active tasks)")
        batch_idx += 1

    print(f"[Orchestrator] Workspace allocation finished. Total batches: {batch_idx}")
    return batch_idx

def dispatch_launcher(mode):
    launcher_map = {
        "pcmono": PROJECT_ROOT / "launchers" / "pcmono.sh",
        "pcpara": PROJECT_ROOT / "launchers" / "pcpara.sh",
        "hpc": PROJECT_ROOT / "launchers" / "hpc.sh",
    }

    launcher_script = launcher_map.get(mode)
    if not launcher_script or not launcher_script.exists():
        print(f"[Error] Target launcher script missing for mode '{mode}': {launcher_script}")
        sys.exit(1)

    print(f"[Orchestrator] Launching pipeline via {launcher_script.name}...")
    subprocess.run(["bash", str(launcher_script)], check=True)

if __name__ == "__main__":
    cfg = setup_params()
    print(f"[Orchestrator] Starting workload dispatch (Submit Mode: {cfg['submit_mode']})")
    
    total_batches = prepare_batch_workspaces(cfg)
    if total_batches > 0:
        dispatch_launcher(cfg['submit_mode'])
