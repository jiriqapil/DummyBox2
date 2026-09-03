# ==== defs4write.py ====
from imports import *

def write_config_log(show_env_func, show_params_func, params_dict):
    """Executes environment and parameter display functions, writing the exact

    terminal output directly into a timestamped config log file.
    """
    # Ensure LOG directory exists
    log_dir = os.path.join(params_dict["output_dir"], "LOG")
    os.makedirs(log_dir, exist_ok=True)

    # Generate timestamp in format: 20260901T124512
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"jobconfig_{timestamp}.log"
    log_filepath = os.path.join(log_dir, filename)

    # Redirect stdout to file while running the print functions
    stdout_original = sys.stdout
    with open(log_filepath, "w", encoding="utf-8") as f:
        sys.stdout = f
        show_env_func()
        print()  # Spacer line between sections
        show_params_func(params_dict)

    # Restore standard output
    sys.stdout = stdout_original
    print(f"Logged setup configuration to: {log_filepath}")

def write_attr_mask(data, mask):
    """Applies a boolean mask to a nested 2D structure, replacing True with np.nan."""
    arr = np.array(data, dtype=float)
    mask_arr = np.array(mask, dtype=bool)
    arr[mask_arr] = np.nan
    return arr.tolist()

def write_clean_pytypes(val):
    """
    Flattens single-element sublists and converts NumPy types 
    (e.g., np.float64) to native Python types.
    """
    if isinstance(val, (list, tuple, np.ndarray)):
        # Convert NumPy types to native python types
        clean_list = [x.item() if hasattr(x, 'item') else x for x in val]
        
        # Flatten double-nested lists of single elements like [['ZZ_AV'], ['ZZ_AC']] -> ['ZZ_AV', 'ZZ_AC']
        if len(clean_list) > 0 and isinstance(clean_list[0], (list, tuple, np.ndarray)):
            if all(len(sub) == 1 for sub in clean_list if isinstance(sub, (list, tuple, np.ndarray))):
                clean_list = [sub[0].item() if hasattr(sub[0], 'item') else sub[0] for sub in clean_list]
            elif len(clean_list) == 1:
                clean_list = clean_list[0]
                
        return clean_list
    return val.item() if hasattr(val, 'item') else val

def write_dict_aggregate(pair_dict, tag_dicts):
    """Applies masks, cleans primitive data types, renames keys, and appends to tag dictionary."""
    cv_tag_val = write_clean_pytypes(pair_dict['crossvalidation_tag'])
    cv_tag_str = cv_tag_val[0] if isinstance(cv_tag_val, list) else cv_tag_val
    cv_tag_str = str(cv_tag_str).upper()

    if cv_tag_str in ['Z1RT1', 'Z1RT2', 'Z2RT1', 'Z2RT2']:
        tag = "3C"
    elif cv_tag_str in ['Z1RT0', 'Z2RT0']:
        tag = "1C"
    else:
        tag = "0C"

    target_dict = tag_dicts[tag]

    # Global dimensions
    if 'curve_id' not in target_dict:
        target_dict['curve_id'] = write_clean_pytypes(pair_dict['disp_id'])
        target_dict['period'] = write_clean_pytypes(pair_dict['period'])

    # Masked period-dependent 2D arrays
    masked_group = write_attr_mask(pair_dict['group_v'], pair_dict['group_mask'])
    masked_phase = write_attr_mask(pair_dict['phase_v'], pair_dict['phase_mask'])
    masked_amp = write_attr_mask(pair_dict['group_amp'], pair_dict['group_mask'])
    
    # --- MASK SNR USING GROUP MASK HERE ---
    masked_snr = write_attr_mask(pair_dict['group_snr'], pair_dict['group_mask'])

    # Metadata
    pair_name = write_clean_pytypes(pair_dict['pair'])
    target_dict['pair'].append(pair_name[0] if isinstance(pair_name, list) else pair_name)
    target_dict['lat_lon_alt_1'].append(write_clean_pytypes(pair_dict['lat_lon_alt_1']))
    target_dict['lat_lon_alt_2'].append(write_clean_pytypes(pair_dict['lat_lon_alt_2']))
    target_dict['midlat_midlon_wgt'].append(write_clean_pytypes(pair_dict['midlat_midlon_wgt']))
    target_dict['dist_azim_az_baz'].append(write_clean_pytypes(pair_dict['dist_azim_az_baz']))
    target_dict['binning'].append(write_clean_pytypes(pair_dict['binning']))
    
    # 2D/3D Data arrays
    target_dict['group'].append(masked_group)
    target_dict['phase'].append(masked_phase)
    target_dict['amplitude'].append(masked_amp)
    target_dict['spectrum_type'].append(write_clean_pytypes(pair_dict['phase_ncyc26']))

    # Component attributes
    target_dict['attribute_snr'].append(masked_snr)  # Now properly NaN-masked!
    target_dict['attribute_bzq'].append(write_clean_pytypes(pair_dict['phase_bzq']))
    target_dict['crossval_tag'].append(cv_tag_str.lower())
    

def write_init_tag_dict():
    """Initializes the output dictionary structure."""
    return {
        'pair': [], 'lat_lon_alt_1': [], 'lat_lon_alt_2': [], 
        'midlat_midlon_wgt': [], 'dist_azim_az_baz': [], 'binning': [],
        'group': [], 'phase': [], 'spectrum_type': [], 'amplitude': [],
        'attribute_snr': [], 'attribute_bzq': [], 'crossval_tag': []
    }

# --- Header Definitions ---

def write_csv_header_stations():
    return [
        "# StationID: network code and station code (network.station)\n",
        "# Latitude: station latitude in decimal degrees (°N)\n",
        "# Longitude: station longitude in decimal degrees (°E)\n",
        "# Elevation: station elevation in meters above sea level (m)\n",
        "StationID,Latitude,Longitude,Elevation\n"
    ]

def write_csv_header_pairs():
    return [
        "# Pair: station1_station2 identifier\n",
        "# InterstationDistance: great-circle distance between stations in km\n",
        "# Azimuth: forward azimuth from station1 to station2 in degrees\n",
        "# BackAzimuth: reverse azimuth from station2 to station1 in degrees\n",
        "# MidLat: midpoint latitude in decimal degrees (°N)\n",
        "# MidLon: midpoint longitude in decimal degrees (°E)\n",
        "# DataCompletenessTag: dispersion data completeness based on Z and RT correlation coverage (ZxRTy) where 2 = full AV with both CA and AC branches 1 = AV with incomplete CA/AC coverage and 0 = missing average (AV)\n",
        "# NumberOfDays: number of days stacked for ambient-noise cross-correlation (EGF)\n",
        "Pair,InterstationDistance,Azimuth,BackAzimuth,MidLat,MidLon,DataCompletenessTag,NumberOfDays\n"
    ]

def write_csv_header_networks():
    return [
        "# FDSNCode: FDSN network code or XX for unregistered temporary networks/experiments\n",
        "FDSNcode\n"
    ]

def get_curve_header(attr_code, wave_code, branch_code, period_list):
    """Generates the dynamic metadata header for curve-dependent CSV files."""
    
    attr_names = {
        'GRP': ('GRP (group velocity)', 'group velocity pick at period Period[i]', 'km/s'),
        'PHA': ('PHA (phase velocity)', 'group velocity pick at period Period[i]', 'km/s'),
        'AMP': ('AMP (amplitude)', 'instantaneous envelope amplitude (a.u.) at period Period[i]', 'dimensionless'),
        'SNR': ('SNR (signal-to-noise ratio)', 'signal-to-noise ratio at period Period[i]', 'dB'),
        'BZQ': ('BZQ (Bessel zero quality metric)', 'time difference between upward and downward Bessel zero-crossing velocity picks, normalized by Period[i]', '% (percent of period)')
    }
    
    wave_names = {
        'ZZ': 'RZZ (Rayleigh vertical)',
        'RR': 'RRR (Rayleigh radial)',
        'TT': 'LTT (Love transverse)'
    }
    
    branch_names = {
        'AV': 'AV (average)',
        'CA': 'CA (causal)',
        'AC': 'AC (acausal)'
    }

    attr_desc, val_desc, unit = attr_names[attr_code]
    wave_desc = wave_names[wave_code]
    branch_desc = branch_names[branch_code]

    period_str = "|".join(str(p) for p in period_list)
    val_cols = ",".join([f"Val{i+1}" for i in range(len(period_list))])

    lines = [
        f"# Attribute: {attr_desc}\n",
        f"# Wave type: {wave_desc}\n",
        f"# CCF branch: {branch_desc}\n",
        "# Pair: station1_station2 identifier  \n",
        f"# Val<i>: {val_desc}  \n",
        f"# Units: {unit}\n",
        "# Missing value: nan\n"
    ]
    
    lines.append("# Period sampling in 1/6-octave steps; Effective period range 2.2 s–161 s  \n")    
    lines.append(f"# Period list (s): {period_str}\n")
    lines.append(f"Pair,{val_cols}\n")
    
    return lines

# --- Processing & Writing Functions ---
def format_value(val, fmt_sci=False):
    """Formats values, converting NaNs to 'nan' string and optionally scientific notation."""
    if val is None or math.isnan(val):
        return "nan"
    if fmt_sci:
        return f"{val:.3e}"
    return str(val)

def write_dataset_csvs(disp_dict, dataset_dir):
    """Generates stations, networks, pairs, and curve CSVs, filtering RZZ-only for 1C."""
    # Guard check: Exit early if disp_dict is empty or lacks pairs/curve_id
    if not disp_dict or 'pair' not in disp_dict or len(disp_dict['pair']) == 0:
        print(f"Warning: No data found for {dataset_dir}. Skipping CSV writing.")
        return

    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir, exist_ok=True)

    stations = {}
    networks = set()
    pairs_rows = []

    attrs = {
        'group': ('group_velocity', 'GRP', False),
        'phase': ('phase_velocity', 'PHA', False),
        'amplitude': ('amplitude', 'AMP', True),
        'attribute_snr': ('attribute', 'SNR', False),
        'attribute_bzq': ('attribute', 'BZQ', False)
    }

    wave_file_map = {
        'ZZ': 'RZZ',
        'RR': 'RRR',
        'TT': 'LTT'
    }

    for sub, _, _ in attrs.values():
        os.makedirs(os.path.join(dataset_dir, sub), exist_ok=True)

    curve_ids = disp_dict['curve_id']
    periods = disp_dict['period']
    
    num_pairs = len(disp_dict['pair'])
    sorted_pair_indices = sorted(range(num_pairs), key=lambda idx: disp_dict['pair'][idx])

    # 1. Write Curve Files
    for c_idx, cid in enumerate(curve_ids):
        wave_code, branch_code = cid.split('_')  # e.g., 'ZZ', 'AV'
        wave_file_code = wave_file_map.get(wave_code, wave_code)
        
        # --- FILTER FOR 1C DATASET: ONLY WRITE RZZ FILES ---
        if "Dataset_1C" in dataset_dir and wave_file_code != 'RZZ':
            continue
        
        for attr_key, (subdir, prefix, is_amp) in attrs.items():
            filename = f"{prefix}_{wave_file_code}_{branch_code}.csv"
            filepath = os.path.join(dataset_dir, subdir, filename)
            
            headers = get_curve_header(prefix, wave_code, branch_code, periods)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(headers)
                writer = csv.writer(f)
                
                for idx in sorted_pair_indices:
                    pair_str = disp_dict['pair'][idx]
                    parts = pair_str.split('_')
                    pair_csv_id = f"{parts[0]}.{parts[1]}_{parts[2]}.{parts[3]}"
                    
                    row_vals = disp_dict[attr_key][idx][c_idx]
                    formatted_vals = [format_value(v, fmt_sci=is_amp) for v in row_vals]
                    writer.writerow([pair_csv_id] + formatted_vals)

    # 2. Extract Stations, Networks, and Pairs Metadata
    for idx in sorted_pair_indices:
        pair_str = disp_dict['pair'][idx]
        parts = pair_str.split('_')
        net1, sta1, net2, sta2 = parts[0], parts[1], parts[2], parts[3]
        sta_id1, sta_id2 = f"{net1}.{sta1}", f"{net2}.{sta2}"
        
        networks.add(net1)
        networks.add(net2)

        lat1, lon1, alt1 = disp_dict['lat_lon_alt_1'][idx][:3]
        lat2, lon2, alt2 = disp_dict['lat_lon_alt_2'][idx][:3]
        stations[sta_id1] = (lat1, lon1, alt1)
        stations[sta_id2] = (lat2, lon2, alt2)

        dist, az, baz = disp_dict['dist_azim_az_baz'][idx][:3]
        midlat, midlon, wgt = disp_dict['midlat_midlon_wgt'][idx][:3]
        cv_tag = disp_dict['crossval_tag'][idx].upper()
        
        pairs_rows.append((
            f"{sta_id1}_{sta_id2}", dist, az, baz, midlat, midlon, cv_tag, int(wgt)
        ))

    # 3. Write stations.csv
    with open(os.path.join(dataset_dir, "stations.csv"), "w", encoding="utf-8") as f:
        f.writelines(write_csv_header_stations())
        writer = csv.writer(f)
        for sta_id, coords in sorted(stations.items(), key=lambda x: x[0]):
            writer.writerow([sta_id, coords[0], coords[1], coords[2]])

    # 4. Write networks.csv
    with open(os.path.join(dataset_dir, "networks.csv"), "w", encoding="utf-8") as f:
        f.writelines(write_csv_header_networks())
        writer = csv.writer(f)
        for net_id in sorted(list(networks)):
            writer.writerow([net_id])

    # 5. Write pairs.csv
    with open(os.path.join(dataset_dir, "pairs.csv"), "w", encoding="utf-8") as f:
        f.writelines(write_csv_header_pairs())
        writer = csv.writer(f)
        for row in pairs_rows:
            writer.writerow(row)
