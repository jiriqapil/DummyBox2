#!/usr/bin/env python
# coding: utf-8

# In[ ]:
module="DummyBox2"

import sys, pathlib

# Register helpers folder relative to notebook path
PROJECT_ROOT = pathlib.Path.cwd()
helpers_path = str(PROJECT_ROOT / "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

# Load all shared libraries into global namespace
from imports import *

# Load processing defs & setup parameters
from defs4process import *
# import remaining pipeline functions
from defs4group import *
from defs4phase import *
from defs4harmo import *
from defs4plot import *
from defs4write import *

# Display environment & package versions
## print redirected to file
#show_env()  

# Display parameter configuration
P = setup_params() # Loads Python defaults & overrides via params/config.env
## print redirected to file
#show_params(P)
# Alias configuration dictionary
cfg = P

# 5. Save exact printout to timestamped log file
if not os.path.exists(cfg["output_dir"] + '/LOG'): os.makedirs(cfg["output_dir"] + '/LOG')
write_config_log(show_env, show_params, P)    

# =====================================================================
# Extract Configurations and Paths from Parameters (cfg / P)
# =====================================================================
inp_dir = cfg["input_dir"]
out_dir = cfg["output_dir"]
etopo_nc = cfg["etopo_nc"]
qgis_dir = cfg.get("qgis_dir") # optional parameter for map_style="Private"
stations_path = cfg["stations_path"]
mseed_path = cfg["mseed_path"]
task_list = cfg["task_list"]

# Display & Rendering Toggles
map_style = cfg["map_style"]
use_qgis = cfg.get("use_qgis", False)  # optional parameter for map_style="Private"
image_quality = cfg["image_quality"]
show_figure = cfg["show_figure"]
dpi = 300 if image_quality.lower() == "publish" else 96

# =====================================================================
# Processing Initialization, thresholds, anchor/FTAN filters,
# =====================================================================
maxlag, snrcut, flt4anch, flt4ftan, Xi, Yi, Xii, Yii = processing_init(cfg)

# =====================================================================
# Canvas Initialization & Base Map Setup, Canvas & Color Palettes
# =====================================================================
figf, axes, clr_group, clr_phase, cividis_dim = plot_master_init()

# Initialize Base Map via Router
fig_map, ax_map, my_map = plot_map_init(
    map_style=map_style,
    etopo_nc=etopo_nc,
    stations=stations_path,
    qgis_dir=qgis_dir,
    use_qgis=use_qgis,
)

# =====================================================================
# Aggregation Buckets Initialization
# =====================================================================
tag_dicts = {
    "3C": write_init_tag_dict(),
    "1C": write_init_tag_dict(),
    "0C": write_init_tag_dict(),
}

### ========================== LOOP TRACES ZRT-FW,RV ==========================
### ========================== GEOMETRY UPDATE ==========================

# --- Step 2: Loop over symbol datasets and save figures ---
## REMOVE ALL Step 2 elements ###

########## NOW cycle stations pairs
# list=OUTDIR+'/8_FTANBES0_CAT19.pylist'
# fo = open(list, "x")
# fo.write('counter,pair,status\n')
# fo.close()

### ============ BATCH HEADER ===========
ZONE='INS'

if not os.path.exists(cfg["output_dir"] + '/NPY'): os.makedirs(cfg["output_dir"] + '/NPY')
if not os.path.exists(cfg["output_dir"] + '/PNG'): os.makedirs(cfg["output_dir"] + '/PNG')
if not os.path.exists(cfg["output_dir"] + '/CSV/Dataset_1C'): os.makedirs(cfg["output_dir"] + '/CSV/Dataset_1C')
if not os.path.exists(cfg["output_dir"] + '/CSV/Dataset_3C'): os.makedirs(cfg["output_dir"] + '/CSV/Dataset_3C')

# flip fw/rv for change pair order
if ZONE=="CPY":rotcode="flipcpy"
elif ZONE=="QST":rotcode="flipqst"
elif ZONE=="RNM":rotcode="fliprnm"
elif ZONE=="RST":rotcode="fliprst"
elif ZONE=="CRS":rotcode="flipcrs"


### ========================== TASK EXECUTION LOOP ==========================

with open(cfg["task_list"], 'r') as f: 
 reader = csv.reader(f)
 for r, row in enumerate(reader):
  if not row:
    continue

  # Parse CSV row columns: id, pair, stack, use
  task_id = row[0].strip()
  inpair = row[1].strip()
  wgtmin = row[2].strip()
  status = row[3].strip()  # Supports 'Yes', 'Y', 'yes', 'y', etc.

  # Execute only active tasks in the chunk (accepts 'yes' or 'y')
  if status.lower() in ("yes", "y"):
   try:
     net1 = inpair.split(sep="_")[0].split(sep=".")[0]
     sta1 = inpair.split(sep="_")[0].split(sep=".")[1]
     net2 = inpair.split(sep="_")[1].split(sep=".")[0]
     sta2 = inpair.split(sep="_")[1].split(sep=".")[1]
     pair = f"{net1}_{sta1}_{net2}_{sta2}"
     # Optional: pass wgtmin if available
     wgtmin_val = wgtmin if wgtmin else None

### update station pair geometry from table containing station coordinates
     (
        wgt, lon1, lat1, alt1, lon2, lat2, alt2,
        dist, az, baz, dist_km, azim, lonMl, latMl, lonMc, latMc, Mdif
     ) = pair_geometry(
        net1=net1, sta1=sta1, net2=net2, sta2=sta2,
        stations_csv=stations_path, wgtmin=wgtmin
     )      

  ### ========================== END GEOMETRY UPDATE ==========================
  
  ## RESET NETWORK CODE XX for FDSN unassigned BOHEMA I-IV and EGER-RIFT operated by GFU
     BOH12=['B02','B09','B10','B18','B19','B20','B21','B22','B23',\
                       'BM11','BM12','BM13','BM14','BM15',\
                       'DIV','DOL','HOM','JAV','KHB','KUN','LAC2','LIP','LNS','SVO','VLD']
     BOH34=['BLA','BUD','CER','DUN','GFO','JAK','KON','KYS','LAN','MIL','MUN','PNS',\
                        'ROC','SLA','UHR','UNT','VAL','ZVI','BCH','BTV','CLH','G1107','JES',\
                        'KRN','KUKS','LOS','NOH','OPOC','ZKO']
     ER=['BIT','CEJ','JPJ','MOS','NEMA','UST','VLC','ALTD','FALK','MUGL','WARM']
     if net1=='ZV' and sta1 in BOH12: net1='XX'
     if net2=='ZV' and sta2 in BOH12: net2='XX'
     if net1=='ZV' and sta1 in BOH34: net1='XX'
     if net2=='ZV' and sta2 in BOH34: net2='XX'
     if net1=='7E' and sta1 in ER: net1='XX'
     if net2=='7E' and sta2 in ER: net2='XX'
     upair=net1+"_"+sta1+"_"+net2+"_"+sta2
     outpair=net1+"."+sta1+"_"+net2+"."+sta2
  
  ##=============GEOMETRY BINNING
     (
        ring, dctr, sec, actr, rdif, adif, LAT, LON, CELL, cdif_km, bscore
     ) = pair_binning(dist_km, azim, latMc, lonMc)

  ### ============= ATTRIBUTES to OUT_NPY ===============
     dispersions = dispersions_get_geometry(
    upair, lat1, lon1, alt1, lat2, lon2, alt2,
    latMc, lonMc, wgt, dist_km, azim, az, baz,
    CELL, ring, sec, bscore
    )

### ========================== BASEMAP - STATIONS Pair Iteration Loop ==========================
    # Overlay Station Pair onto Map
     map_handles = plot_map_main(
        map_style=map_style,
        fig_map=fig_map,
        ax_map=ax_map,
        my_map=my_map,
        lon1=lon1,
        lat1=lat1,
        lon2=lon2,
        lat2=lat2,
        net1=net1,
        sta1=sta1,
        net2=net2,
        sta2=sta2,
        dist_km=dist_km,
        azim=azim,
        wgt=wgt,
     )

    # Embed Map Frame into Subplot Grid (r1c1) and Remove Overlays
     plot_map_embed(
        fig_map=fig_map,
        ax_map=ax_map,
        axes_dict=axes,
        handles=map_handles,
     )

  ### ========================== END BASEMAP - STATIONS ==========================
  # read trace split in half, flip and stack both sides
     for pathseed in glob.glob(cfg["mseed_path"] + '/' + inpair + '.mseed'):        
    # =================================================================================        
    # EXPECTED INPUT (9 TRACES in STREEM):
    # -------------------------
    # Index 0 : ZZ AV (Vertical Rayleigh Average (Causal, Acausal))
    # Index 1 : ZZ AC (Acausal)
    # Index 2 : ZZ CA (Causal)
    # Index 3 : RR AV (Radia Rayleigh Average (Causal, Acausal))
    # Index 4 : RR AC (Acausal)
    # Index 5 : RR CA (Causal)
    # Index 6 : TT AV (Transverse Love Average (Causal, Acausal))
    # Index 7 : TT AC (Acausal)
    # Index 8 : TT CA (Causal)
    # =====================================================================
      st = read(pathseed)

    # =================================================================================        
    # ===================== START ANCHRORSav - 3C SOLVER Z-R-T###
    # =====================================================================
    # Initialize dictionary
     anch3C = anchor_init()

    # --- PASS 1: MICROSEISMIC TREND (8-32s) ---
     if cfg.get("anchor_harmonisation", True):
        for icc, cc in enumerate(["ZZ", "RR", "TT"]):
            acc = icc * 3  # component index mapping
            anch3C = harmo_trends_search(st, dist_km, flt4anch, anch3C, cc, acc, params=cfg)
    
        anch3C = harmo_trends_solve3c(anch3C, params=cfg)
    
    # --- PASS 2: DISCRETE ANCHORS (4-128s) ---
     anch1c_dict = {}
    
     for icc, cc in enumerate(["ZZ", "RR", "TT"]):
        acc = icc * 3  # component index mapping
        anch3C, anch1c = harmo_anchors_search(st, dist_km, flt4anch, anch3C, cc, acc, params=cfg)
        anch1c_dict[cc] = anch1c
    
     anch3C = harmo_anchors_solve3c(anch3C, params=cfg)
    
    # --- CONTINUATION: APPLY HARMONISATION & PROCESS TRACES ---
     graph_atten_ymax = 3e-5
     graph_atten_store = []
    
     for icc, cc in enumerate(["ZZ", "RR", "TT"]):
       acc = icc * 3  # component index mapping
        
        # Update local anch1c with 3C-solved values and clip decreasing anchors
       anchors = harmo_anchors_apply(dist_km, anch3C, anch1c_dict[cc], cc)        
### ====================== END ANCHRORSav - 3C SOLVER Z-R-T###
    
        # Initialize clean canvas
       fig_tv, ax_tv = plot_diagram_init(cc)  # Initialize the clean, isolated canvas using the new name
       ax_tv.set_title(f"Dispersion measurements ({cc})") # Add the component-specific title
       ax3 = ax_tv  # Map 'ax3' locally to 'ax_tv' so your existing sub-functions write directly to it

### !!! ======= END FTAN prep ===========  
             
### !!! ========== prepare ATTENUATION graph here ========== !!!
       fig_attenuation, ax_attenuation = plot_attenuation_init(cc) 
### !!! ======= END ATTEN GRAPHS prep ===========       

### !!! ========== prepare QCGRAPHS here ========== !!!
       fig_qc, ax_qc, ax_qc_r = plot_qcgraphs_init(cc)
        # Establish base tracking limits
       running_snr_max = 40
       running_bzq_max = 100           
### !!! ======= END QCGRAPHS prep ===========       

### !!! ========== prepare SPECTRA here ========== !!!
       fig_spec, ax_spec, clr_trace, clr_trfill, itr_label = plot_spec_init(cc)
       ax5 = ax_spec  # Map 'ax5' locally to 'ax_spec' so your existing sub-functions write directly to it

### !!! ======= END SPECTRA prep ===========       
       
### !!! ========== prepare TRACE plot wiggles here ========== !!!
       fig_trace, ax_trace, clr_trace, clr_trfill, itr_label = plot_trace_init(cc)
### !!! ======= END TRACE plot prep ===========   
       
### =========== START GROUP AND PHASE SOLVERS         
         
# Extract trace stack for current component
       proc_st = st.copy().clear()
       proc_st.append(st[0 + acc])
       proc_st.append(st[1 + acc])
       proc_st.append(st[2 + acc])         
     
       for itr, tr in enumerate(proc_st):
         vmin = cfg.get("vmin_grid", 1.0)
         vmax = cfg.get("vmax_grid", 8.0)
         tmin = int(np.round(dist_km / vmax))
         tmax = int(np.round(dist_km / vmin))
 
         Zii = np.zeros_like(Xii)  

    # --- Initialize filtered ObsPy Stream ---
         bpf_stream = Stream()
           
         for f4f, val in enumerate(flt4ftan["t_ctr"]):
            if 2 <= flt4ftan["t_ctr"][f4f] <= 250:
                env_dnorm, bpf_tr = group_multifilter_apply(
                    tr,
                    flt4ftan,
                    f4f,
                    dist_km,
                    maxlag,
                    Yi,
                    vmin=vmin,
                    vmax=vmax,
                    cc=cc,
                    params=cfg,
                )
                Zii.T[f4f] = env_dnorm
                bpf_stream.append(bpf_tr)
            else:
                # Add a dummy zeroed trace to preserve exact index alignment with flt4ftan['t_ctr']
                dummy_tr = tr.copy()
                dummy_tr.data.fill(0.0)
                bpf_stream.append(dummy_tr)    
      
        # --- FTAN GRID INTERPOLATION (PREPARATION FOR GROUP/PHASE PICKING) ---
         Xpp, Ypp, Zpp = group_search_grid(Xii, Yii, Zii, x_new=np.linspace(1, 200, 797), y_new=Yi)   
                  
  #### =================================================================================        
  #### ===================== START GROUP PICKER - FTAN
  #### =================================================================================        
         # Initializes fresh ftan_pick dict + parameters for THIS trace
         coefT, ftan_pick, ref_v, anchor_tuple_down, anchor_tuple_up = group_search_prep(
            cc, anchors, params=cfg
         )           
         
         ZiiPICK = Zii.copy()
         
         # Downwards search (short periods)

        # Downwards & Upwards Search
         ftan_pick = group_search_downwards(
            ZiiPICK, Xi, Yi, dist_km, coefT, ftan_pick, ref_v, anchor_tuple_down, cc=cc, params=cfg
         )
        
         ref_v16 = anchors['pickv'][2]  # Reset anchor reference before upwards search ---
           # Upwards search (long periods)
         ftan_pick = group_search_upwards(
            ZiiPICK, Xi, Yi, dist_km, coefT, ftan_pick, ref_v16, anchor_tuple_up, cc=cc, params=cfg
         )

        # Group Refine  (Handles Instantaneous computation, Slope, Infill, Outliers, and SNR internally)
         ftan_pick, yin_filled = group_refine(
            ftan_pick,
            flt4ftan,
            bpf_stream,
            anchors,
            dist_km,
            coefT=coefT,
            cc=cc,
            eval_slope=True,
            eval_snr=True,
            eval_outliers=True,
            params=cfg,
         )

  #### =================================================================================        
  #### ===================== START PHASE PICKER - BESSEL ZERO CROSSING
  #### =================================================================================        
        # Setup & Spectral Pre-processing

         bzero_pick = phase_search_prep(
            ftan_pick, dist_km, coefT=coefT, cc=cc, params=cfg
         )
         realspec, freq = phase_get_spectra(tr)
           
        # Refine spectrum using boolean feature controls
         spec_detrend, spec_metrics = phase_spectrum_refine(
            realspec, freq, despike26=True, smooth=True, detrend=True
         )
        # Unpack metrics
         n_cyclesFhi = spec_metrics["n_cyclesFhi"]
         n_cyclesFlo = spec_metrics["n_cyclesFlo"]
         spike26 = spec_metrics["spike26"]

        # Search Zero-Crossings
         crossings_tuple = phase_search_zeros(
            spec_detrend, freq, dist_km, cc=cc
         )
         if itr == 0:
            crossings_data2plot = phase_crossings4plot_updown(
                crossings_tuple, 
                bzero_pick, 
                dist_km, 
                cc=cc,
                params=cfg)
         else:
            crossings_data2plot = None

        # Refine Phase Velocity Picks
         bzero_pick = phase_refine(
            bzero_pick,
            crossings_tuple,
            dist_km,
            eval_updown=True,
            apply_reposition=True,
            eval_outliers=True,
         )    
           
  #### =================================================================================        
  #### ===================== COLLECT DISPERSIONS, PLOT AND CROSSVALIDATE
  #### =================================================================================        
             
         dispersions = dispersions_get_picks(
            dispersions,
            cc=cc,
            itr=itr,
            ftan_pick=ftan_pick,
            bzero_pick=bzero_pick,
            n_cyclesFhi=n_cyclesFhi,
            n_cyclesFlo=n_cyclesFlo,
            spike26=spike26,
            group=True,
            phase=True
         ) 
    # Deepcopy bzero_pick before sending to phase metrics/plotting
         current_phase_pick = copy.deepcopy(bzero_pick)

        # Extract 1C GV / PV bounds for the CURRENT iteration (most recent index: -1)
         GVfirst, GVlast, GVnval = dispersions['group_fln'][-1]
         PVfirst, PVlast, PVnval = dispersions['phase_fln'][-1]
         
         current_group_metrics = {
            'ftan_pick': ftan_pick,
            'GVfirst': GVfirst,
            'GVlast': GVlast,
            'GVnval': GVnval,
            'yin_filled': yin_filled
         }
                
         current_phase_metrics = {
            'bzero_pick': bzero_pick,
            'PVfirst': PVfirst,
            'PVlast': PVlast,
            'PVnval': PVnval,
         }        
           
   # Render onto active canvas
         plot_diagram_main(
            ax=ax_tv,
            itr=itr,
            dist_km=dist_km,
            Xii=Xii, Yii=Yii,
            Xpp=Xpp, Ypp=Ypp,
            anchors=anchors,
            Zii=Zii,
            plot_background=(itr == 0),
            group_data=current_group_metrics,
            phase_data=current_phase_metrics,
            crossings_data2plot=crossings_data2plot,
            clr_group=clr_group,
            clr_phase=clr_phase  
         )   

          
         graph_atten_ymax = plot_attenuation_main(
            ax4=ax_attenuation,
            itr=itr,
            clr_group=clr_group,
            ftan_pick=ftan_pick, 
            dist_km=dist_km,
            GVnval=GVnval,
            ax4_ccALPHAMAX=graph_atten_ymax,
         )

    # Plot the reliability graphs and track bounding maximums
         running_snr_max, running_bzq_max = plot_qcgraphs_main(
                ax6=ax_qc, 
                ax6_r=ax_qc_r, 
                itr=itr, 
                clr_group=clr_group, 
                clr_phase=clr_phase, 
                ftan_pick=ftan_pick, 
                bzero_pick=bzero_pick, 
                GVnval=GVnval, 
                PVnval=PVnval,
                ax6_ccSNRmax=running_snr_max,
                ax6_ccBZQmax=running_bzq_max
            )

         plot_spec_main(
            ax5=ax_spec, 
            itr=itr,
            freq=freq, 
            spec_detrend=spec_detrend, 
            clr_trace=clr_trace, 
            clr_trfill=clr_trfill, 
            itr_label=itr_label
            )  

         plot_trace_main(
            ax2=ax_trace,
            itr=itr,
            acc=acc, 
            st=st,
            dist_km=dist_km,
            clr_trace=clr_trace,
            clr_trfill=clr_trfill,
            itr_label=itr_label,
                            )      

    # Embed diagrams into Row 3           
       plot_diagram_embed(fig_tv, ax_tv, cc, axes) # Save, Embed, Style and Clear memory ---
     
    # Store figures tbefore embed with global yrange
       graph_atten_store.append((fig_attenuation, ax_attenuation, cc))     
           
    # Embed QC Graphs into Row 6
       plot_qcgraphs_embed(
                fig=fig_qc, 
                ax6=ax_qc, 
                ax6_r=ax_qc_r, 
                cc=cc, 
                axes_dict=axes, 
                clr_group=clr_group, 
                clr_phase=clr_phase, 
                ax6_ccSNRmax=running_snr_max, 
                ax6_ccBZQmax=running_bzq_max
            )
           
    # Embed Spec into Row 5
       plot_spec_embed(figspec=fig_spec, ax5=ax_spec, cc=cc, axes_dict=axes)    

    # Embed Trace wiggles into Row 2
       plot_trace_embed(
             fig_trace=fig_trace,
             ax2=ax_trace,
             cc=cc,
             dist_km=dist_km,
             axes_dict=axes,
                            )
# Re-engage interactive loop after component calculations complete

    # Embed Attenuation Graph into Row 4
     for fig_attenuation, ax_attenuation, cc in graph_atten_store:
        plot_attenuation_embed(
            fig=fig_attenuation,
            ax4=ax_attenuation,
            cc=cc,
            axes_dict=axes,
            clr_group=clr_group,
            ax4_ccALPHAMAX=graph_atten_ymax,
        )         

     # Process dispersion harmonisation and crossvalidation based on cfg parameters
     if cfg.get("crossvalidation", True):
        dispersions = harmo_picks_solve3c(dispersions, params=cfg)
    
     dispersions = dispersions_crossvalidation(dispersions)         
         
       # Initialize figure and axes for final plot (r1c2)
     fig1, ax1 = plt.subplots(figsize=(8, 8))

# Draw everything onto ax1
# Draw dispersion curves directly from the finalized dictionary
     plot_crossvalidation_main(ax1=ax1, dispersions=dispersions)
      
# Embed straight into master layout panel (axes_dict['r1c2'])
     plot_crossvalidation_embed(fig1=fig1, ax_r1c2=axes['r1c2']) 
     
     title_str = f"{module}: multifilter_type={cfg['multifilter_type']}, harmonisation={cfg['anchor_harmonisation']}, cross-validation={cfg['crossvalidation']}"
     ytitle=0.89
     if cfg['map_style']=="Private": ytitle=0.88
     figf.suptitle(title_str, fontsize=14, fontweight="bold",y=ytitle)      
# Wrap up and render to PIL
     imgout, imgf, buff = plot_pillow_wrapup(figf, image_quality=image_quality)

# Construct path string
     if dispersions['crossvalidation_tag'][0].upper() in ['Z1RT1','Z1RT2','Z2RT1','Z2RT2']:
         tag="3C"
     elif dispersions['crossvalidation_tag'][0].upper() in ['Z1RT0','Z2RT0']:
         tag="1C"
     else:
         tag="0C"   
     #tag=str(dispersions['crossvalidation_tag'][0].upper())
      
     output_png = f"{cfg['output_dir']}/PNG/{outpair}_{image_quality[:4]}.png"      
     imgout.save(output_png, optimize=True)

# Clean up buffer & image RAM
     plot_pillow_cleanup(imgout, imgf, buff)

# Display on screen & close figure
     if show_figure:
        display(figf)      

     plt.close(figf)

# Aggregate current dispersion dictionary
     write_dict_aggregate(dispersions, tag_dicts)
      
# --- CLEAR MEMORY HERE ---
     gc.collect() # Force immediate garbage collection

     print('[TASK_RESULT] ' + str(task_id)+','+outpair+',Dataset_'+str(tag))

   except Exception:
     print('[TASK_RESULT] ' + str(task_id)+','+outpair+',Error')
     continue
# Unpack aggregated dictionaries after the loop completes
dispersions_3C = tag_dicts["3C"]
dispersions_1C = tag_dicts["1C"]
dispersions_0C = tag_dicts["0C"]

# Save aggregated dictionaries
np.save(f"{cfg['output_dir']}/NPY/dispersions_3C.npy", dispersions_3C)
np.save(f"{cfg['output_dir']}/NPY/dispersions_1C.npy", dispersions_1C)
np.save(f"{cfg['output_dir']}/NPY/dispersions_0C.npy", dispersions_0C)

# Write CSV files for each dataset folder
write_dataset_csvs(dispersions_3C, f"{cfg['output_dir']}/CSV/Dataset_3C")
write_dataset_csvs(dispersions_1C, f"{cfg['output_dir']}/CSV/Dataset_1C")
