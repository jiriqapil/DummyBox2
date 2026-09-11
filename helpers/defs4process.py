# ==== defs4process.py =====
from imports import *

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

BAKED_BATCH = None
BAKED_NTASKS = None

def setup_params(env_path=None):
    batch_dir = Path.cwd().resolve()
    
    if BAKED_BATCH is not None:
        project_dir = batch_dir.parent.parent
    else:
        project_dir = batch_dir

    raw_input = os.getenv("INPUT_DIR", "./demo/input")
    raw_output = os.getenv("OUTPUT_DIR", "./demo/output")

    input_path = Path(raw_input)
    base_input_dir = str((project_dir / input_path).resolve()) if not input_path.is_absolute() else str(input_path.resolve())

    out_path = Path(raw_output)
    base_output_dir = (project_dir / out_path).resolve() if not out_path.is_absolute() else out_path.resolve()

    if BAKED_BATCH is not None:
        tmp_output_dir = str(batch_dir / "tmp_output")
        real_output_dir = str(base_output_dir / f"batch_{int(BAKED_BATCH):03d}")
    else:
        tmp_output_dir = str(base_output_dir)
        real_output_dir = str(base_output_dir)

    os.makedirs(tmp_output_dir, exist_ok=True)

    local_manifest = batch_dir / "batch_manifest.txt"
    if local_manifest.exists():
        selected_task_list = str(local_manifest)
    else:
        selected_task_list = os.getenv("TASK_LIST", f"{base_input_dir}/task_list_demo.csv")

    defaults = {
        "SUBMIT_MODE": "pcmono",
        "PC_EXECUTION": "active",                   # Internal execution style (active vs detached)
        "INPUT_DIR": base_input_dir,
        "TASK_LIST": selected_task_list,
        "OUTPUT_DIR": tmp_output_dir,
        "OUTPUT_DIR_REAL": real_output_dir,
        "STATIONS_PATH": f"{base_input_dir}/META/stations.csv",
        "MSEED_PATH": f"{base_input_dir}/MSEED",
        "ETOPO_NC": f"{base_input_dir}/META/ETOPO/ETOPO1_Ice_g_gmt4_cropEU.nc",
        "QGIS_DIR": f"{base_input_dir}/META/QGIS",

        "CPUS_PC": "1",
        "NTASKS_IN_BATCH": "1",
        "CPUS_HPC": "1",
        "MEMORY": "1gb",
        "WALLTIME": "00:30:00",

        "MAP_STYLE": "Default",
        "USE_QGIS": "false",
        "IMAGE_QUALITY": "Publish",
        "SHOW_FIGURE": "false",

        "MULTIFILTER_TYPE": "acoustic_butterworth",
        "ANCHOR_HARMONISATION": "true",
        "CROSSVALIDATION": "true",

        "MAXLAG": 720,
        "SNRCUT": 1.0,
        "HARMO_COEFT": 1.1,
        "HARMO_SNRCUT": 3.0,
        "HARMO_MAXDIFFZR": 0.05,
        "HARMO_RANGE_COEFT": "0.9,1.25",

        "VMIN_PICK": 1.5,
        "VMAX_PICK": 6.0,
        "VMIN_GRID": 1.0,
        "VMAX_GRID": 8.0,
        "VMIN_TAP": 1.8,
        "VMAX_TAP": 4.6,
    }

    cfg = {}
    cfg["baked_batch"] = BAKED_BATCH
    cfg["baked_ntasks"] = BAKED_NTASKS
    cfg["project_dir"] = str(project_dir)
    cfg["batch_dir"] = str(batch_dir)

    cfg["submit_mode"] = os.getenv("SUBMIT_MODE", defaults["SUBMIT_MODE"])
    cfg["pc_execution"] = os.getenv("PC_EXECUTION", defaults["PC_EXECUTION"])
    cfg["input_dir"] = os.getenv("INPUT_DIR", defaults["INPUT_DIR"])
    cfg["task_list"] = selected_task_list
    cfg["output_dir"] = defaults["OUTPUT_DIR"]
    cfg["output_dir_real"] = defaults["OUTPUT_DIR_REAL"]

    cfg["stations_path"] = os.getenv("STATIONS_PATH", defaults["STATIONS_PATH"])
    cfg["mseed_path"] = os.getenv("MSEED_PATH", defaults["MSEED_PATH"])
    cfg["etopo_nc"] = os.getenv("ETOPO_NC", defaults["ETOPO_NC"])
    cfg["qgis_dir"] = os.getenv("QGIS_DIR", defaults["QGIS_DIR"])

    cfg["cpus_pc"] = os.getenv("CPUS_PC", defaults["CPUS_PC"])
    cfg["ntasks_in_batch"] = int(os.getenv("NTASKS_IN_BATCH", defaults["NTASKS_IN_BATCH"]))
    cfg["cpus_hpc"] = int(os.getenv("CPUS_HPC", defaults["CPUS_HPC"]))
    cfg["memory"] = os.getenv("MEMORY", defaults["MEMORY"])
    cfg["walltime"] = os.getenv("WALLTIME", defaults["WALLTIME"])

    cfg["map_style"] = os.getenv("MAP_STYLE", defaults["MAP_STYLE"])
    cfg["use_qgis"] = (os.getenv("USE_QGIS", defaults["USE_QGIS"]).lower() == "true")
    cfg["image_quality"] = os.getenv("IMAGE_QUALITY", defaults["IMAGE_QUALITY"])
    cfg["show_figure"] = os.getenv("SHOW_FIGURE", defaults["SHOW_FIGURE"]).lower() == "true"
    cfg["multifilter_type"] = os.getenv("MULTIFILTER_TYPE", defaults["MULTIFILTER_TYPE"]).lower()
    cfg["anchor_harmonisation"] = os.getenv("ANCHOR_HARMONISATION", defaults["ANCHOR_HARMONISATION"]).lower() == "true"
    cfg["crossvalidation"] = os.getenv("CROSSVALIDATION", defaults["CROSSVALIDATION"]).lower() == "true"
    cfg["maxlag"] = int(os.getenv("MAXLAG", defaults["MAXLAG"]))
    cfg["snrcut"] = float(os.getenv("SNRCUT", defaults["SNRCUT"]))
    cfg["harmo_coeft"] = float(os.getenv("HARMO_COEFT", defaults["HARMO_COEFT"]))
    cfg["harmo_snrcut"] = float(os.getenv("HARMO_SNRCUT", defaults["HARMO_SNRCUT"]))
    cfg["harmo_maxdiffzr"] = float(os.getenv("HARMO_MAXDIFFZR", defaults["HARMO_MAXDIFFZR"]))

    harmo_range_raw = os.getenv("HARMO_RANGE_COEFT", defaults["HARMO_RANGE_COEFT"])
    cfg["harmo_range_coeft"] = [float(x.strip()) for x in harmo_range_raw.split(",")]

    cfg["vmin_pick"] = float(os.getenv("VMIN_PICK", defaults["VMIN_PICK"]))
    cfg["vmax_pick"] = float(os.getenv("VMAX_PICK", defaults["VMAX_PICK"]))
    cfg["vmin_grid"] = float(os.getenv("VMIN_GRID", defaults["VMIN_GRID"]))
    cfg["vmax_grid"] = float(os.getenv("VMAX_GRID", defaults["VMAX_GRID"]))
    cfg["vmin_tap"] = float(os.getenv("VMIN_TAP", defaults["VMIN_TAP"]))
    cfg["vmax_tap"] = float(os.getenv("VMAX_TAP", defaults["VMAX_TAP"]))

    return cfg

def show_env():
    """Prints system information and inspects loaded non-standard top-level modules."""
    print("=" * 60)
    print(f"{'SYSTEM & ENVIRONMENT INFO':^60}")
    print("=" * 60)
    print(f"{'Python Version':<25} : {sys.version.split()[0]}")
    print(f"{'Platform / OS':<25} : {sys.platform}")
    print(f"{'Python Executable':<25} : {sys.executable}")

    print("-" * 60)
    print(f"{'--- LOADED MODULES & VERSIONS ---':^60}")

    loaded_pkgs = {}
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name.startswith("_") and "." not in mod_name:
            version = getattr(mod, "__version__", None)
            if version:
                loaded_pkgs[mod_name] = version

    for mod_name in sorted(loaded_pkgs.keys()):
        print(f"Package: {mod_name:<16} : {loaded_pkgs[mod_name]}")

    print("=" * 60)


def show_params(params_dict):
    """Prints initialized parameters split dynamically between active ENV overrides

    (present in params/config.env) and Python baseline defaults.
    """
    # Identify which keys were explicitly provided by the loaded config.env file
    env_keys = set()
    for key in params_dict:
        env_var_name = key.upper()
        if env_var_name in os.environ:
            env_keys.add(key)

    print("=" * 60)
    print(f"{'INITIALISED PIPELINE PARAMETERS':^60}")
    print("=" * 60)

    # 1. Print Active ENV Overrides
    print(f"{'--- ENVIRONMENT OVERRIDES (params/config.env) ---':^60}")
    for key in sorted(env_keys):
        val = params_dict[key]
        val_str = (
            f"Array shape {val.shape}"
            if isinstance(val, np.ndarray)
            else str(val)
        )
        print(f"{key:<25} : {val_str}")

    # 2. Print Python Baseline Defaults (for keys not set in .env)
    print("-" * 60)
    print(f"{'----- DEFAULTS (PYTHON BASELINE) -----':^60}")
    for key, val in sorted(params_dict.items()):
        if key not in env_keys:
            if isinstance(val, np.ndarray):
                val_str = f"Array shape {val.shape} (min={val.min():.2f}, max={val.max():.2f})"
            else:
                val_str = str(val)
            print(f"{key:<25} : {val_str}")

    print("=" * 60)

import numpy as np


def processing_init(cfg):
    """Initializes processing thresholds, constructs anchor/FTAN filters,

    and generates the FTAN velocity-period meshgrid.
    """
    # Processing Thresholds & Bounds
    maxlag = cfg["maxlag"]
    snrcut = cfg["snrcut"]
    vmin = cfg["vmin_pick"]
    vmax = cfg["vmax_pick"]

    # Build FTAN anchor and narrow-band filters
    flt4anch, flt4ftan = build_filters()

    # =====================================================================
    # FTAN Meshgrid Setup
    # =====================================================================
    # X-axis: 2x1/3 octave bands (FTAN)
    Xi = flt4ftan["t_ctr"]

    # Y-axis (velocity axis): sampling 0.01
    Yi = np.linspace(vmin, vmax, int((vmax - vmin) * 100) + 1)
    Xii, Yii = np.meshgrid(Xi, Yi)

    return maxlag, snrcut, flt4anch, flt4ftan, Xi, Yi, Xii, Yii


def pair_geometry(net1, sta1, net2, sta2, stations_csv, wgtmin=None):
    """
    Updates station pair geometry parameters based on reference catalog lookup.
    Uses 'stations_csv' passed from pipeline configuration.
    """
    wgt = 1 if wgtmin is None else int(wgtmin)

    sta1_key = f"{net1}.{sta1}"
    sta2_key = f"{net2}.{sta2}"

    lon1 = lat1 = alt1 = None
    lon2 = lat2 = alt2 = None

    # Single-pass catalog load into dictionary
    coord_map = {}
    with open(stations_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            # Match by reformatted net.sta (e.g., CH.BALST)
            coord_map[row["net.sta"].strip()] = (
                float(row["lon"]),
                float(row["lat"]),
                float(row["alt"]),
            )


    if sta1_key not in coord_map or sta2_key not in coord_map:
        raise ValueError(f"Station pair {sta1_key}:{sta2_key} not found in {stations_csv}")

    lon1, lat1, alt1 = coord_map[sta1_key]
    lon2, lat2, alt2 = coord_map[sta2_key]

    # Distance calculation via gps2dist
    dist, az, baz = gps2dist(lat1, lon1, lat2, lon2)
    dist_km = np.round(dist / 1000.0, 3)

    # Undirected azimuth
    raz = az % 180
    rbaz = baz % 180
    if raz <= 22.5:
        raz += 180
    if rbaz <= 22.5:
        rbaz += 180

    azim = (raz + rbaz) / 2.0
    azim = azim % 180

    # Midpoint calculation
    lonMl = (lon1 + lon2) / 2.0
    latMl = (lat1 + lat2) / 2.0

    if lon1 == lon2:
        lonMc, latMc, Mdif = lon1, latMl, 0.0
    elif lat1 == lat2:
        latMc, lonMc, Mdif = lat1, lonMl, 0.0
    else:
        rlon1, rlat1 = radians(lon1), radians(lat1)
        rlon2, rlat2 = radians(lon2), radians(lat2)
        dLon = rlon2 - rlon1
        Bx = cos(rlat2) * cos(dLon)
        By = cos(rlat2) * sin(dLon)
        latMc = degrees(
            atan2(
                sin(rlat1) + sin(rlat2),
                np.sqrt((cos(rlat1) + Bx) * (cos(rlat1) + Bx) + By * By),
            )
        )
        lonMc = degrees(rlon1 + atan2(By, cos(rlat1) + Bx))

        radius = 6371.0  # km
        dlat, dlon = radians(latMc - latMl), radians(lonMc - lonMl)
        a = (
            sin(dlat / 2.0) ** 2
            + cos(radians(latMl)) * cos(radians(latMc)) * sin(dlon / 2.0) ** 2
        )
        c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
        Mdif = radius * c

    return (
        wgt, lon1, lat1, alt1, lon2, lat2, alt2,
        dist, az, baz, dist_km, azim, lonMl, latMl, lonMc, latMc, Mdif
    )
    
def pair_binning(dist_km, azim, latMc, lonMc):
    """
    Categorizes station pairs into distance rings (R1-R6), azimuth sectors (A1-A4),
    determines spatial grid cells, and calculates a normalized binning score.
    """
  ##=============GEOMETRY BINNING
  # select cmpMc:
  # LON >=7 <=21.5
  # LAT >=46 <=54 
  
  # select distance >=50and <=1200 km
  #     ->R1 newNEAR >=50 <200
  #     ->R2 newMID  >=200 <400
  #     ->R3 newFAR  >=400 <600
  #     ->R4 newVFAR>=600 <800
  #     ->R5 newEFAR>=800 <=1200

  # group by azimuth segmets (hourglass octants)
  # AZS1   N-S: >337.5 <=22.5 and >157.5 <=202.5 (<=180)
  # AZS2 NE-SW: >22.5 <=67.5 and >202.5 <=247.5
  # AZS3   E-W: >67.5 <=112.5 and >247.5 <=292.5 
  # AZS4 SE-NW: >112.5 <=157.5 and >292.5 <=337.5


    # 1. Distance Ring Classification
    if dist_km < 200:
        ring = "R1"
        dctr = 100
    elif 200 <= dist_km < 400:
        ring = "R2"
        dctr = 300
    elif 400 <= dist_km < 600:
        ring = "R3"
        dctr = 500
    elif 600 <= dist_km < 800:
        ring = "R4"
        dctr = 700
    elif 800 <= dist_km < 1000:
        ring = "R5"
        dctr = 900
    elif 1000 <= dist_km:
        ring = "R6"
        dctr = 1100

    # 2. Azimuth Sector Classification (Hourglass Octants)
    if (azim > 337.5) or (azim <= 22.5):  # N
        sec = "A1"
        actr = 180
    elif azim <= 67.5:  # NE
        sec = "A2"
        actr = 45
    elif azim <= 112.5:  # E
        sec = "A3"
        actr = 90
    elif azim <= 157.5:  # SE
        sec = "A4"
        actr = 135
    elif azim <= 202.5:  # N
        sec = "A1"
        actr = 180
    elif azim <= 247.5:
        sec = "A2"
        actr = 45
    elif azim <= 292.5:
        sec = "A3"
        actr = 90
    else:  # 292.5 < az <= 337.5
        sec = "A4"
        actr = 135

    rdif = abs(dctr - dist_km)
    adif = abs(actr - azim)

    # 3. Spatial Cell Determination
    LON = int((lonMc * 100 + 7.5) / 15) * 15
    LAT = int((latMc * 100 + 5) / 10) * 10
    CELL = str("{:04d}".format(LAT)) + "_" + str("{:04d}".format(LON))

    # Distance to cell center
    mdist, maz, mbaz = gps2dist(float(latMc), float(lonMc), LAT / 100, LON / 100)
    cdif_km = np.round(mdist / 1000)

    # 4. Binning Score Calculation
    rdlt = 100    # halfwidth of ring
    adlt = 22.5   # halfwidth of sector
    cdlt = 8      # cell radius

    cnorm = cdif_km / cdlt
    rnorm = rdif / rdlt
    anorm = adif / adlt

    bscore = np.sqrt((cnorm**2 + rnorm**2 + anorm**2) / 3)

    return ring, dctr, sec, actr, rdif, adif, LAT, LON, CELL, cdif_km, bscore


def build_filters():
    """Builds FTAN anchor filters and 1/6 octave narrow-band filters.

    Returns:
        tuple: (flt4anch, flt4ftan) dictionaries
    """
    # -------------------------------------------------------------
    # 1. Anchor filters for FTAN 1/6 octave picking
    # -------------------------------------------------------------
    ff = 1.0
    band = 1.0
    bw = 1 / 2
    order = 4

    flt4anch = {
        "band": [],
        "label": [],
        "t_ctr": [],
        "f_ctr": [],
        "f_lo": [],
        "f_hi": [],
    }

    for idx in range(1, 9):
        if idx == 1:
            f_ctr = ff
        else:
            f_ctr = ff / np.power(2, band)

        f_lo = f_ctr / np.power(2, bw)
        f_hi = f_ctr * np.power(2, bw)

        # Store points as picking anchors (idx 3 to 8)
        if 3 <= idx <= 8:
            flt4anch["band"].append(idx)
            flt4anch["t_ctr"].append(int(np.round(1 / f_ctr)))
            flt4anch["f_ctr"].append(f_ctr)
            flt4anch["f_lo"].append(f_lo)
            flt4anch["f_hi"].append(f_hi)

            if idx == 3:
                flt4anch["label"].append("near surface")
            elif idx == 4:
                flt4anch["label"].append("secondary microseis")
            elif idx == 5:
                flt4anch["label"].append("primary microseis")
            elif idx == 6:
                flt4anch["label"].append("lower crust")
            elif idx == 7:
                flt4anch["label"].append("uppermost mantle")
            elif idx == 8:
                flt4anch["label"].append("upper mantle")

        # Update running center frequency for next iteration
        ff = f_ctr

    # -------------------------------------------------------------
    # 2. FTAN narrow band filters (1/6 Octave)
    # -------------------------------------------------------------
    ff = 1.0
    band = 1 / 6 # octave band sampling
    bw = 1 / 4   # bandwidth
    order = 4    # butterworth order (in application zero-hase order 2 is recursive giving order 4)
    # bedge=1/12   # band separation ###EDGE TO EDGE for 1/6 octave
    # bedge=1/6   # band separation ###CENTER TO CENTER for 1/4 octave
    bedge=1/4   # band separation ###CENTER TO CENTER for 1/4 octave

    flt4ftan = {
        "band": [],
        "t_ctr": [],
        "f_ctr": [],
        "f_lo": [],
        "f_hi": [],
        'f_lo_edge':[],
        'f_hi_edge':[]
    }

    for idx in range(1, 50):
        if idx == 1:
            f_ctr = ff
        else:
            f_ctr = ff / np.power(2, band)

        f_lo = f_ctr / np.power(2, bw)
        f_hi = f_ctr * np.power(2, bw)
        f_lo_edge = f_ctr / np.power(2, bedge)
        f_hi_edge = f_ctr * np.power(2, bedge)   


        flt4ftan["band"].append(idx)
        flt4ftan["t_ctr"].append(1 / f_ctr)
        flt4ftan["f_ctr"].append(f_ctr)
        flt4ftan["f_lo"].append(f_lo)
        flt4ftan["f_hi"].append(f_hi)
        flt4ftan['f_lo_edge'].append(f_lo_edge)
        flt4ftan['f_hi_edge'].append(f_hi_edge)

        # Update running center frequency for next iteration
        ff = f_ctr

    return flt4anch, flt4ftan
    
def gaussian_bandpass_zeropad(tr, f0, alpha=50.0, pad_factor=50):
    """
    Gaussian bandpass filter with FFT zero-padding for fine frequency resolution.
    """
    tr_f = tr.copy()
    n = tr.stats.npts
    dt = tr.stats.delta

    n_pad = int(n * pad_factor)

    spec = np.fft.rfft(tr_f.data, n=n_pad)
    freqs = np.fft.rfftfreq(n_pad, dt)

    H = np.exp(-alpha * ((freqs - f0) / f0) ** 2)

    spec_filtered = spec * H
    data_filt = np.fft.irfft(spec_filtered, n=n_pad)
    tr_f.data = data_filt[:n]

    return tr_f


