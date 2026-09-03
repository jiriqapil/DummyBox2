# ==== defs4phase.py ====
from imports import *

def phase_search_prep(
    ftan_pick, dist_km, coefT=1.0, vmin=None, vmax=None, tstop=None, cc="ZZ", params=None
):
    """Initializes phase dictionary, clips refV, and constructs searching corridors."""
    if params:
        if cc == "TT":
            coefT = params.get("harmo_coeft", 1.1)
        vmin = params.get("vmin_tap", 1.5) if vmin is None else vmin
        vmax = params.get("vmax_tap", 6.0) if vmax is None else vmax
    else:
        vmin = 1.5 if vmin is None else vmin
        vmax = 6.0 if vmax is None else vmax

    bzero_pick = {
        "period": ftan_pick["period"].copy(),
        "refV": ftan_pick["poly_v"].copy(),
        "refVmin": [],
        "refVmax": [],
        "refVref20": [],
        "pick_v": np.array([]),
        "pick_q": np.array([]),
        "poly_v": np.array([]),
        "ndv_posneg": np.array([]),
        "bzq_posneg": np.array([]),
        "ndv_near": np.array([]),
    }

    refVminI, refVmaxI, refVref20I = [], [], []
    clipRef, clipMin = 0, 0

    for it, valt in enumerate(bzero_pick["period"][::-1]):
        if it >= 20 and bzero_pick["refV"][::-1][it] < clipRef:
            bzero_pick["refV"][::-1][it] = clipRef
        clipRef = bzero_pick["refV"][::-1][it]

        tzero = dist_km / bzero_pick["refV"][::-1][it]

        if dist_km / (tzero + 0.2 * valt) > clipMin:
            clipMin = dist_km / (tzero + 0.2 * valt)
        refVminI.append(clipMin)

        if tzero > valt and dist_km / (tzero - 1 * valt) < 4.3 * coefT:
            refVmaxI.append(dist_km / (tzero - 1 * valt))
        else:
            refVmaxI.append(4.3 * coefT)

        if tzero > valt and dist_km / (tzero - 0.2 * valt) < 4.0 * coefT:
            refVref20I.append(dist_km / (tzero - 0.20 * valt))
        else:
            refVref20I.append(4.0 * coefT)

    bzero_pick["refVmin"] = refVminI[::-1]
    bzero_pick["refVmax"] = refVmaxI[::-1]
    bzero_pick["refVref20"] = refVref20I[::-1]

    return bzero_pick

def phase_get_spectra(tr, dt=0.1, oversample=100):
    """Extracts normalized real spectrum and frequency array from trace."""
    win_samples = len(tr.data)
    xcorr = np.fft.rfft(tr.data, win_samples * oversample)
    freq = np.fft.rfftfreq(win_samples * oversample, dt)

    xcorrNormCoeff = max(np.abs(np.real(xcorr)))
    realspec = np.real(xcorr) / xcorrNormCoeff

    return realspec, freq

def phase_spectrum_refine(
    realspec, freq, despike26=True, smooth=True, detrend=True
):
    """Refines the real spectrum using optional 26s notch despiking, dynamic

    Savitzky-Golay smoothing, and period-dependent detrending.
    """
    metrics = {"n_cyclesFhi": 1, "n_cyclesFlo": 1, "spike26": 0}

    # Dynamic Cycle Counting for Band-Specific Filtering
    fa, fb = 0.03125, 0.125
    mask = (freq >= fa) & (freq <= fb)
    spec_seg = realspec[mask] - np.mean(realspec[mask])
    sign = np.sign(spec_seg)
    n_cyclesFhi = max(
        1, int(np.round(np.sum((sign[:-1] < 0) & (sign[1:] >= 0))))
    )

    fa, fb = 0.00806, 0.03125
    mask = (freq >= fa) & (freq <= fb)
    spec_seg = realspec[mask] - np.mean(realspec[mask])
    sign = np.sign(spec_seg)
    n_cyclesFlo = max(
        1, int(np.round(np.sum((sign[:-1] < 0) & (sign[1:] >= 0))))
    )

    metrics["n_cyclesFhi"] = n_cyclesFhi
    metrics["n_cyclesFlo"] = n_cyclesFlo

    rawspec = realspec.copy()

    # 1. Microseism 26s Resonance Despiking
    if despike26:
        f0, f0idx = 0.038, 2737
        flo, fhi = 0.0357, 0.04
        fwidth = fhi - flo

        fi = np.argmin(np.abs(freq - freq[f0idx]))
        dfreq = freq[1] - freq[0]
        n_spike = max(1, int(round(fwidth / 4 / dfreq)))

        left_zero = any(
            realspec[fj] * realspec[fj + 1] <= 0
            for fj in range(max(0, fi - n_spike), fi)
        )
        right_zero = any(
            realspec[fj] * realspec[fj + 1] <= 0
            for fj in range(fi, min(len(realspec) - 1, fi + n_spike))
        )

        fa, fb = 0.03333, 0.05
        mask = (freq >= fa) & (freq <= fb)
        spec_seg = realspec[mask] - np.mean(realspec[mask])
        sign = np.sign(spec_seg)
        n_cycles26 = np.sum((sign[:-1] < 0) & (sign[1:] >= 0))

        if left_zero and right_zero and n_cycles26 < 8:
            spike26 = 1 if realspec[fi] > 0 else -1
            metrics["spike26"] = spike26
            sigma = (fhi - flo) / 2.355
            blend_sigma = sigma * 1.5
            fweight = np.exp(-0.5 * ((freq - f0) / blend_sigma) ** 2)
            notch = -0.5 * np.exp(-0.5 * ((freq - f0) / sigma) ** 2) * spike26
            rawspec = realspec * (1 - fweight) + notch * fweight

    # 2. Dual-Band Savitzky-Golay Smoothing
    if smooth:
        smoFhi_coef = int(np.round(1200 * n_cyclesFhi ** (-0.5)) / 2) * 2 + 1
        smoFlo_coef = int(np.round(750 * n_cyclesFlo ** (-0.5)) / 2) * 2 + 1

        smo_shortT = savgol_filter(
            rawspec, window_length=smoFhi_coef, polyorder=2
        )
        smo_longT = savgol_filter(
            rawspec, window_length=smoFlo_coef, polyorder=2
        )

        f2, f3 = 0.03, 0.1
        weights = np.clip((f3 - freq) / (f3 - f2), 0, 1)
        weights[freq < f2] = 1
        weights[freq > f3] = 0
        spec_smo = weights * smo_longT + (1 - weights) * smo_shortT
    else:
        spec_smo = rawspec

    # 3. Period-Dependent Moving Average Detrending
    if detrend:
        trendFhi_coef = int(np.round(13600 * n_cyclesFhi ** (-0.7)))
        trendFlo_coef = int(np.round(800000 * n_cyclesFlo ** (-1)))

        x = 1 / (freq[::-1] + 1e-12)
        y = spec_smo[::-1]
        min_win, max_win = trendFhi_coef, trendFlo_coef
        N = len(y)

        cumsum = np.cumsum(np.insert(y, 0, 0))
        trend = np.zeros_like(y)
        step = 10
        idxs = np.arange(0, N, step)
        win_sizes = np.interp(
            x[idxs], [x.min(), x.max()], [min_win, max_win]
        ).astype(int)

        for j, w in zip(idxs, win_sizes):
            i1 = max(0, j - w // 2)
            i2 = min(N, j + w // 2)
            trend[j] = (cumsum[i2] - cumsum[i1]) / (i2 - i1)

        trend = np.interp(np.arange(N), idxs, trend[idxs])
        processed_spec = (y - trend)[::-1]
    else:
        processed_spec = spec_smo

    return processed_spec, metrics

def phase_search_zeros(
    realspec, freq, dist_km, cc="ZZ", vmin=None, vmax=None, tstop=None, params=None
):
    """Finds spectral zero crossings and maps them to Bessel function roots."""
    if params:
        vmin = params.get("vmin_tap", 1.5) if vmin is None else vmin
        vmax = params.get("vmax_tap", 6.0) if vmax is None else vmax
        if cc == "TT":
            harmo_coeft = params.get("harmo_coeft", 1.1)
            vmax = vmax * harmo_coeft
    else:
        vmin = 1.5 if vmin is None else vmin
        vmax = 6.0 if vmax is None else vmax

    if tstop is None:
        tstop = dist_km / vmin / 0.5
    freqmin = 1 / tstop
    freqmax = 0.5

    w = freq[(freq >= freqmin) & (freq <= freqmax)]
    maxf = w[-1]
    ccspec = realspec[(freq >= freqmin) & (freq <= freqmax)]

    cross_idx = np.where((ccspec[:-1] * ccspec[1:] < 0))[0]
    crossings = -ccspec[cross_idx] / (
        ccspec[cross_idx + 1] - ccspec[cross_idx]
    ) * (w[cross_idx + 1] - w[cross_idx]) + w[cross_idx]

    values = ccspec[cross_idx]
    pos_crossings = crossings[values < 0]
    neg_crossings = crossings[values > 0]

    no_bessel_zeros = int(maxf * 2 * np.pi * dist_km / vmin / np.pi)

    if cc in ["ZZ", "RR"]:
        bessel_zeros = jn_zeros(0, no_bessel_zeros)
    else:
        j02_axis = np.linspace(
            0, 2 * np.pi * maxf * dist_km / vmin, no_bessel_zeros * 5
        )
        J02 = jv(0, j02_axis) - jv(2, j02_axis)
        b_cross_idx = np.where((J02[:-1] * J02[1:]) < 0)[0]
        bessel_zeros = -J02[b_cross_idx] / (
            J02[b_cross_idx + 1] - J02[b_cross_idx]
        ) * (j02_axis[b_cross_idx + 1] - j02_axis[b_cross_idx]) + j02_axis[
            b_cross_idx
        ]

    pos_bessel_zeros = bessel_zeros[1::2]
    neg_bessel_zeros = bessel_zeros[0::2]

    pos_crossings_vel, pos_crossings_freqs, bessel_pidx = [], [], []
    neg_crossings_vel, neg_crossings_freqs, bessel_nidx = [], [], []

    for j, pcross in enumerate(pos_crossings):
        velocities = pcross * 2 * np.pi * dist_km / pos_bessel_zeros
        velocities_all = velocities
        velocities = velocities[(velocities > vmin) * (velocities < vmax)]
        pos_crossings_freqs.extend([pcross] * len(velocities))
        pos_crossings_vel.extend(velocities[::-1])
        for val in velocities:
            bessel_pidx.append(velocities_all.tolist().index(val) + 2 - j)

    for j, ncross in enumerate(neg_crossings):
        velocities = ncross * 2 * np.pi * dist_km / neg_bessel_zeros
        velocities_all = velocities
        velocities = velocities[(velocities > vmin) * (velocities < vmax)]
        neg_crossings_freqs.extend([ncross] * len(velocities))
        neg_crossings_vel.extend(velocities[::-1])
        for val in velocities:
            bessel_nidx.append(velocities_all.tolist().index(val) + 1 - j)

    all_crossings_vel = np.hstack((pos_crossings_vel, neg_crossings_vel))
    all_crossings_freqs = np.hstack(
        (pos_crossings_freqs, neg_crossings_freqs)
    )
    all_crossings_idx = np.hstack((bessel_pidx, bessel_nidx))

    crossings_tuple = (
        all_crossings_vel,
        all_crossings_freqs,
        all_crossings_idx,
        np.array(pos_crossings_freqs),
        np.array(neg_crossings_freqs),
        np.array(pos_crossings_vel),
        np.array(neg_crossings_vel),
    )
    return crossings_tuple


def phase_track_bessel(bzero_pick, crossings_tuple, dist_km):
    """Tracks continuous zero-crossing phase picks and separates up/down components."""
    (
        all_crossings_vel,
        all_crossings_freqs,
        _,
        pos_crossings_freqs,
        neg_crossings_freqs,
        _,
        _,
    ) = crossings_tuple

    pbsmp = []
    for val in all_crossings_freqs:
        ival = 1 / val
        if ival not in pbsmp:
            pbsmp.append(ival)

    xou = np.array(np.sort(pbsmp))
    xin = np.array(bzero_pick["period"])
    yin1 = np.array(bzero_pick["refVref20"])
    yin2 = np.array(bzero_pick["refVmin"])
    yin3 = np.array(bzero_pick["refVmax"])

    valid = ~np.isnan(yin1)
    f1 = interp1d(
        xin[valid], yin1[valid], kind="linear", fill_value="extrapolate"
    )
    f2 = interp1d(
        xin[valid], yin2[valid], kind="linear", fill_value="extrapolate"
    )
    f3 = interp1d(
        xin[valid], yin3[valid], kind="linear", fill_value="extrapolate"
    )

    psmp_periodI = xou.tolist()[::-1]
    psmp_pvmaxI = f3(xou).tolist()[::-1]
    psmp_pvminI = f2(xou).tolist()[::-1]
    psmp_pvref20I = f1(xou).tolist()[::-1]

    pv, pt, pf = [], [], []

    for i, vali in enumerate(psmp_periodI):
        flag = 0
        vel, freqs = np.nan, np.nan
        if i == 0:
            v_prevpick = psmp_pvref20I[i]

        count = 0
        for j, valj in enumerate(all_crossings_freqs):
            if (
                vali == 1 / valj
                and all_crossings_vel[j] >= psmp_pvref20I[i]
                and all_crossings_vel[j] < psmp_pvmaxI[i]
            ):
                t_prevpick = dist_km / v_prevpick
                if all_crossings_vel[j] < dist_km / (
                    t_prevpick - 0.5 * vali
                ):
                    count += 1
                    flag = 1
                    if count == 1:
                        vel = all_crossings_vel[j]
                        freqs = all_crossings_freqs[j]

        if flag == 0:
            count = 0
            for jx, valj in enumerate(all_crossings_freqs[::-1]):
                j = len(all_crossings_freqs) - jx - 1
                if (
                    vali == 1 / valj
                    and all_crossings_vel[j] > psmp_pvminI[i]
                    and all_crossings_vel[j] < psmp_pvref20I[i]
                ):
                    t_prevpick = dist_km / v_prevpick
                    if all_crossings_vel[j] > dist_km / (
                        t_prevpick + 0.5 * vali
                    ):
                        count += 1
                        flag = 2
                        if count == 1:
                            vel = all_crossings_vel[j]
                            freqs = all_crossings_freqs[j]

        if flag > 0:
            v_prevpick = vel
            pv.append(vel)
            pt.append(psmp_periodI[i])
            pf.append(freqs)
        else:
            v_prevpick = (v_prevpick + psmp_pvref20I[i]) / 2
            pv.append(np.nan)
            pt.append(psmp_periodI[i])
            pf.append(freqs)

    pt_pos, pt_neg, pv_pos, pv_neg = [], [], [], []
    for iall, valall in enumerate(pf):
        if valall in pos_crossings_freqs:
            pt_pos.append(pt[iall])
            pv_pos.append(pv[iall])
        elif valall in neg_crossings_freqs:
            pt_neg.append(pt[iall])
            pv_neg.append(pv[iall])

    return pt, pv, pt_pos, pt_neg, pv_pos, pv_neg

def phase_eval_dif_updown(
    bzero_pick, pt, pv, pt_pos, pt_neg, pv_pos, pv_neg, dist_km
):
    """Evaluates relative differences (ndv, bzq) between zero crossings and sets quality flags."""
    xin, yin = np.array(pt[::-1]), np.array(pv[::-1])
    xin_pos, yin_pos = np.array(pt_pos[::-1]), np.array(pv_pos[::-1])
    xin_neg, yin_neg = np.array(pt_neg[::-1]), np.array(pv_neg[::-1])

    valid = np.isfinite(yin)
    xin, yin = xin[valid], yin[valid]
    xin_pos, yin_pos = xin_pos[np.isfinite(yin_pos)], yin_pos[np.isfinite(yin_pos)]
    xin_neg, yin_neg = xin_neg[np.isfinite(yin_neg)], yin_neg[np.isfinite(yin_neg)]

    xou = np.array(bzero_pick["period"])
    n_periods = len(xou)

    if len(xin) < 2:
        bzero_pick["pick_v"] = np.full(n_periods, np.nan)
        bzero_pick["pick_q"] = np.ones(n_periods)
        bzero_pick["ndv_near"] = np.full(n_periods, np.nan)
        bzero_pick["ndv_posneg"] = np.full(n_periods, np.nan)
        bzero_pick["bzq_posneg"] = np.full(n_periods, np.nan)
        return bzero_pick

    f = PchipInterpolator(xin, yin, extrapolate=False)
    fpos = (
        PchipInterpolator(xin_pos, yin_pos, extrapolate=False)
        if len(xin_pos) >= 2
        else lambda x: np.full_like(x, np.nan)
    )
    fneg = (
        PchipInterpolator(xin_neg, yin_neg, extrapolate=False)
        if len(xin_neg) >= 2
        else lambda x: np.full_like(x, np.nan)
    )
    fref = interp1d(xin, yin, kind="nearest", fill_value="extrapolate")

    you = f(xou)
    youpos, youneg, youref = fpos(xou), fneg(xou), fref(xou)

    pick_v, pick_q = [], []
    ndv_near_arr, ndv_posneg_arr, bzq_posneg_arr = [], [], []

    for itou, valtou in enumerate(xou):
        current_v = you[itou]

        if np.isfinite(current_v):
            ndv_near = abs(current_v - youref[itou]) / current_v * 100
            pick_v.append(current_v)
            ndv_near_arr.append(np.round(ndv_near, 2))
        else:
            ndv_near = np.nan
            pick_v.append(np.nan)
            ndv_near_arr.append(np.nan)

        if np.isfinite(youpos[itou]) and np.isfinite(youneg[itou]):
            ndv_posneg = abs(youneg[itou] - youpos[itou]) / current_v * 100
            bzq_posneg = (
                abs(dist_km / youpos[itou] - dist_km / youneg[itou])
                / valtou
                * 100
            )
            ndv_posneg_arr.append(np.round(ndv_posneg, 2))
            bzq_posneg_arr.append(np.round(bzq_posneg, 2))
        else:
            ndv_posneg, bzq_posneg = np.nan, np.nan
            ndv_posneg_arr.append(np.nan)
            bzq_posneg_arr.append(np.nan)

        if (
            np.isfinite(ndv_near)
            and np.isfinite(ndv_posneg)
            and ndv_near < 5
            and ndv_posneg < 5
        ):
            pick_q.append(1.0)
        else:
            pick_q.append(0.9 if valtou < 64 and np.isfinite(current_v) else 1.0)

    bzero_pick["pick_v"] = np.array(pick_v)
    bzero_pick["pick_q"] = np.array(pick_q)
    bzero_pick["ndv_near"] = np.array(ndv_near_arr)
    bzero_pick["ndv_posneg"] = np.array(ndv_posneg_arr)
    bzero_pick["bzq_posneg"] = np.array(bzq_posneg_arr)

    prevpick = 0.0
    for it in range(len(bzero_pick["period"]) - 1, -1, -1):
        if bzero_pick["pick_q"][it] == 1.0:
            current_idx = len(bzero_pick["period"]) - 1 - it
            current_v = bzero_pick["pick_v"][it]

            if (
                current_idx >= 20
                and np.isfinite(current_v)
                and current_v < prevpick
            ):
                bzero_pick["pick_q"][it] = 0.8
            elif np.isfinite(current_v):
                prevpick = current_v

    return bzero_pick

def phase_pick_reposition(bzero_pick, target_q=1):
    """Interpolates valid phase picks and applies Savitzky-Golay curve fitting."""
    valid_v, valid_t = [], []
    for p, period in enumerate(bzero_pick["period"]):
        v_val = bzero_pick["pick_v"][p]
        if bzero_pick["pick_q"][p] >= target_q and np.isfinite(v_val):
            valid_v.append(v_val)
            valid_t.append(period)

    if len(valid_v) < 2:
        return bzero_pick

    xin, yin = np.array(valid_t[::-1]), np.array(valid_v[::-1])
    xou = np.array(bzero_pick["period"][::-1])

    interp_yfill = PchipInterpolator(xin, yin, extrapolate=True)
    you = interp_yfill(xou)

    prevpick = 0
    for it, valt in enumerate(you):
        if it >= 20 and you[it] < prevpick:
            you[it] = prevpick
        else:
            prevpick = you[it]

    win_len = min(7, len(you) if len(you) % 2 != 0 else len(you) - 1)
    if win_len >= 3:
        ysm = savgol_filter(you, window_length=win_len, polyorder=2)
    else:
        ysm = you

    bzero_pick["poly_v"] = ysm[::-1]

    return bzero_pick

def phase_refine(
    bzero_pick,
    crossings_tuple,
    dist_km,
    eval_updown=True,
    apply_reposition=True,
    eval_outliers=True,
    outlier_thresh=0.05,
):
    """Refines phase velocity picks through tracking, quality evaluation, outlier rejection,

    and curve repositioning (mirrors `group_refine`).
    """
    # 1. Track Bessel Zero-Crossings
    pt, pv, pt_pos, pt_neg, pv_pos, pv_neg = phase_track_bessel(
        bzero_pick, crossings_tuple, dist_km
    )

    # 2. Quality Flagging / Difference Evaluation
    if eval_updown:
        bzero_pick = phase_eval_dif_updown(
            bzero_pick, pt, pv, pt_pos, pt_neg, pv_pos, pv_neg, dist_km
        )

    # 3. Curve Repositioning
    if apply_reposition:
        bzero_pick = phase_pick_reposition(bzero_pick, target_q=1)

    # 4. Outlier Rejection Pass
    if eval_outliers and "poly_v" in bzero_pick and len(bzero_pick["poly_v"]) > 0:
        for p, period in enumerate(bzero_pick["period"]):
            if (
                bzero_pick["pick_q"][p] == 1
                and abs(bzero_pick["poly_v"][p] - bzero_pick["pick_v"][p])
                >= outlier_thresh * bzero_pick["poly_v"][p]
            ):
                bzero_pick["pick_q"][p] = 0.5

        if apply_reposition:
            bzero_pick = phase_pick_reposition(bzero_pick, target_q=1)

    return bzero_pick

