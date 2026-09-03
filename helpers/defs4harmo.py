# ==== defs4harmo.py ==============
from imports import *

def anchor_init():
    """Initializes the 3C dictionary."""
    return {
        "rawZ": [], "rawR": [], "rawT": [],
        "snrZ": [], "snrR": [], "snrT": [],
        "qZ": [], "qR": [], "qT": [],
        "finZ": [], "finR": [], "finT": [],
        "nZ": 0, "nR": 0, "nT": 0,
        "coefZ": [], "coefR": [], "coefT": [],
    }

def harmo_trends_search(st, dist_km, flt4anch, anch3C, cc, acc, harmo_snrcut=3.0, params=None):
    harmo_snrcut = params.get("harmo_snrcut", harmo_snrcut) if params else harmo_snrcut

    """Pass 1: Computes initial 8-32s microseismic trends for a single component."""
    anch1c = {
        "flt4anch": flt4anch,
        "rmswin": [4, 8, 14, 23, 37, 58],
        "vmin":   [0, 1.5, 1.5, 99, 99, 99],
        "vmax":   [0, 3.5, 3.75, 99, 99, 99],
        "midt":   [0, 0, 0, 0, 0, 0],
        "snr":    [0, 0, 0, 0, 0, 0],
        "maxt":   [0, 0, 0, 0, 0, 0],
        "signal": [0, 0, 0, 0, 0, 0],
        "noise":  [0, 0, 0, 0, 0, 0],
        "pickv":  [0, 0, 0, 0, 0, 0],
        "pickq":  [1, 1, 1, 1, 1, 1], 
        "tapmin": [], "tapmax": [],
    }    
    anch = read().clear(); anchN = read().clear()

    # Tapmin / Tapmax
    for i, _ in enumerate(anch1c["flt4anch"]["band"]):
        tctr = anch1c["flt4anch"]["t_ctr"][i]
        tmin = max(int(dist_km / 4.5 - tctr / 2), 10)
        tmax = min(int(dist_km / 1.5 + tctr / 2), 720)
        anch1c["tapmin"].append(tmin)
        anch1c["tapmax"].append(tmax)

    # Bandpass + envelope            
    for i, _ in enumerate(anch1c["flt4anch"]["band"]):
        f_lo, f_hi, tctr = anch1c["flt4anch"]["f_lo"][i], anch1c["flt4anch"]["f_hi"][i], anch1c["flt4anch"]["t_ctr"][i]
        bpf = st[0 + acc].copy()
        bpf.taper(type="cosine", max_percentage=0.5, max_length=10)
        bpf.filter("bandpass", freqmin=f_lo, freqmax=f_hi, zerophase=True, corners=2)
        bpf.taper(type="cosine", max_percentage=0.5, max_length=10)
        bpf.data = envelope(bpf.data)
        tmin, tmax = anch1c["tapmin"][i] * 10, anch1c["tapmax"][i] * 10
        for j in range(len(bpf.data)): bpf.data[j] = bpf.data[j] if tmin <= j <= tmax else 0
        bpf.stats.location = f"AV{tctr}"
        anch.append(bpf)
        
        bpfN = st[0 + acc].copy()
        bpfN.filter("bandpass", freqmin=f_lo, freqmax=f_hi, zerophase=True, corners=2)
        bpfN.data = envelope(bpfN.data)
        bpfN.stats.location = f"AV{tctr}"
        anchN.append(bpfN)

    # MIDT / SNR / RMS / MAXT SOLVER 8->32s
    for f4a, _ in enumerate(anch1c["flt4anch"]['band']):        
        if 8 <= anch1c["flt4anch"]['t_ctr'][f4a] <= 32:
            if anch1c['vmin'][f4a] == 99: anch1c['vmin'][f4a] = dist_km / anch1c['maxt'][f4a - 1]   
            if anch1c['vmax'][f4a] == 99: anch1c['vmax'][f4a] = dist_km / anch1c['maxt'][f4a - 1] + 0.5 * dist_km / anch1c['maxt'][f4a - 1] 

            SIGstart = int(np.round(dist_km / anch1c['vmax'][f4a] - anch1c['rmswin'][f4a] / 4))
            SIGstop = int(np.round(dist_km / anch1c['vmin'][f4a]))    
            if SIGstart < anch1c['rmswin'][f4a]: SIGstart = int(np.round(anch1c['rmswin'][f4a]))
            if SIGstop > 720 - anch1c["flt4anch"]['t_ctr'][f4a]: SIGstop = int(np.round(720 - anch1c["flt4anch"]['t_ctr'][f4a]))
            if SIGstop < SIGstart + anch1c['rmswin'][f4a]: SIGstop = int(np.round(SIGstart + anch1c['rmswin'][f4a]))           
            
            SIGsmp = np.linspace(SIGstart, SIGstop, num=(SIGstop - SIGstart + 1))
            RMSsigT, RMSsigA = 0, 0
            for smp in SIGsmp:
                rms = np.sqrt(np.mean(np.square(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)])))
                if rms > RMSsigA:
                    RMSsigA = rms
                    RMSsigT = smp
            if RMSsigT < 2 * anch1c['rmswin'][f4a]: RMSsigT = 2 * anch1c['rmswin'][f4a] 
            anch1c['midt'][f4a] = RMSsigT

            smp = anch1c['midt'][f4a]        
            RMSsigA = np.sqrt(np.mean(np.square(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)])))
            noisestart = 720 - anch1c["flt4anch"]['t_ctr'][f4a] - anch1c['rmswin'][f4a]
            noiseend = 720 - anch1c['rmswin'][f4a]
            RMSnoiseA = np.sqrt(np.mean(np.square(anchN[f4a].data[int((noisestart) * 10):int((noiseend) * 10)])))
            
            anch1c['snr'][f4a] = np.round(RMSsigA / RMSnoiseA, 1)
            anch1c['maxt'][f4a] = np.argmax(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)]) / 10 + int(smp - anch1c['rmswin'][f4a])
            
            # CLIP and ASSIGN Q
            Vanch = np.round(dist_km / anch1c['maxt'][f4a], 3)
            Tanch = anch1c["flt4anch"]['t_ctr'][f4a]
            
            if cc != "TT":  
                if Vanch < 1.8 or Vanch > 4.0:
                    Vanch = np.clip(Vanch, 1.8, 4.0)
                    anch1c['pickq'][f4a] = 0.5 
            else:  
                if Vanch < 2.0 or Vanch > 4.4:
                    Vanch = np.clip(Vanch, 2.0, 4.4)
                    anch1c['pickq'][f4a] = 0.5 

            if anch1c['snr'][f4a] < harmo_snrcut: 
                anch1c['pickq'][f4a] = 0              
            anch1c['pickv'][f4a] = Vanch   
            if 0.5 * Tanch * Vanch > dist_km and anch1c['pickq'][f4a] == 1: 
                anch1c['pickq'][f4a] = 0.9

    # 3-point microseis trend
    valid_v, valid_t, nvalid = [], [], 0  
    for p, period in enumerate(anch1c["flt4anch"]['t_ctr']):
        if 1 <= p <= 3: 
            valid_v.append(anch1c['pickv'][p]) 
            valid_t.append(period) 
            if anch1c['pickq'][p] == 1: nvalid += 1   

    coef = np.polyfit(np.array(valid_t), np.array(valid_v), deg=1)
    if coef[0] < 0: coef[0] = 0  
    
    if cc == "ZZ": 
        anch3C["nZ"], anch3C["coefZ"] = nvalid, coef        
    elif cc == "RR":
        anch3C["nR"], anch3C["coefR"] = nvalid, coef        
    elif cc == "TT":
        anch3C["nT"], anch3C["coefT"] = nvalid, coef        

    return anch3C

def harmo_trends_solve3c(anch3C, harmo_maxdiffZR=0.05, harmo_coefT=1.1, anchor_harmonisation=True, params=None):
    if params:
      anchor_harmonisation = params.get("anchor_harmonisation", anchor_harmonisation)
      harmo_maxdiffZR      = params.get("harmo_maxdiffzr", harmo_maxdiffZR)
      harmo_coefT          = params.get("harmo_coeft", harmo_coefT)
    """Evaluates 3C Rayleigh-Love trend consistency if anchor_harmonisation is True."""
    if not anchor_harmonisation:
        return anch3C # Skip execution if disabled

    xrange = [8, 16, 32]   
    yZ = np.clip(np.polyval(anch3C["coefZ"], xrange), 1.8, 4.0)   
    yR = np.clip(np.polyval(anch3C["coefR"], xrange), 1.8, 4.0)   
    yT = np.clip(np.polyval(anch3C["coefT"], xrange), 2.0, 4.4)   
  
    meanZR = (yZ + yR) / 2  
    diffZR = np.mean(abs(yZ - yR) / meanZR)
    better_val = yZ if anch3C["nZ"] >= anch3C["nR"] else yR
     
    if diffZR <= harmo_maxdiffZR:  
        if not (anch3C["nT"] > 0 and 1 < np.mean(yT / meanZR) < 1.25):
            yT = harmo_coefT * better_val
    else: 
        yZ = yR = better_val
        yT = harmo_coefT * better_val
  
    anch3C["coefZ"] = np.polyfit(xrange, yZ, deg=1)
    anch3C["coefR"] = np.polyfit(xrange, yR, deg=1)
    anch3C["coefT"] = np.polyfit(xrange, yT, deg=1)
    
    for k in ["coefZ", "coefR", "coefT"]:
        if anch3C[k][0] < 0: anch3C[k][0] = 0

    return anch3C

def harmo_anchors_search(st, dist_km, flt4anch, anch3C, cc, acc, harmo_snrcut=3.0, anchor_harmonisation=True, params=None):
    if params:
      anchor_harmonisation = params.get("anchor_harmonisation", anchor_harmonisation)
      harmo_snrcut         = params.get("harmo_snrcut", harmo_snrcut)

    """
    Pass 2: Searches discrete points across 4-128s.
    - If anchor_harmonisation=True: Tightens vmin/vmax around solved 3C microseis trend.
    - If anchor_harmonisation=False: Uses default 1C initial anch1c bounds.
    """
    anch1c = {
        "flt4anch": flt4anch,
        "rmswin": [4, 8, 14, 23, 37, 58],
        "vmin":   [1.0, 1.5, 1.5, 99, 99, 99],  
        "vmax":   [3.5, 3.5, 3.75, 99, 99, 99],
        "midt":   [0, 0, 0, 0, 0, 0],
        "snr":    [0, 0, 0, 0, 0, 0],
        "maxt":   [0, 0, 0, 0, 0, 0],
        "signal": [0, 0, 0, 0, 0, 0],
        "noise":  [0, 0, 0, 0, 0, 0],
        "pickv":  [0, 0, 0, 0, 0, 0],
        "pickq":  [1, 1, 1, 1, 1, 1],
        "tapmin": [],
        "tapmax": [],
    }    

    # Reset vmin/vmax tight around 3C trend ONLY if harmonisation is enabled
    if anchor_harmonisation and len(anch3C.get(f"coef{cc[0]}", [])) > 0:
        yrange = np.polyval(anch3C[f"coef{cc[0]}"], [4, 8, 16, 32]) 
        upper_bound = 1.01 if cc != "TT" else 0.99
        anch1c["vmin"] = [0.9 * yrange[0], 0.99 * yrange[1], 0.99 * yrange[2], 0.99 * yrange[3], 99, 99]
        anch1c["vmax"] = [1.0 * yrange[0], 1.01 * yrange[1], 1.01 * yrange[2], upper_bound * yrange[3], 99, 99]
         
    anch = read().clear(); anchN = read().clear()

    for i, _ in enumerate(anch1c["flt4anch"]["band"]):
        tctr = anch1c["flt4anch"]["t_ctr"][i]
        tmin = max(int(dist_km / 4.5 - tctr / 2), 10)
        tmax = min(int(dist_km / 1.5 + tctr / 2), 720)
        anch1c["tapmin"].append(tmin)
        anch1c["tapmax"].append(tmax)

    for i, _ in enumerate(anch1c["flt4anch"]["band"]):
        f_lo = anch1c["flt4anch"]["f_lo"][i]
        f_hi = anch1c["flt4anch"]["f_hi"][i]
        tctr = anch1c["flt4anch"]["t_ctr"][i]
        bpf = st[0 + acc].copy()
        bpf.taper(type="cosine", max_percentage=0.5, max_length=10)
        bpf.filter("bandpass", freqmin=f_lo, freqmax=f_hi, zerophase=True, corners=2)
        bpf.taper(type="cosine", max_percentage=0.5, max_length=10)
        bpf.data = envelope(bpf.data)
        tmin = anch1c["tapmin"][i] * 10; tmax = anch1c["tapmax"][i] * 10
        for j in range(len(bpf.data)): 
            bpf.data[j] = bpf.data[j] if tmin <= j <= tmax else 0
        bpf.stats.location = f"AV{tctr}"
        anch.append(bpf)

        bpfN = st[0 + acc].copy()
        bpfN.filter("bandpass", freqmin=f_lo, freqmax=f_hi, zerophase=True, corners=2)
        bpfN.data = envelope(bpfN.data)
        bpfN.stats.location = f"AV{tctr}"
        anchN.append(bpfN)

    # ANCHORSav START MIDT COMPUTATION 4->128s
    for f4a, _ in enumerate(anch1c["flt4anch"]['band']):        
        if anch1c['vmin'][f4a] == 99 or anch1c['vmin'][f4a] <= 0: 
            prev_maxt = anch1c['maxt'][f4a - 1] if f4a > 0 and anch1c['maxt'][f4a - 1] > 0 else 10.0
            anch1c['vmin'][f4a] = dist_km / prev_maxt
            
        if anch1c['vmax'][f4a] == 99 or anch1c['vmax'][f4a] <= 0:
            prev_maxt = anch1c['maxt'][f4a - 1] if f4a > 0 and anch1c['maxt'][f4a - 1] > 0 else 10.0
            anch1c['vmax'][f4a] = 1.1 * dist_km / prev_maxt
                 
        v_max_val = max(anch1c['vmax'][f4a], 0.1)
        v_min_val = max(anch1c['vmin'][f4a], 0.1)

        SIGstart = int(np.round(dist_km / v_max_val - anch1c['rmswin'][f4a] / 4))
        SIGstop = int(np.round(dist_km / v_min_val))

        # shift 4s window to slower vels 
        if anch1c["flt4anch"]['t_ctr'][f4a] == 4:
            SIGstart = int(np.round(dist_km / v_max_val))
            SIGstop = int(np.round(dist_km / v_min_val) + anch1c['rmswin'][f4a] / 4) 

        if SIGstart < anch1c['rmswin'][f4a]: 
            SIGstart = int(np.round(anch1c['rmswin'][f4a]))
        if SIGstop > 720 - anch1c["flt4anch"]['t_ctr'][f4a]: 
            SIGstop = int(np.round(720 - anch1c["flt4anch"]['t_ctr'][f4a]))
        if SIGstop < SIGstart + anch1c['rmswin'][f4a]: 
            SIGstop = int(np.round(SIGstart + anch1c['rmswin'][f4a]))           

        SIGsmp = np.linspace(SIGstart, SIGstop, num=(SIGstop - SIGstart + 1))
        RMSsigT = 0
        RMSsigA = 0
        for smp in SIGsmp:
            rms = np.sqrt(np.mean(np.square(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)])))
            if rms > RMSsigA:
                RMSsigA = rms
                RMSsigT = smp
        if RMSsigT < 2 * anch1c['rmswin'][f4a]:
            RMSsigT = 2 * anch1c['rmswin'][f4a]

        anch1c['midt'][f4a] = RMSsigT

        smp = anch1c['midt'][f4a]        
        RMSsigA = np.sqrt(np.mean(np.square(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)])))
        noisestart = 720 - anch1c["flt4anch"]['t_ctr'][f4a] - anch1c['rmswin'][f4a]
        noiseend = 720 - anch1c['rmswin'][f4a]
        RMSnoiseA = np.sqrt(np.mean(np.square(anchN[f4a].data[int((noisestart) * 10):int((noiseend) * 10)])))
        RMSratio = RMSsigA / RMSnoiseA if RMSnoiseA > 0 else 0
        MAXsigT = np.argmax(anch[f4a].data[int((smp - anch1c['rmswin'][f4a]) * 10):int((smp + anch1c['rmswin'][f4a]) * 10)]) / 10 + int(smp - anch1c['rmswin'][f4a])
        
        anch1c['snr'][f4a] = np.round(RMSratio, 1)
        anch1c['maxt'][f4a] = MAXsigT
        anch1c['signal'][f4a] = RMSsigA
        anch1c['noise'][f4a] = RMSnoiseA
            
        Vanch = np.round(dist_km / anch1c['maxt'][f4a], 3) if anch1c['maxt'][f4a] > 0 else 0
        Tanch = anch1c["flt4anch"]['t_ctr'][f4a]
        if cc != "TT": 
            if Vanch < 1.8:
                Vanch = 1.8
                anch1c['pickq'][f4a] = 0.5 
            if Vanch > 4.0:
                Vanch = 4.0
                anch1c['pickq'][f4a] = 0.5 
        else: 
            if Vanch < 2.0:
                Vanch = 2.0
                anch1c['pickq'][f4a] = 0.5 
            if Vanch > 4.4:
                Vanch = 4.4
                anch1c['pickq'][f4a] = 0.5 

        if anch1c['snr'][f4a] < harmo_snrcut:
            anch1c['pickq'][f4a] = 0              
        anch1c['pickv'][f4a] = Vanch   

        if 0.5 * Tanch * Vanch > dist_km and anch1c['pickq'][f4a] == 1:
            anch1c['pickq'][f4a] = 0.9

    if cc == "ZZ": 
        anch3C["rawZ"] = anch1c["pickv"]
        anch3C["snrZ"] = anch1c["snr"]         
        anch3C["qZ"] = anch1c["pickq"]         
    if cc == "RR":
        anch3C["rawR"] = anch1c["pickv"]
        anch3C["snrR"] = anch1c["snr"]         
        anch3C["qR"] = anch1c["pickq"]         
    if cc == "TT":
        anch3C["rawT"] = anch1c["pickv"]
        anch3C["snrT"] = anch1c["snr"]         
        anch3C["qT"] = anch1c["pickq"]         

    return anch3C, anch1c


def harmo_anchors_solve3c(anch3C, harmo_maxdiffZR=0.05, harmo_coefT=1.1, anchor_harmonisation=True, params=None):
    if params:
      anchor_harmonisation = params.get("anchor_harmonisation", anchor_harmonisation)
      harmo_maxdiffZR      = params.get("harmo_maxdiffzr", harmo_maxdiffZR)
      harmo_coefT          = params.get("harmo_coeft", harmo_coefT)
    """Solves 3C discrete anchor measurements."""
    if not anchor_harmonisation:
        # If bypassed, bypass validation directly to final fields
        anch3C["finZ"] = anch3C["rawZ"]
        anch3C["finR"] = anch3C["rawR"]
        anch3C["finT"] = anch3C["rawT"]
        return anch3C

    for ia, _ in enumerate(anch3C["rawZ"]):
        Z, R, T = anch3C["rawZ"][ia], anch3C["rawR"][ia], anch3C["rawT"][ia]
        Zs, Rs, Ts = anch3C["snrZ"][ia], anch3C["snrR"][ia], anch3C["snrT"][ia]
        Zq, Rq, Tq = anch3C["qZ"][ia], anch3C["qR"][ia], anch3C["qT"][ia]
         
        meanZR = (Z + R) / 2
        diffZR = abs(Z - R) / meanZR
  
        if Zq == 1 and Zs >= Rs: better_val = Z
        elif Zq != 1 and Rq != 1 and Zs >= Rs: better_val = Z
        else: better_val = R
  
        if diffZR <= harmo_maxdiffZR: 
            if Tq == 1 and meanZR < T < 1.25 * meanZR:
                anch3C["finZ"].append(Z); anch3C["finR"].append(R); anch3C["finT"].append(T)
            else:
                anch3C["finZ"].append(Z); anch3C["finR"].append(R); anch3C["finT"].append(harmo_coefT * better_val) 
        else:  
            if Tq == 1 and better_val < T < 1.25 * better_val:
                anch3C["finZ"].append(better_val); anch3C["finR"].append(better_val); anch3C["finT"].append(T)
            else:
                anch3C["finZ"].append(better_val); anch3C["finR"].append(better_val); anch3C["finT"].append(harmo_coefT * better_val)
                
    return anch3C

def harmo_anchors_apply(dist_km, anch3C, anch1c, cc):
    """Applies the solved 3C final anchors back to the 1C struct for continuity."""
    c = cc[0] # "Z", "R", or "T"
    clip_min = 2.0 if c == "T" else 1.8
    clip_max = 4.4 if c == "T" else 4.0
    
    anch1c["pickv"] = np.clip(anch3C[f"fin{c}"], clip_min, clip_max)
    anch1c["pickq"] = anch3C[f"q{c}"]
    anch1c["snr"] = anch3C[f"snr{c}"]
    
    # downgrade borrowed anchors
    for iq, _ in enumerate(anch1c["pickv"]):
        if anch3C[f"raw{c}"][iq] != anch3C[f"fin{c}"][iq]:
            anch1c["pickq"][iq] = 0.25
            
    # clip decreasing anchors
    prev_pick = 999
    for iq in range(len(anch1c['flt4anch']['t_ctr'])):
        if 3 * anch1c['flt4anch']['t_ctr'][iq] * anch1c['pickv'][iq] < dist_km:
            prev_pick = anch1c['pickv'][iq] 
        else:
            if anch1c['pickv'][iq] < prev_pick:
                anch1c['pickv'][iq] = prev_pick
            else:
                prev_pick = anch1c['pickv'][iq]
                
    return anch1c

# =====================
# crossvalidation 
# =====================

def dispersions_get_geometry(
    upair, lat1, lon1, alt1, lat2, lon2, alt2,
    latMc, lonMc, wgt, dist_km, azim, az, baz,
    CELL, ring, sec, bscore
):
    """
    Initializes and populates the station pair geometry into the dispersions dictionary.
    """
    dispersions = {
        'pair': [upair],
        'lat_lon_alt_1': [np.round(lat1, 3), np.round(lon1, 3), np.round(alt1, 1)],
        'lat_lon_alt_2': [np.round(lat2, 3), np.round(lon2, 3), np.round(alt2, 1)],
        'midlat_midlon_wgt': [np.round(latMc, 3), np.round(lonMc, 3), wgt],
        'dist_azim_az_baz': [dist_km, np.round(azim, 1), np.round(az, 1), np.round(baz, 1)],
        'binning': [CELL, ring, sec, np.round(bscore, 3)],
        
        # --- Initialize picking output lists ---
        'disp_id': [],
        'period': [],
        'group_v': [],
        'group_q': [],
        'group_snr': [],
        'group_amp': [],
        'group_fln': [],
        'phase_v': [],
        'phase_q': [],
        'phase_bzq': [],
        'phase_fln': [],
        'phase_ncyc26': []
    }
    return dispersions

def dispersions_get_picks(
    dispersions,
    cc,
    itr,
    ftan_pick=None,
    bzero_pick=None,
    n_cyclesFhi=None,
    n_cyclesFlo=None,
    spike26=None,
    group=True,
    phase=True
):
    """
    Ingests FTAN group picks and Bessel zero-crossing phase picks into the dispersions dictionary.
    Both group and phase processing are enabled by default (group=True, phase=True).
    """
    dist_km = dispersions['dist_azim_az_baz'][0]

    # --- Construct disp_id string ---
    if itr == 0:
        disp_id = f"{cc}_AV"
    elif itr == 1:
        disp_id = f"{cc}_AC"
    elif itr == 2:
        disp_id = f"{cc}_CA"
    else:
        disp_id = f"{cc}_i{itr}"

    # Only append period list once (during ZZ_AV component pass)
    if disp_id == "ZZ_AV" and ftan_pick is not None:
        dispersions['period'].append(ftan_pick['period'].tolist()[::-1])

    dispersions['disp_id'].append([disp_id])

    # --- INGEST GROUP VELOCITY PICKS ---
    if group:
        if ftan_pick is None:
            raise ValueError("ftan_pick dictionary must be provided when group=True.")

        GVlast = 0
        GVfirst = 999
        GVnval = 0

        # Quality check & 2x wavelength distance check
        for il, period in enumerate(ftan_pick['period']):
            if 2 * period * ftan_pick['pick_v'][il] >= dist_km:
                ftan_pick['pick_q'][il] = 0.1

            if ftan_pick['pick_q'][il] >= 0.75:
                if period > GVlast:
                    GVlast = period
                if period < GVfirst:
                    GVfirst = period
                if 8 <= period <= 32:
                    GVnval += 1  # Count valid picks in microseism range

        dispersions['group_v'].append(np.round(ftan_pick['poly_v'], 3).tolist()[::-1])
        dispersions['group_q'].append(ftan_pick['pick_q'].tolist()[::-1])
        dispersions['group_snr'].append(ftan_pick['pick_snr'].tolist()[::-1])
        dispersions['group_amp'].append(ftan_pick['pick_signal'].tolist()[::-1])
        dispersions['group_fln'].append([GVfirst, GVlast, GVnval])

    # --- INGEST PHASE VELOCITY PICKS ---
    if phase:
        if bzero_pick is None:
            raise ValueError("bzero_pick dictionary must be provided when phase=True.")

        PVlast = 0
        PVfirst = 999
        PVnval = 0

        for il, period in enumerate(bzero_pick['period']):
            # 1x wavelength distance filter
            if bzero_pick['pick_q'][il] == 1 and (1 * period * bzero_pick['pick_v'][il] < dist_km):
                if period > PVlast:
                    PVlast = period
                if period < PVfirst:
                    PVfirst = period
                if 8 <= period <= 32:
                    PVnval += 1  # Count valid picks in microseism range

        dispersions['phase_v'].append(np.round(bzero_pick['poly_v'], 3).tolist()[::-1])
        dispersions['phase_q'].append(bzero_pick['pick_q'].tolist()[::-1])
        dispersions['phase_bzq'].append(bzero_pick['bzq_posneg'].tolist()[::-1])
        dispersions['phase_fln'].append([PVfirst, PVlast, PVnval])
        dispersions['phase_ncyc26'].append([n_cyclesFhi, n_cyclesFlo, spike26])

    return dispersions

def harmo_picks_solve3c(
    dispersions,
    harmo_maxdiffZR=0.05,
    harmo_range_coefT=[0.9, 1.25],
    params=None,
):
    if params:
        harmo_maxdiffZR = params.get("harmo_maxdiffzr", harmo_maxdiffZR)
        harmo_range_coefT = params.get("harmo_range_coeft", harmo_range_coefT)
    """
    3C Velocity Consistency Evaluation (Strict Z-Trust Priority Strategy)
    ---------------------------------------------------------------------
    Evaluates 3C (Z, R, T) dispersion velocity consistency point-by-point.
    Updates quality scores in `group_q` and `phase_q` (downgrades failures to 0.05).

    STRICT HARMONISATION RULES:
    1. Z Quality Priority:
       - Z retains its initial validity (z_ok = Zq_valid) independently.
       - If Z fails initial quality (Zq_valid = False), all components fail.
       
    2. ZR Relative Difference Test (|Z - R| / meanZR <= 0.05):
       - If PASS (<= 5%):
           * Evaluates T against meanZR (0.9 * meanZR <= T <= 1.25 * meanZR).
           * If T PASSES -> All three pass (z_ok=True, r_ok=True, t_ok=True).
           * If T FAILS  -> Z stays valid, R & T are invalidated (r_ok=False, t_ok=False).
       - If FAIL (> 5%):
           * Z stays valid, R & T are both invalidated immediately (r_ok=False, t_ok=False).

    3. Missing Components:
       - If R or T is missing/invalid, Z stays valid while R/T are marked invalid.
    """
    idx_map = {'Z': (0, 1, 2), 'R': (3, 4, 5), 'T': (6, 7, 8)}
    n_pts = len(dispersions['period'][0])
    t_min_factor, t_max_factor = harmo_range_coefT

    for pick_type in ['group', 'phase']:
        v_key = f"{pick_type}_v"
        q_key = f"{pick_type}_q"
        q_thresh = 0.75 if pick_type == 'group' else 1.0

        z_av_v, z_av_q = dispersions[v_key][0], dispersions[q_key][0]
        r_av_v, r_av_q = dispersions[v_key][3], dispersions[q_key][3]
        t_av_v, t_av_q = dispersions[v_key][6], dispersions[q_key][6]

        for k in range(n_pts):
            Z, R, T = z_av_v[k], r_av_v[k], t_av_v[k]

            Zq_valid = (z_av_q[k] >= q_thresh) and not np.isnan(Z)
            Rq_valid = (r_av_q[k] >= q_thresh) and not np.isnan(R)
            Tq_valid = (t_av_q[k] >= q_thresh) and not np.isnan(T)

            # Z always retains its own validity status
            z_ok = Zq_valid
            r_ok = False
            t_ok = False

            if Zq_valid:
                if Rq_valid:
                    meanZR = (Z + R) / 2.0
                    diffZR = abs(Z - R) / meanZR

                    # Check relative difference boundary
                    if diffZR <= harmo_maxdiffZR:
                        if Tq_valid:
                            # Evaluate T against meanZR
                            t_passes = (t_min_factor * meanZR <= T <= t_max_factor * meanZR)
                            if t_passes:
                                # All three pass
                                r_ok = True
                                t_ok = True
                            else:
                                # T fails -> invalidate BOTH R & T
                                r_ok = False
                                t_ok = False
                        else:
                            # T is invalid/missing -> keep R valid against Z
                            r_ok = True
                            t_ok = False
                    else:
                        # diffZR > threshold -> Invalidate BOTH R & T
                        r_ok = False
                        t_ok = False
                else:
                    # R is invalid/missing -> T cannot be validated alone without R
                    r_ok = False
                    t_ok = False

            # --- Downgrade Failed Components (q -> 0.05) ---
            valid_flags = {'Z': z_ok, 'R': r_ok, 'T': t_ok}

            for comp in ['Z', 'R', 'T']:
                av_idx, ac_idx, ca_idx = idx_map[comp]
                if not valid_flags[comp]:
                    dispersions[q_key][av_idx][k] = 0.05
                    dispersions[q_key][ac_idx][k] = 0.05
                    dispersions[q_key][ca_idx][k] = 0.05

    return dispersions
    
def dispersions_crossvalidation(dispersions):
    """
    Complete Crossvalidation:
    1. Initial quality evaluation (q >= 0.75 for group, q >= 1.0 for phase).
    2. Applies 5-point sliding window support on Group -> Phase.
    3. Evaluates 3-component classification (cZ, cR, cT) and assigns tag.
    4. Translates tag into final component flags:
       - If tag is 'rt0' (e.g. z1rt0, z2rt0), both R and T are invalidated (q=0.01, mask=False).
       - If tag is 'z0' (z0rt0 / failed), all components including Z are invalidated (q=0.01, mask=False).
    5. Syncs group_mask/phase_mask and recalculates fln bounds.
    """
    disp_id = dispersions['disp_id']
    periods = dispersions['period'][0]
    group_q = dispersions['group_q']
    phase_q = dispersions['phase_q']
    group_v = dispersions['group_v']
    phase_v = dispersions['phase_v']
    n_pts = len(periods)
    n_rows = len(disp_id)

    # Initial Masks based on existing q (which includes 0.05 from harmo_picks)
    group_mask = [[(group_q[i][t] >= 0.75 and not np.isnan(group_v[i][t])) for t in range(n_pts)] for i in range(n_rows)]
    phase_mask = [[(phase_q[i][t] >= 1.0 and not np.isnan(phase_v[i][t])) for t in range(n_pts)] for i in range(n_rows)]

    # --- STEP 1: SLIDING WINDOW GROUP SUPPORT FOR PHASE ---
    countgrp = []
    countpha = []

    for i in range(n_rows):
        countg = 0
        countp = 0

        for t, valt in enumerate(periods):
            # Check 5-point sliding window for group support
            start_idx = max(0, t - 2)
            end_idx = min(n_pts, t + 3)
            slideGR = sum(1 for k in range(start_idx, end_idx) if group_mask[i][k])

            # Invalidate phase if no group support exists -> set q to 0.01
            if slideGR == 0:
                phase_mask[i][t] = False
                phase_q[i][t] = 0.01

            if 4 <= valt <= 32:
                if group_mask[i][t]:
                    countg += 1
                if phase_mask[i][t]:
                    countp += 1

        countgrp.append(countg)
        countpha.append(countp)

    # --- STEP 2: COMPONENT CONSISTENCY CLASSIFICATION & TAG ASSIGNMENT ---
    cZ = 0 if countgrp[0] < 3 else (2 if countgrp[0] >= 3 and countgrp[1] >= 3 and countgrp[2] >= 3 else 1)
    cR = 0 if (cZ == 0 or countgrp[3] < 3) else (2 if countgrp[3] >= 3 and countgrp[4] >= 3 and countgrp[5] >= 3 else 1)
    cT = 0 if (cZ == 0 or countgrp[6] < 3) else (2 if countgrp[6] >= 3 and countgrp[7] >= 3 and countgrp[8] >= 3 else 1)

    if cZ == 0:
        tag = 'z0rt0'
    elif cZ == 1:
        tag = 'z1rt0' if (cR == 0 or cT == 0) else ('z1rt2' if (cR == 2 and cT == 2) else 'z1rt1')
    elif cZ == 2:
        tag = 'z2rt0' if (cR == 0 or cT == 0) else ('z2rt2' if (cR == 2 and cT == 2) else 'z2rt1')
    else:
        tag = 'failed'

    dispersions['crossvalidation_tag'] = [str(tag)]

    # --- STEP 3: TAG TO MASK & Q-FLAG TRANSLATION ---
    comp_validity = {'Z': True, 'R': True, 'T': True}

    if tag in ['z0rt0', 'failed']:
        comp_validity['Z'] = False
        comp_validity['R'] = False
        comp_validity['T'] = False
    elif tag in ['z1rt0', 'z2rt0']:
        comp_validity['R'] = False
        comp_validity['T'] = False
    else:
        comp_validity['Z'] = (cZ > 0)
        comp_validity['R'] = (cR > 0)
        comp_validity['T'] = (cT > 0)

    idx_ranges = {'Z': range(0, 3), 'R': range(3, 6), 'T': range(6, 9)}

    for comp, is_valid in comp_validity.items():
        if not is_valid:
            for i in idx_ranges[comp]:
                for t in range(n_pts):
                    group_q[i][t] = 0.01
                    phase_q[i][t] = 0.01
                    group_mask[i][t] = False
                    phase_mask[i][t] = False

    # Sync group_mask and phase_mask with final q-values (> 0.05 ensures neither 0.05 nor 0.01 pass)
    for i in range(n_rows):
        for t in range(n_pts):
            if group_q[i][t] <= 0.05:
                group_mask[i][t] = False
            if phase_q[i][t] <= 0.05:
                phase_mask[i][t] = False

    dispersions['group_mask'] = group_mask
    dispersions['phase_mask'] = phase_mask

    # --- STEP 4: RECALCULATE MASKED BOUNDS ---
    group_fln_masked = []
    phase_fln_masked = []

    for i in range(n_rows):
        valid_g = [periods[k] for k in range(n_pts) if group_mask[i][k]]
        if valid_g:
            group_fln_masked.append([min(valid_g), max(valid_g), sum(1 for p in valid_g if 8 <= p <= 32)])
        else:
            group_fln_masked.append([999, 0, 0])

        valid_p = [periods[k] for k in range(n_pts) if phase_mask[i][k]]
        if valid_p:
            phase_fln_masked.append([min(valid_p), max(valid_p), sum(1 for p in valid_p if 8 <= p <= 32)])
        else:
            phase_fln_masked.append([999, 0, 0])

    dispersions['group_fln_masked'] = group_fln_masked
    dispersions['phase_fln_masked'] = phase_fln_masked

    return dispersions

