# ==== defs4group.py
from imports import *
from defs4process import gaussian_bandpass_zeropad

def group_multifilter_apply(
    tr,
    flt4ftan,
    f4f,
    dist_km,
    maxlag,
    Yi,
    vmin=1.0,
    vmax=8.0,
    cc="ZZ",
    multifilter_type="acoustic_butterworth",
    alpha=50.0,
    pad_factor=50,
    params=None,
):
    """
    Applies MFT filtering (Gaussian or Butterworth), distance-dependent tapering,
    velocity domain mapping, envelope extraction, and RMS normalization.
    """
    if params:
        multifilter_type = params.get("multifilter_type", multifilter_type)
        vmin = params.get("vmin_grid", vmin)
        vmax = params.get("vmax_grid", vmax)
        vmin_tap = params.get("vmin_tap", 1.8)
        vmax_tap = params.get("vmax_tap", 4.5)
        harmo_coeft = params.get("harmo_coeft", 1.1)
    else:
        vmin_tap = 1.8
        vmax_tap = 4.5
        harmo_coeft = 1.1

    # Apply scaling coefficient if cross-correlation component is TT
    coefT = harmo_coeft if cc == "TT" else 1.0
    v_min_taper = vmin_tap * coefT
    v_max_taper = vmax_tap * coefT

    bpf = tr.copy()

    # Filter selection
    if multifilter_type.lower() == "ftan_gaussian":
        f0 = flt4ftan["f_ctr"][f4f]
        bpf = gaussian_bandpass_zeropad(bpf, f0=f0, alpha=alpha, pad_factor=pad_factor)
    else:
        bpf.filter(
            "bandpass",
            freqmin=flt4ftan["f_lo"][f4f],
            freqmax=flt4ftan["f_hi"][f4f],
            zerophase=True,
            corners=2,
        )

    # --- SAVE UNTAPERED FILTERED TRACE FOR SNR / INSTANTANEOUS COMPUTATIONS ---
    bpf_filtered = bpf.copy()

    # Tapering grid bounds scaled dynamically
    t_ctr = flt4ftan["t_ctr"][f4f]
    TAPmin = int(np.round(dist_km) / v_max_taper - t_ctr / 2)
    TAPmax = int(np.round(dist_km) / v_min_taper + t_ctr / 2)
    
    if TAPmin < 10:
        TAPmin = 10
    if TAPmax > 710:
        TAPmax = 710

    # Zero out data outside valid velocity window
    bpf.data[: TAPmin * 10] = 0.0
    bpf.data[TAPmax * 10 :] = 0.0
    bpf.taper(type="cosine", max_percentage=0.5, max_length=10)

    # Velocity sampling & resampling
    bpf_t = np.linspace(0, maxlag, len(bpf.data))
    bpf_t[0] = 1e-13  # Guard against division by zero
    bpf_v = dist_km / bpf_t

    valid_mask = (bpf_v > vmin) & (bpf_v < vmax)
    arr_v = bpf_v[valid_mask]
    arr_d = bpf.data[valid_mask]

    # Interpolate envelope to regular velocity axis (Yi)
    env_vreg = Yi[::-1]
    fi = interpolate.interp1d(arr_v, envelope(arr_d), fill_value="extrapolate")
    env_dreg = fi(env_vreg)[::-1]

    # Amplitude Normalization (RMS)
    env_rms = np.sqrt(np.mean(env_dreg**2))
    env_dnorm = env_dreg / (env_rms if env_rms > 0 else 1.0)

    return env_dnorm, bpf_filtered

def group_search_grid(Xii, Yii, Zii, x_new=None, y_new=None):
    """
    Interpolates irregular MFT velocity matrix Zii onto uniform picking grid.
    Defaults x_new to np.linspace(1, 200, 797) if not provided.
    """
    if x_new is None:
        x_new = np.linspace(1, 200, 797)
    if y_new is None:
        y_new = Yii

    Xpp, Ypp = np.meshgrid(x_new, y_new)
    Zpp = interpolate.griddata(
        (Xii.flatten(), Yii.flatten()), Zii.flatten(), (Xpp, Ypp), method="cubic"
    )
    return Xpp, Ypp, Zpp
    


def anchor_line_ref_v(xidx, direction, ref_v_tuple):
    """
    Interpolates reference velocity from anchor points based on index step.
    
    direction : str
        'down' or 'up'
    ref_v_tuple : tuple
        For 'down': (ref_v16, ref_v8, ref_v4, ref_v2)
        For 'up'  : (ref_v16, ref_v32, ref_v64, ref_v128)
    """
    if direction == "down":
        ref_v16, ref_v8, ref_v4, ref_v2 = ref_v_tuple
        weights = {
            22: (1, 0, 0, 0, 1.00),
            23: (1, 0, 0, 0, 1.00),
            24: (1, 0, 0, 0, 1.00),
            25: (5, 1, 0, 0, 1.00),
            26: (4, 2, 0, 0, 1.00),
            27: (3, 3, 0, 0, 1.00),
            28: (2, 4, 0, 0, 1.00),
            29: (1, 5, 0, 0, 1.00),
            30: (0, 1, 0, 0, 1.00),
            31: (0, 5, 1, 0, 0.97),
            32: (0, 4, 2, 0, 0.97),
            33: (0, 3, 3, 0, 0.97),
            34: (0, 2, 4, 0, 0.97),
            35: (0, 1, 5, 0, 0.97),
            36: (0, 0, 1, 0, 0.97),
            37: (0, 0, 5, 1, 0.97),
            38: (0, 0, 4, 2, 0.97),
            39: (0, 0, 3, 3, 0.97),
            40: (0, 0, 2, 4, 0.97),
            41: (0, 0, 1, 5, 0.97),
            42: (0, 0, 0, 1, 0.97),
        }
        if xidx in weights:
            w16, w8, w4, w2, factor = weights[xidx]
            total = w16 + w8 + w4 + w2
            return factor * (
                (w16 * ref_v16 + w8 * ref_v8 + w4 * ref_v4 + w2 * ref_v2) / total
            )

    elif direction == "up":
        ref_v16, ref_v32, ref_v64, ref_v128 = ref_v_tuple
        weights = {
            25: (5, 1, 0, 0),
            26: (4, 2, 0, 0),
            27: (3, 3, 0, 0),
            28: (2, 4, 0, 0),
            29: (1, 5, 0, 0),
            30: (0, 1, 0, 0),
            31: (0, 5, 1, 0),
            32: (0, 4, 2, 0),
            33: (0, 3, 3, 0),
            34: (0, 2, 4, 0),
            35: (0, 1, 5, 0),
            36: (0, 0, 1, 0),
            37: (0, 0, 5, 1),
            38: (0, 0, 4, 2),
            39: (0, 0, 3, 3),
            40: (0, 0, 2, 4),
            41: (0, 0, 1, 5),
            42: (0, 0, 0, 1),
            43: (0, 0, 0, 1),
            44: (0, 0, 0, 1),
        }
        if xidx in weights:
            w16, w32, w64, w128 = weights[xidx]
            total = w16 + w32 + w64 + w128
            return (
                w16 * ref_v16 + w32 * ref_v32 + w64 * ref_v64 + w128 * ref_v128
            ) / total

    return None

def group_search_prep(cc, anchors, params=None):
    """
    Initializes picking parameters, a fresh ftan_pick dictionary, 
    and reference anchor velocities for each trace.
    """
    harmo_coeft = params.get("harmo_coeft", 1.1) if params else 1.1
    coefT = harmo_coeft if cc == "TT" else 1.0

    # Freshly initialized for every trace iteration
    ftan_pick = {
        'period': np.array([]),
        'pick_v': np.array([]),
        'pick_q': np.array([]),
        'poly_v': np.array([]),
        'pick_vmin': np.array([]),
        'pick_vmax': np.array([]),
        'pick_snr': np.array([]),
        'pick_vraw': np.array([]),        
        'period_inst': np.array([]),
        'pick_signal': np.array([]),
        'pick_noise': np.array([]),
    }

    ref_v = anchors["pickv"][2]     # anchV(16s)
    ref_v16 = anchors["pickv"][2]   # anchV(16s)
    ref_v8 = anchors["pickv"][1]    # anchV(8s)

    if anchors["pickv"][0] <= anchors["pickv"][1]:  # anchV(4s) < anchV(8s)
        ref_v4 = anchors["pickv"][0]
    else:
        ref_v4 = anchors["pickv"][1]

    ref_v2 = 0.9 * ref_v4
    if ref_v2 < 1.8 * coefT:
        ref_v2 = 1.8 * coefT

    ref_v32 = anchors["pickv"][3]   # anchV(32s)
    ref_v64 = anchors["pickv"][4]   # anchV(64s)
    ref_v128 = anchors["pickv"][5]  # anchV(128s)

    if ref_v64 < 0.95 * ref_v32:
        ref_v64 = 0.95 * ref_v32
    if ref_v128 < ref_v64:
        ref_v128 = ref_v64

    anchor_tuple_down = (ref_v16, ref_v8, ref_v4, ref_v2)
    anchor_tuple_up = (ref_v16, ref_v32, ref_v64, ref_v128)

    return coefT, ftan_pick, ref_v, anchor_tuple_down, anchor_tuple_up

def group_search_downwards(
    ZiiPICK,
    Xi,
    Yi,
    dist_km,
    coefT,
    ftan_pick,
    ref_v,
    anchor_tuple_down,
    cc="ZZ",
    params=None,
):
    if params and cc == "TT":
        coefT = params.get("harmo_coeft", 1.1)

    """
    Performs group velocity picking downwards from 16s anchor towards short periods.
    """
    ref_idx = next(
        iter(np.where(np.round(Yi, 2) == np.round(ref_v, 0))[0]), None
    )

    for xidx, ftanx in enumerate(ZiiPICK.T[::-1]):
        xidx_r = len(ZiiPICK.T) - xidx - 1
        period = np.round(Xi[xidx_r], 1)

        if 2.2 <= period <= 20.2:
            ref_t = dist_km / ref_v
            ref_l = ref_v * period

            if period >= 12:
                pickmin_v = ref_v - (0.5 * ref_l) / ref_t
                pickmax_v = ref_v + (0.5 * ref_l) / ref_t

                if pickmin_v < 1.8 * coefT:
                    pickmin_v = 1.8 * coefT
                if pickmax_v > 4 * coefT:
                    pickmax_v = 4 * coefT

                if ref_v - pickmin_v < 0.075 * ref_v:
                    pickmin_v = ref_v - 0.075 * ref_v
                if pickmax_v - ref_v < 0.075 * ref_v:
                    pickmax_v = ref_v + 0.075 * ref_v
            else:
                pickmin_v = ref_v - (0.75 * ref_l) / ref_t
                pickmax_v = ref_v + (0.25 * ref_l) / ref_t

                if pickmin_v < 1.8 * coefT:
                    pickmin_v = 1.8 * coefT
                if pickmax_v > 4 * coefT:
                    pickmax_v = 4 * coefT

                if ref_v - pickmin_v < 0.1 * ref_v:
                    pickmin_v = ref_v - 0.1 * ref_v
                if pickmax_v - ref_v < 0.05 * ref_v:
                    pickmax_v = ref_v + 0.05 * ref_v

            pickmin_idx = ref_idx - int((ref_v - pickmin_v) / 0.01)
            pickmax_idx = ref_idx + int((pickmax_v - ref_v) / 0.01)

            ftan_pick["period"] = np.append(ftan_pick["period"], period)
            ftan_pick["pick_vmin"] = np.append(
                ftan_pick["pick_vmin"], pickmin_v
            )
            ftan_pick["pick_vmax"] = np.append(
                ftan_pick["pick_vmax"], pickmax_v
            )

            for ycut, val in enumerate(ftanx):
                if ycut < pickmin_idx - 1:
                    ftanx[ycut] = 0
                elif ycut > pickmax_idx + 1:
                    ftanx[ycut] = 0

            pick_idx = np.argmax(ftanx)
            pick_v = Yi[pick_idx]

            if (
                pick_v < 1.8 * coefT
                or pick_v > 4 * coefT
                or pick_idx <= pickmin_idx
                or pick_idx >= pickmax_idx
            ):
                pick_q = 0
                new_ref_v = anchor_line_ref_v(
                    xidx, "down", anchor_tuple_down
                )
                if new_ref_v is not None:
                    ref_v = new_ref_v

                ref_idx = next(
                    iter(
                        np.where(np.round(Yi, 2) == np.round(ref_v, 2))[0]
                    ),
                    None,
                )
                pick_idx = ref_idx
                pick_v = ref_v
                ftan_pick["pick_v"] = np.append(ftan_pick["pick_v"], pick_v)
                ftan_pick["pick_q"] = np.append(ftan_pick["pick_q"], pick_q)
            else:
                pick_q = 1
                if 1 * period * pick_v >= dist_km:
                    pick_q = 0
                ftan_pick["pick_v"] = np.append(ftan_pick["pick_v"], pick_v)
                ftan_pick["pick_q"] = np.append(ftan_pick["pick_q"], pick_q)

            new_ref_v = anchor_line_ref_v(xidx, "down", anchor_tuple_down)
            if new_ref_v is not None:
                ref_v = new_ref_v

            ref_v = (pick_v + ref_v) / 2
            ref_idx = next(
                iter(np.where(np.round(Yi, 2) == np.round(ref_v, 2))[0]),
                None,
            )

    # Delete overlap between up & down (first two picks, 18s and 20.2s)
    for key in ["period", "pick_v", "pick_q", "pick_vmin", "pick_vmax"]:
        ftan_pick[key] = np.delete(ftan_pick[key], [0, 1])

    return ftan_pick

def group_search_upwards(
    ZiiPICK,
    Xi,
    Yi,
    dist_km,
    coefT,
    ftan_pick,
    ref_v16,
    anchor_tuple_up,
    cc="ZZ",
    params=None,
):
    if params and cc == "TT":
        coefT = params.get("harmo_coeft", 1.1)

    """
    Performs group velocity picking upwards towards long periods.
    """
    if len(ftan_pick["pick_q"]) > 0 and ftan_pick["pick_q"][0] == 1:
        ref_v = ftan_pick["pick_v"][0]
    else:
        ref_v = ref_v16

    ref_idx = next(
        iter(np.where(np.round(Yi, 2) == np.round(ref_v, 2))[0]), None
    )
    pick_v = ref_v

    for xidx, ftanx in enumerate(ZiiPICK.T):
        period = np.round(Xi[xidx], 1)
        if 18 <= period < 162:
            previous_v = pick_v
            previous_idx = (
                pick_idx if "pick_idx" in locals() else ref_idx
            )

            ref_t = dist_km / ref_v
            ref_l = ref_v * period

            pickmin_v = ref_v - (0.5 * ref_l) / ref_t
            pickmax_v = ref_v + (0.5 * ref_l) / ref_t
            if pickmin_v < 1.8 * coefT:
                pickmin_v = 1.8 * coefT
            if pickmax_v > 3.4 * coefT:
                pickmax_v = 3.4 * coefT

            if 20.2 <= period <= 25.4:
                pickmin_v = ref_v - (0.4 * ref_l) / ref_t
                pickmax_v = ref_v + (0.6 * ref_l) / ref_t
                if pickmin_v < 1.9 * coefT:
                    pickmin_v = 1.9 * coefT
                if pickmax_v > 3.6 * coefT:
                    pickmax_v = 3.6 * coefT
            elif 28.5 <= period <= 35.9:
                pickmin_v = ref_v - (0.3 * ref_l) / ref_t
                pickmax_v = ref_v + (0.7 * ref_l) / ref_t
                if pickmin_v < 2.0 * coefT:
                    pickmin_v = 2.0 * coefT
                if pickmax_v > 3.8 * coefT:
                    pickmax_v = 3.8 * coefT
            elif 40.3 <= period <= 50.8:
                pickmin_v = ref_v - (0.2 * ref_l) / ref_t
                pickmax_v = ref_v + (0.8 * ref_l) / ref_t
                if pickmin_v < 2.5 * coefT:
                    pickmin_v = 2.5 * coefT
                if pickmax_v > 4.0 * coefT:
                    pickmax_v = 4.0 * coefT
            elif period >= 57.0:
                pickmin_v = ref_v - (0.1 * ref_l) / ref_t
                pickmax_v = ref_v + (0.9 * ref_l) / ref_t
                if pickmin_v < 2.75 * coefT:
                    pickmin_v = 2.75 * coefT
                if pickmax_v > 4.0 * coefT:
                    pickmax_v = 4.0 * coefT

            if ref_v - pickmin_v < 0.1 * ref_v:
                pickmin_v = ref_v - 0.1 * ref_v
            if pickmax_v - ref_v < 0.1 * ref_v:
                pickmax_v = ref_v + 0.1 * ref_v

            pickmin_idx = ref_idx - int((ref_v - pickmin_v) / 0.01)
            pickmax_idx = ref_idx + int((pickmax_v - ref_v) / 0.01)

            ftan_pick["period"] = np.insert(
                ftan_pick["period"], 0, period
            )
            ftan_pick["pick_vmin"] = np.insert(
                ftan_pick["pick_vmin"], 0, pickmin_v
            )
            ftan_pick["pick_vmax"] = np.insert(
                ftan_pick["pick_vmax"], 0, pickmax_v
            )

            for ycut, val in enumerate(ftanx):
                if ycut < pickmin_idx - 1:
                    ftanx[ycut] = 0
                elif ycut > pickmax_idx + 1:
                    ftanx[ycut] = 0

            pick_idx = np.argmax(ftanx)
            pick_v = Yi[pick_idx]

            out_bounds = (
                (
                    xidx <= 25
                    and (
                        pick_v < 1.8 * coefT
                        or pick_v > 3.4 * coefT
                        or pick_idx <= pickmin_idx
                        or pick_idx >= pickmax_idx
                    )
                )
                or (
                    (26 <= xidx <= 28)
                    and (
                        pick_v < 1.9 * coefT
                        or pick_v > 3.6 * coefT
                        or pick_idx <= pickmin_idx
                        or pick_idx >= pickmax_idx
                    )
                )
                or (
                    (29 <= xidx <= 31)
                    and (
                        pick_v < 2.0 * coefT
                        or pick_v > 3.8 * coefT
                        or pick_idx <= pickmin_idx
                        or pick_idx >= pickmax_idx
                    )
                )
                or (
                    (32 <= xidx <= 34)
                    and (
                        pick_v < 2.5 * coefT
                        or pick_v > 4.0 * coefT
                        or pick_idx <= pickmin_idx
                        or pick_idx >= pickmax_idx
                    )
                )
                or (
                    xidx >= 35
                    and (
                        pick_v < 2.75 * coefT
                        or pick_v > 4.0 * coefT
                        or pick_idx <= pickmin_idx
                        or pick_idx >= pickmax_idx
                    )
                )
            )

            if out_bounds:
                pick_q = 0
                new_ref_v = anchor_line_ref_v(xidx, "up", anchor_tuple_up)
                if new_ref_v is not None:
                    ref_v = new_ref_v

                try:
                    ref_idx = next(
                        iter(
                            np.where(np.round(Yi, 2) == np.round(ref_v, 2))[0]
                        ),
                        None,
                    )
                    pick_idx = ref_idx
                    pick_v = ref_v
                except Exception:
                    pick_idx = previous_idx
                    pick_v = previous_v
                    print("exception_outside xidx=", xidx)
                    pass

                ftan_pick["pick_v"] = np.insert(
                    ftan_pick["pick_v"], 0, pick_v
                )
                ftan_pick["pick_q"] = np.insert(
                    ftan_pick["pick_q"], 0, pick_q
                )
            else:
                pick_q = 1
                ftan_pick["pick_v"] = np.insert(
                    ftan_pick["pick_v"], 0, pick_v
                )
                ftan_pick["pick_q"] = np.insert(
                    ftan_pick["pick_q"], 0, pick_q
                )

            new_ref_v = anchor_line_ref_v(xidx, "up", anchor_tuple_up)
            if new_ref_v is not None:
                ref_v = new_ref_v

            try:
                ref_v = (pick_v + ref_v) / 2
                ref_idx = next(
                    iter(np.where(np.round(Yi, 2) == np.round(ref_v, 2))[0]),
                    None,
                )
            except Exception:
                print("exception_inside xidx=", xidx)
                pass

    return ftan_pick

def group_get_instantaneous(
    ftan_pick, flt4ftan, bpf_stream, dist_km, noise_window=(4200, 6000)
):
    """Extracts instantaneous period, signal RMS, and noise RMS via Hilbert transform.

    All arrays are stored in natural period order (matching ftan_pick['period']).
    """
    ftan_pick["pick_vraw"] = ftan_pick["pick_v"].copy()
    ftan_pick["period_inst"] = np.full_like(ftan_pick["period"], np.nan)
    ftan_pick["signal_inst"] = np.full_like(ftan_pick["period"], np.nan)
    ftan_pick["noise_inst"] = np.full_like(ftan_pick["period"], np.nan)

    t_ctr_arr = np.array(flt4ftan["t_ctr"])

    for iftan, vftan in enumerate(ftan_pick["period"]):
        # Robust center-period index lookup
        f4f = np.argmin(np.abs(t_ctr_arr - vftan))
        bpf = bpf_stream[f4f]

        # Define signal window centered on travel time (+/- 0.5 cycle)
        idx_t0 = int(np.round(dist_km / ftan_pick["pick_v"][iftan] * 10) + 1)
        half_cycle = int(np.round(0.5 * ftan_pick["period"][iftan] * 10))
        idx_tf = max(0, idx_t0 - half_cycle)
        idx_tl = idx_t0 + half_cycle

        # Extract signal slice
        FIdata = bpf.data[idx_tf:idx_tl]
        if len(FIdata) == 0 or np.all(FIdata == 0):
            continue

        # Analytic signal & Hilbert envelope
        analytic = hilbert(FIdata)
        env = np.abs(analytic)
        idx_tau = np.argmax(env)

        # Instantaneous Signal Amplitude evaluated at the envelope peak
        ftan_pick["signal_inst"][iftan] = env[idx_tau]

        # Extract noise slice & calculate Hilbert envelope noise amplitude
        noise_slice = bpf.data[noise_window[0] : noise_window[1]]
        if len(noise_slice) > 0 and not np.all(noise_slice == 0):
            noise_env = np.abs(hilbert(noise_slice))
            ftan_pick["noise_inst"][iftan] = np.mean(noise_env)
        else:
            ftan_pick["noise_inst"][iftan] = 0.0

        # Phase & Instantaneous Period
        phase = np.unwrap(np.angle(analytic))
        dphi_dt = np.gradient(phase, bpf.stats.delta)
        f_inst = gaussian_filter1d(dphi_dt / (2 * np.pi), sigma=2)
        fi = f_inst[idx_tau]

        inst_period = (
            np.round(1 / fi, 2) if fi > 0 else ftan_pick["period"][iftan]
        )
        ftan_pick["period_inst"][iftan] = inst_period

        # Quality check: Invalidate if instantaneous frequency crosses filter edges
        t_hi_edge = 1 / flt4ftan["f_hi_edge"][f4f]
        t_lo_edge = 1 / flt4ftan["f_lo_edge"][f4f]

        if inst_period < t_hi_edge or inst_period >= t_lo_edge:
            ftan_pick["pick_q"][iftan] = 0.33
            ftan_pick["period_inst"][iftan] = ftan_pick["period"][iftan]

    return ftan_pick

def group_apply_reposition(ftan_pick, xin, yin_filled):
    """Repositions instantaneous-period velocities, signal, and noise onto target grid

    using PCHIP interpolation.

    Returns all arrays back to the original ftan_pick['period'] direction.
    """
    # Reverse to ascending order for PCHIP
    xinIF = ftan_pick["period_inst"][::-1]
    xouIF = ftan_pick["period"][::-1]

    nan_mask = np.isnan(xinIF)
    if np.any(nan_mask):
        xinIF[nan_mask] = xouIF[nan_mask]

    # Sort x and y pairs by instantaneous period for strict monotonicity
    sort_idx = np.argsort(xinIF)
    xinIF_sorted = xinIF[sort_idx]

    # Remove exact duplicate instantaneous periods
    xinIF_unique, unique_idx = np.unique(xinIF_sorted, return_index=True)

    # Sort target periods output grid
    sort_xou = np.argsort(xouIF)
    xou_sorted = xouIF[sort_xou]
    inv_sort_xou = np.argsort(sort_xou)

    def _reposition_asc(arr_asc):
        """Interpolates an ASCENDING array (matching xinIF grid) and returns it in

        DESCENDING order to match ftan_pick['period'].
        """
        arr_sorted = arr_asc[sort_idx]
        arr_unique = arr_sorted[unique_idx]
        interp = PchipInterpolator(xinIF_unique, arr_unique, extrapolate=True)
        yout_sorted = interp(xou_sorted)
        return yout_sorted[inv_sort_xou][::-1]

    # 1. Reposition Group Velocity (yin_filled is ALREADY ascending from group_apply_infill)
    ftan_pick["pick_v"] = _reposition_asc(yin_filled)

    # 2. Reposition Signal & Noise (signal_inst/noise_inst are descending, so [::-1] makes them ascending)
    sig_asc = np.nan_to_num(ftan_pick["signal_inst"][::-1], nan=0.0)
    noise_asc = np.nan_to_num(ftan_pick["noise_inst"][::-1], nan=1e-12)

    ftan_pick["pick_signal"] = _reposition_asc(sig_asc)
    ftan_pick["pick_noise"] = _reposition_asc(noise_asc)

    # 3. Compute pick_snr in dB (both pick_signal and pick_noise are now descending)
    with np.errstate(divide="ignore", invalid="ignore"):
        snr_db = np.where(
            (ftan_pick["pick_noise"] > 0) & np.isfinite(ftan_pick["pick_signal"]),
            20 * np.log10(
                np.maximum(ftan_pick["pick_signal"], 1e-12)
                / np.maximum(ftan_pick["pick_noise"], 1e-12)
            ),
            0.0,
        )
    ftan_pick["pick_snr"] = np.maximum(0.0, np.round(snr_db, 1))

    return ftan_pick

def group_eval_snr(ftan_pick, snr_threshold=None, q_flag=0.20, params=None):
    if snr_threshold is None:
        snr_threshold = params.get("snrcut", 1.0) if params else 1.0
    """Evaluates SNR against threshold `snr_threshold`.
    Only downgrades pick_q to q_flag if pick_q > 0 and pick_snr < snr_threshold.
    Never upgrades pick_q under any circumstances.
    """
    q = ftan_pick["pick_q"].copy()
    snr = ftan_pick["pick_snr"]

    # Identify entries with quality > 0 that fail SNR threshold
    mask_downgrade = (q > 0) & (snr < snr_threshold)
    q[mask_downgrade] = q_flag

    ftan_pick["pick_q"] = q
    return ftan_pick

def group_eval_slope(ftan_pick, dist_km, order=1):
    """Evaluates local dispersion slope across 2x-3x wavelength windows.

    Flags invalid negative slopes with q=0.10 or q=0.75.
    """
    cutlambda_idx, keeplambda_idx = 999, 999
    for junksmp, (p, v) in enumerate(
        zip(ftan_pick["period"], ftan_pick["pick_v"])
    ):
        if (
            2 * p * v < dist_km
            and junksmp < cutlambda_idx
            and ftan_pick["pick_q"][junksmp] == 1
        ):
            cutlambda_idx = junksmp
        if 3 * p * v < dist_km and junksmp < keeplambda_idx:
            keeplambda_idx = junksmp

    slopemin_idx = min(17, keeplambda_idx)
    slopemax_idx = cutlambda_idx

    rev_periods = ftan_pick["period"][::-1]
    rev_picks = ftan_pick["pick_v"][::-1]
    rev_q = ftan_pick["pick_q"][::-1]

    for ismp in range(len(ftan_pick["period"][slopemax_idx : slopemin_idx + 1])):
        mid = len(ftan_pick["period"]) - slopemin_idx + ismp - 1
        x = rev_periods[mid - 2 : mid + 3]
        y = rev_picks[mid - 2 : mid + 3]

        idx = np.isfinite(x) & np.isfinite(y)
        if np.count_nonzero(idx) >= 3:
            slope = np.polyfit(x[idx], y[idx], order)[0]
            if (
                rev_q[mid] == 1
                and 3 * rev_periods[mid] * rev_picks[mid] > dist_km
            ):
                if slope < -0.01:
                    rev_q[mid] = 0.10
                elif slope < 0:
                    rev_q[mid] = 0.75

    ftan_pick["pick_q"] = rev_q[::-1]
    return ftan_pick    

def group_eval_outliers(ftan_pick, coefT=1.0, cc="ZZ", threshold=0.025, params=None):
    """
    Clips out-of-bound group velocities using dynamic vmin_tap/vmax_tap 
    and harmo_coeft scaling for TT component.
    """
    if params:
        vmin_tap = params.get("vmin_tap", 1.8)
        vmax_tap = params.get("vmax_tap", 4.5)
        if cc == "TT":
            coefT = params.get("harmo_coeft", 1.1)
    else:
        vmin_tap = 1.8
        vmax_tap = 4.5

    v_max = vmax_tap * coefT if cc == "TT" else vmax_tap
    v_min = vmin_tap

    # 1. Physical boundary clipping pass (flags q = 0.55 for out-of-bounds)
    out_of_bounds = (
        (ftan_pick["pick_v"] < v_min)
        | (ftan_pick["pick_v"] > v_max)
        | np.isnan(ftan_pick["pick_v"])
    )
    ftan_pick["pick_v"] = np.clip(ftan_pick["pick_v"], v_min, v_max)
    ftan_pick["pick_q"][out_of_bounds] = 0.55

    # 2. Savitzky-Golay trend outlier pass (flags q = 0.50)
    for p in range(len(ftan_pick["period"])):
        if (
            ftan_pick["pick_q"][p] >= 0.75
            and abs(ftan_pick["poly_v"][p] - ftan_pick["pick_v"][p])
            >= threshold * ftan_pick["poly_v"][p]
        ):
            ftan_pick["pick_q"][p] = 0.50

    return ftan_pick

def group_apply_infill(ftan_pick, anchors, dist_km):
    """
    Masks invalid picks (q < 0.75 or 2*T*v >= dist_km).
    - Anchor PCHIP infill is applied ONLY if both adjacent neighbors (i-1 and i+1) are invalid.
    - Isolated invalid picks (adjacent to at least 1 valid pick) are filled via PCHIP on valid/known points.
    
    Returns (xin, yin_filled) in ASCENDING period order.
    """
    valid_v = [
        v if q >= 0.75 and 2 * p * v < dist_km else np.nan
        for p, v, q in zip(
            ftan_pick["period"], ftan_pick["pick_v"], ftan_pick["pick_q"]
        )
    ]

    # Preserve original flip: xin and yin are ASCENDING ([::-1])
    xin = ftan_pick["period"][::-1]
    yin = np.array(valid_v[::-1])

    # Ensure anchor coordinates are strictly sorted ascending for PCHIP
    xfill = np.array(anchors["flt4anch"]["t_ctr"])
    yfill = np.array(anchors["pickv"])
    sort_anch = np.argsort(xfill)
    xfill_sorted, yfill_sorted = xfill[sort_anch], yfill[sort_anch]
    xfill_unique, unique_idx = np.unique(xfill_sorted, return_index=True)
    yfill_unique = yfill_sorted[unique_idx]

    interp_anchor = PchipInterpolator(
        xfill_unique, yfill_unique, extrapolate=True
    )

    # xin is ascending; sort_xin preserves exact ascending grid alignment
    sort_xin = np.argsort(xin)
    xin_sorted = xin[sort_xin]
    yin_sorted = yin[sort_xin]
    n_pts = len(xin_sorted)

    yfill_on_xin = interp_anchor(xin_sorted)

    # Identify multi-point invalid regions (both neighbors invalid)
    is_nan = np.isnan(yin_sorted)
    to_anchor_infill = np.zeros(n_pts, dtype=bool)

    for i in range(n_pts):
        if is_nan[i]:
            left_invalid = (i == 0) or is_nan[i - 1]
            right_invalid = (i == n_pts - 1) or is_nan[i + 1]
            if left_invalid and right_invalid:
                to_anchor_infill[i] = True

    # Fill multi-point gaps with Anchor values
    yin_partially_filled = np.where(to_anchor_infill, yfill_on_xin, yin_sorted)

    # Local PCHIP interpolation for isolated invalid points
    known_mask = ~np.isnan(yin_partially_filled)
    if np.any(~known_mask):
        if np.sum(known_mask) >= 2:
            interp_local = PchipInterpolator(
                xin_sorted[known_mask], yin_partially_filled[known_mask], extrapolate=True
            )
            yin_filled_sorted = np.where(
                np.isnan(yin_partially_filled),
                interp_local(xin_sorted),
                yin_partially_filled,
            )
        else:
            yin_filled_sorted = yfill_on_xin
    else:
        yin_filled_sorted = yin_partially_filled

    # Restore original order of xin (ASCENDING)
    inv_sort_xin = np.argsort(sort_xin)
    return xin, yin_filled_sorted[inv_sort_xin]

def group_refine(
    ftan_pick_in,
    flt4ftan,
    bpf_stream,
    anchors,
    dist_km,
    coefT=1.0,
    cc="ZZ",
    snr_threshold=None,
    eval_slope=True,
    eval_snr=True,
    eval_outliers=True,
    params=None,
):
    if params:
        if snr_threshold is None:
            snr_threshold = params.get("snrcut", 1.0)
        if cc == "TT":
            coefT = params.get("harmo_coeft", 1.1)
    elif snr_threshold is None:
        snr_threshold = 1.0

    ftan_pick = copy.deepcopy(ftan_pick_in)

    # 1. Instantaneous Parameters
    ftan_pick = group_get_instantaneous(ftan_pick, flt4ftan, bpf_stream, dist_km)

    # 2. Slope Evaluation
    if eval_slope:
        ftan_pick = group_eval_slope(ftan_pick, dist_km)

    # 3. First Infill & Reposition
    xin, yin_filled = group_apply_infill(ftan_pick, anchors, dist_km)
    ftan_pick = group_apply_reposition(ftan_pick, xin, yin_filled)

    # 4. First SNR Pass
    if eval_snr:
        ftan_pick = group_eval_snr(ftan_pick, snr_threshold=snr_threshold, q_flag=0.20, params=params)

    # 5. Savitzky-Golay Trend Line
    yinIF = ftan_pick["pick_v"][::-1]
    ftan_pick["poly_v"] = savgol_filter(yinIF, window_length=7, polyorder=2)[::-1]

    ftan_pick["poly_v"][-1] = ftan_pick["pick_v"][-1]
    ftan_pick["poly_v"][-2] = 0.50 * ftan_pick["poly_v"][-2] + 0.50 * ftan_pick["pick_v"][-2]
    ftan_pick["poly_v"][-3] = 0.75 * ftan_pick["poly_v"][-3] + 0.25 * ftan_pick["pick_v"][-3]

    # 6. Outlier & Physical Clipping Pass
    if eval_outliers:
        ftan_pick = group_eval_outliers(ftan_pick, coefT=coefT, cc=cc, threshold=0.025, params=params)
        xin, yin_filled = group_apply_infill(ftan_pick, anchors, dist_km)
        ftan_pick = group_apply_reposition(ftan_pick, xin, yin_filled)

        ftan_pick["poly_v"] = savgol_filter(yin_filled, window_length=7, polyorder=2)[::-1]

        ftan_pick["poly_v"][-1] = ftan_pick["pick_v"][-1]
        ftan_pick["poly_v"][-2] = 0.50 * ftan_pick["poly_v"][-2] + 0.50 * ftan_pick["pick_v"][-2]
        ftan_pick["poly_v"][-3] = 0.75 * ftan_pick["poly_v"][-3] + 0.25 * ftan_pick["pick_v"][-3]

    # 7. Final SNR Pass
    if eval_snr:
        ftan_pick = group_eval_snr(ftan_pick, snr_threshold=snr_threshold, q_flag=0.25, params=params)

    return ftan_pick, yin_filled    

def group_amp2atten(ftan_pick, dist_km):
    """
    Computes apparent attenuation alpha_app (1/m) vs Period.
    """
    r_m = dist_km * 1000.0
    r_rad = dist_km / 6371.0
    geom_factor = np.sqrt(np.sin(r_rad))

    period = np.array(ftan_pick["period"])
    signal = np.array(ftan_pick["pick_signal"])

    # Calculate Geometrical Amplitude and Apparent Attenuation (1/m)
    A_geom = signal * geom_factor
    
    with np.errstate(divide='ignore', invalid='ignore'):
        alpha_app = -np.log(A_geom) / r_m

    return period, alpha_app
