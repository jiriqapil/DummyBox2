#  ==== defs4plot.py =====
from imports import *
from defs4group import *

###==== BUILD MASTER CANVAS

def plot_master_init():
    """INITIALIZE MASTER CANVAS: Sets global figure canvas, GridSpec layout,

    and color definitions across all panels.
    """
    plt.style.use("default")

    figf = plt.figure(figsize=(18, 27))
    gs = GridSpec(27, 18, figure=figf, hspace=0.05, wspace=0.05)

    axes_dict = {
        "r1c1": figf.add_subplot(gs[0:9, 0:10]),
        "r1c2": figf.add_subplot(gs[0:9, 10:18]),
        "r2c1": figf.add_subplot(gs[9:12, 0:6]),
        "r2c2": figf.add_subplot(gs[9:12, 6:12]),
        "r2c3": figf.add_subplot(gs[9:12, 12:18]),
        "r3c1": figf.add_subplot(gs[12:18, 0:6]),
        "r3c2": figf.add_subplot(gs[12:18, 6:12]),
        "r3c3": figf.add_subplot(gs[12:18, 12:18]),
        "r4c1": figf.add_subplot(gs[18:21, 0:6]),
        "r4c2": figf.add_subplot(gs[18:21, 6:12]),
        "r4c3": figf.add_subplot(gs[18:21, 12:18]),
        "r5c1": figf.add_subplot(gs[21:24, 0:6]),
        "r5c2": figf.add_subplot(gs[21:24, 6:12]),
        "r5c3": figf.add_subplot(gs[21:24, 12:18]),
        "r6c1": figf.add_subplot(gs[24:27, 0:6]),
        "r6c2": figf.add_subplot(gs[24:27, 6:12]),
        "r6c3": figf.add_subplot(gs[24:27, 12:18]),
    }

    clr_group = ["#4b157d", "#dda0dd", "#8c40a3"]
    clr_phase = ["orangered", "orange", "#c17d3a"]

    # Initialize dimmed cividis colormap (skips dark blue tail end)
    orig_cmap = plt.get_cmap("cividis")
    cividis_dim = mcolors.LinearSegmentedColormap.from_list(
        "cividis_dim", orig_cmap(np.linspace(0.2, 1.0, 256))
    )

    return figf, axes_dict, clr_group, clr_phase, cividis_dim   

def plot_map_init(map_style="Default", etopo_nc=None, stations="", qgis_dir=None, use_qgis=False):
    """Router for map initialization based on the selected rendering style."""
    if map_style.lower() == "default":
        return plot_map_init_default(etopo_nc=etopo_nc, stations=stations)
    elif map_style.lower() == "private":
        return plot_map_init_private(etopo_nc=etopo_nc, qgis_dir=qgis_dir, use_qgis=use_qgis)
    else:
        raise ValueError(
            f"Invalid map_style '{map_style}'. Expected 'Default' or 'Private'."
        )

def plot_map_init_private(etopo_nc=None, qgis_dir=None, use_qgis=False):
    """Initializes private mode map view.

    Renders ETOPO elevation and overlays QGIS tectonic layer if `use_qgis` is True
    and a valid directory path is provided. Falls back to standard coastlines/countries
    if QGIS data is disabled or unavailable.
    """
    crnrlon1, crnrlon2 = 4.95, 25.45
    crnrlat1, crnrlat2 = 44.45, 55.3

    plt.ioff()
    fig_map, ax_map = plt.subplots(figsize=(9, 9))

    my_map = Basemap(
        projection="lcc",
        lat_0=(crnrlat1 + crnrlat2) / 2.0,
        lon_0=(crnrlon1 + crnrlon2) / 2.0,
        resolution="h",
        area_thresh=100.0,
        llcrnrlon=crnrlon1,
        llcrnrlat=crnrlat1,
        urcrnrlon=crnrlon2,
        urcrnrlat=crnrlat2,
        ax=ax_map,
    )

    # 1. Base topography / background fill
    plot_map_render_topo_or_fill(my_map, ax_map, etopo_nc)

    # 2. Gridlines (Parallels & Meridians)
    my_map.drawparallels(
        np.arange(-90, 90, 4),
        labels=[1, 0, 0, 0],
        linewidth=2,
        dashes=[5, 242],
        fontsize=12,
    )
    my_map.drawmeridians(
        np.arange(10, 25, 5),
        labels=[0, 0, 0, 1],
        linewidth=2,
        dashes=[11, 195],
        fontsize=12,
    )

    # 3. QGIS layer rendering with fallback guard
    if use_qgis and qgis_dir and os.path.exists(qgis_dir):
        plot_map_qgis(qgis_dir, my_map, ax_map)
    else:
        my_map.drawcountries(linewidth=1.0, color="black", zorder=4)
        my_map.drawcoastlines(linewidth=1.0, color="black", zorder=4)

    return fig_map, ax_map, my_map

def plot_map_qgis(QGISDIR, my_map, ax):
    """OPTIONAL QGIS LAYER: Parses and plots tectonic faults, fronts, volcanics,

    basins, and massifs onto the Basemap instance.
    """
    # -----------------------------
    # 1. Sutures
    # -----------------------------
    with open(QGISDIR + "/EGDI_Faults/EGDI_Sutures.csv", "r") as infile:
        reader = csv.DictReader(
            infile,
            delimiter=",",
            fieldnames=(
                "pkuid",
                "vertex_index",
                "xcoord",
                "ycoord",
                "code",
                "name",
            ),
        )
        faults = {}
        for row in reader:
            if row["pkuid"] != "pkuid":
                for header, value in row.items():
                    try:
                        faults[header].append(value)
                    except KeyError:
                        faults[header] = [value]
    for object in sorted(set(faults["pkuid"])):
        count = -1
        ix = 0
        for i, id in enumerate(faults["pkuid"]):
            if id == object:
                count += 1
                ix = i
        latitude = faults["ycoord"][ix - count : ix + 1]
        longitude = faults["xcoord"][ix - count : ix + 1]
        latf = [float(i) for i in latitude]
        lonf = [float(i) for i in longitude]
        x, y = my_map(lonf, latf)

        if 33 <= int(object) <= 39:  # TTS exposed
            ax.plot(
                x, y, linestyle="-", linewidth=10, color="grey", alpha=0.5, zorder=9
            )
        elif 55 <= int(object) <= 56:  # SAVA
            ax.plot(
                x, y, linestyle="-", linewidth=5, color="grey", alpha=0.5, zorder=9
            )

    # -----------------------------
    # 2. Fronts
    # -----------------------------
    with open(QGISDIR + "/EGDI_Faults/EGDI_Fronts.csv", "r") as infile:
        reader = csv.DictReader(
            infile,
            delimiter=",",
            fieldnames=(
                "pkuid",
                "vertex_index",
                "xcoord",
                "ycoord",
                "code",
                "name",
            ),
        )
        faults = {}
        for row in reader:
            if row["pkuid"] != "pkuid":
                for header, value in row.items():
                    try:
                        faults[header].append(value)
                    except KeyError:
                        faults[header] = [value]
    for object in sorted(set(faults["pkuid"])):
        count = -1
        ix = 0
        for i, id in enumerate(faults["pkuid"]):
            if id == object:
                count += 1
                ix = i
        latitude = faults["ycoord"][ix - count : ix + 1]
        longitude = faults["xcoord"][ix - count : ix + 1]
        latf = [float(i) for i in latitude]
        lonf = [float(i) for i in longitude]
        x, y = my_map(lonf, latf)

        if 10 <= int(object) <= 11:  # ADF
            ax.plot(
                x, y, linestyle="-", linewidth=3, color="black", alpha=0.5, zorder=9
            )
        elif int(object) == 15:  # Jura - ADF
            ax.plot(
                x, y, linestyle="-", linewidth=2, color="black", alpha=0.5, zorder=9
            )

    # -----------------------------
    # 3. Volcanics
    # -----------------------------
    with open(QGISDIR + "/IGME5000_Volcanics/Volcanics.csv", "r") as infile:
        reader = csv.DictReader(
            infile,
            delimiter=",",
            fieldnames=(
                "pkuid",
                "vertex_index",
                "xcoord",
                "ycoord",
                "code",
                "name",
            ),
        )
        volcs = {}
        for row in reader:
            if row["pkuid"] != "pkuid":
                for header, value in row.items():
                    try:
                        volcs[header].append(value)
                    except KeyError:
                        volcs[header] = [value]
    for object in sorted(set(volcs["pkuid"])):
        count = -1
        ix = 0
        for i, id in enumerate(volcs["pkuid"]):
            if id == object:
                count += 1
                ix = i
        latitude = volcs["ycoord"][ix - count : ix + 1]
        longitude = volcs["xcoord"][ix - count : ix + 1]
        latf = [float(i) for i in latitude]
        lonf = [float(i) for i in longitude]
        x, y = my_map(lonf, latf)
        xy = list(zip(x, y))
        poly = Polygon(
            xy,
            facecolor="none",
            edgecolor="black",
            linestyle=":",
            linewidth=1.5,
            alpha=0.5,
            fill=False,
            zorder=9,
        )
        ax.add_patch(poly)
        poly.set_hatch("." * 3)
        poly.set_color("gray")

    # -----------------------------
    # 4. Basins (Pannonian, PoPlain, Scheck99)
    # -----------------------------
    basin_files = [
        "/IGME5000_Basins/IGME5000_PB_Pannonian.csv",
        "/IGME5000_Basins/IGME5000_POP_PoPlain.csv",
        "/IGME5000_Basins/Basins_fromScheck99.csv",
    ]
    for bfile in basin_files:
        with open(QGISDIR + bfile, "r") as infile:
            reader = csv.DictReader(
                infile,
                delimiter=",",
                fieldnames=(
                    "pkuid",
                    "vertex_index",
                    "xcoord",
                    "ycoord",
                    "code",
                    "name",
                ),
            )
            masfs = {}
            for row in reader:
                if row["pkuid"] != "pkuid":
                    for header, value in row.items():
                        try:
                            masfs[header].append(value)
                        except KeyError:
                            masfs[header] = [value]
        for object in sorted(set(masfs["pkuid"])):
            count = -1
            ix = 0
            for i, id in enumerate(masfs["pkuid"]):
                if id == object:
                    count += 1
                    ix = i
            names = masfs["pkuid"][ix - count : ix + 1]
            latitude = masfs["ycoord"][ix - count : ix + 1]
            longitude = masfs["xcoord"][ix - count : ix + 1]
            latf = [float(i) for i in latitude]
            lonf = [float(i) for i in longitude]
            x, y = my_map(lonf, latf)
            xy = list(zip(x, y))
            poly = Polygon(
                xy,
                facecolor="none",
                linestyle=":",
                edgecolor="black",
                linewidth=1.5,
                label=names[0],
                fill=False,
                zorder=9,
            )
            ax.add_patch(poly)

    # -----------------------------
    # 5. Massifs (Restored original conditional structure)
    # -----------------------------
    with open(QGISDIR + "/IGME5000_Massifs/Massifs.csv", "r") as infile:
        reader = csv.DictReader(
            infile,
            delimiter=",",
            fieldnames=(
                "pkuid",
                "vertex_index",
                "xcoord",
                "ycoord",
                "code",
                "name",
            ),
        )
        masfs = {}
        for row in reader:
            if row["pkuid"] != "pkuid":
                for header, value in row.items():
                    try:
                        masfs[header].append(value)
                    except KeyError:
                        masfs[header] = [value]
    for object in sorted(set(masfs["pkuid"])):
        count = -1
        ix = 0
        for i, id in enumerate(masfs["pkuid"]):
            if id == object:
                count += 1
                ix = i
        names = masfs["pkuid"][ix - count : ix + 1]
        latitude = masfs["ycoord"][ix - count : ix + 1]
        longitude = masfs["xcoord"][ix - count : ix + 1]
        latf = [float(i) for i in latitude]
        lonf = [float(i) for i in longitude]
        x, y = my_map(lonf, latf)
        xy = list(zip(x, y))

        if 70 <= int(object) < 90:
            if int(object) != 70:
                poly = Polygon(
                    xy,
                    facecolor="none",
                    linestyle="--",
                    edgecolor="black",
                    linewidth=1,
                    alpha=0.5,
                    label=names[0],
                    fill=False,
                    zorder=9,
                )
                ax.add_patch(poly)
        else:
            poly = Polygon(
                xy,
                facecolor="none",
                linestyle="-",
                edgecolor="black",
                linewidth=1.5,
                alpha=0.5,
                label=names[0],
                fill=False,
                zorder=9,
            )
            ax.add_patch(poly)

    # -----------------------------
    # 6. Faults
    # -----------------------------
    fault_files = [
        "/EGDI_Faults/EGDI_Faults.csv",
        "/IGME5000_FaultsBM/BMfaults.csv",
        "/IGME5000_FaultsAlps/AlpFaults.csv",
    ]
    for ffile in fault_files:
        with open(QGISDIR + ffile, "r") as infile:
            reader = csv.DictReader(
                infile,
                delimiter=",",
                fieldnames=(
                    "pkuid",
                    "vertex_index",
                    "xcoord",
                    "ycoord",
                    "code",
                    "name",
                ),
            )
            faults = {}
            for row in reader:
                if row["pkuid"] != "pkuid":
                    for header, value in row.items():
                        try:
                            faults[header].append(value)
                        except KeyError:
                            faults[header] = [value]
        for object in sorted(set(faults["pkuid"])):
            count = -1
            ix = 0
            for i, id in enumerate(faults["pkuid"]):
                if id == object:
                    count += 1
                    ix = i
            latitude = faults["ycoord"][ix - count : ix + 1]
            longitude = faults["xcoord"][ix - count : ix + 1]
            latf = [float(i) for i in latitude]
            lonf = [float(i) for i in longitude]
            x, y = my_map(lonf, latf)
            if "EGDI_Faults" in ffile and int(object) == 54:
                continue
            ax.plot(x, y, linestyle="-", linewidth=1, color="black", zorder=9)


def plot_map_embed(fig_map, ax_map, axes_dict, handles, dpi=96):
    """EMBED & CLEANUP MAP: Memory-buffers current map state, embeds into Row 1

    Col 1 (r1c1) cell, and clears pair overlays.
    """
    ax_r1c1 = axes_dict["r1c1"]

    buf = io.BytesIO()
    fig_map.savefig(
        buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05
    )
    buf.seek(0)
    img = plt.imread(buf)

    ax_r1c1.imshow(img)
    ax_r1c1.axis("off")

    del img
    buf.close()
    del buf

    # Remove active pair overlays so map remains clean for next station pair
    for handle in handles:
        handle.remove()

### WIGGLE TRACES - ROW=2

def plot_trace_init(cc):
    """1. INITIALIZE TRACE PLOTS: Creates isolated canvas and styling arrays."""
    plt.ioff()  # Suppress canvas screen pop-ups
    fig_trace, ax2 = plt.subplots(figsize=(6, 3))

    # Match indexing: 0 = Average, 1 = Acausal, 2 = Causal
    clr_trace = ["black", "darkblue", "darkred"]
    clr_trfill = ["lightgrey", "lightblue", "lightcoral"]
    itr_label = ["Average", "Acausal side", "Causal side"]

    return fig_trace, ax2, clr_trace, clr_trfill, itr_label


def plot_trace_main(
    ax2, itr, acc, st, dist_km, clr_trace, clr_trfill, itr_label
):
    """2. PROCESS & PLOT TRACE MAIN: Handles filtering, joint 3C normalization,

    slicing, and rendering for the active trace inside the component loop.
    """
    # Calculate joint maximum amplitude across all 3 components in proc_st
    st_plot=st.copy()
    st_plot.filter('bandpass',freqmin=0.015625,freqmax=0.25,zerophase=True,corners=2)
      # ----------------------------
      # Normalize amplitude
      # ----------------------------
    max_amp = np.max(np.abs([st_plot[0+acc],st_plot[1+acc], st_plot[2+acc]]))

    # Filter a temporary copy of the active trace (1C processing)
    tr_plot = st_plot[itr+acc].copy()

    # Normalize amplitude
    norm_data = tr_plot.data / (max_amp+0.0000000001)

    # Define time sampling & slicing parameters
    dt = 0.1  # seconds
    t_whole = np.arange(len(norm_data)) * dt

    t0 = max(0, int(np.round(dist_km / 3)) - 100)

    # Slice data array and time vector
    slice_start = t0 * 10
    slice_end = t0 * 10 + 2000

    t_slice = t_whole[slice_start:slice_end]
    trace_slice = norm_data[slice_start:slice_end]

    # --- Plotting ---
    # Vector line path
    ax2.plot(
        t_slice,
        trace_slice,
        color=clr_trace[itr],
        linewidth=1.3,
        label=itr_label[itr],
        zorder=10 - itr,
    )

    # Baseline fill for positive region
    ax2.fill_between(
        t_slice,
        trace_slice,
        0,
        where=(trace_slice > 0),
        color=clr_trfill[itr],
        alpha=0.50 if itr != 0 else 0.55,
        zorder=5 - itr,
    )

def plot_trace_embed(fig_trace, ax2, cc, dist_km, axes_dict, dpi=96):
    """3. EMBED & FINALISE TRACE: Formats axes, overlays velocity guides, and

    embeds final PNG into Row 2 grid destinations.
    """
    # Group velocity guide lines
    tv2p5 = dist_km / 2.5
    tv3p5 = dist_km / 3.5

    ax2.axvline(x=tv2p5, color="black", linestyle="--", linewidth=1.3)
    ax2.axvline(x=tv3p5, color="black", linestyle="--", linewidth=1.3)
    ax2.text(
        tv2p5 + 4,
        -1.0,
        "2.5 km/s",
        ha="center",
        va="bottom",
        fontsize=8,
        color="black",
        rotation=-90,
    )
    ax2.text(
        tv3p5 + 4,
        -1.0,
        "3.5 km/s",
        ha="center",
        va="bottom",
        fontsize=8,
        color="black",
        rotation=-90,
    )

    ax2.axhline(0, color="black", linestyle="-", linewidth=1)
    ax2.set_ylim(-1.05, 1.05)
    ax2.set_xlabel("Time lag (s)")
    ax2.set_ylabel("Amplitude")
    ax2.grid(alpha=0.3)
    ax2.set_title(f"Cross-correlation ({cc})")

    # Reorder legend entries (Average -> Causal -> Acausal)
    h, l = zip(*dict(zip(*ax2.get_legend_handles_labels())).items())
    order = [0, 2, 1]  # Index 0: Average, Index 2: Causal, Index 1: Acausal
    ax2.legend(
        [h[i] for i in order if i < len(h)],
        [l[i] for i in order if i < len(l)],
        ncol=1,
        loc="upper right",
        fontsize=10,
    )

    fig_trace.tight_layout()

    # Destination mapping for Row 2
    grid_map = {"ZZ": "r2c1", "RR": "r2c2", "TT": "r2c3"}
    target_ax_name = grid_map.get(cc)

    if target_ax_name not in axes_dict:
        print(f"Error: Master Trace axis '{target_ax_name}' not found.")
        plt.close(fig_trace)
        return

    # Memory buffer embedding
    buf2 = io.BytesIO()
    fig_trace.savefig(
        buf2, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05
    )
    buf2.seek(0)
    img2 = plt.imread(buf2)

    ax_target = axes_dict[target_ax_name]
    ax_target.imshow(img2)
    ax_target.axis("off")

    # Resource destruction
    del img2
    buf2.close()
    del buf2
    plt.close(fig_trace)


### FTAN DIAGRAMS - ROW=3
def plot_diagram_init(cc):
    """
    1. INITIALIZE: Creates a clean, isolated square figure 
    for the current component.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    return fig, ax


# --- C. DELEGATE TO SUB-DEFS (Group & Phase) ---
    if group_data is not None:
        plot_group_dispersion(
            ax=ax, 
            itr=itr, 
            ftan_pick=group_data['ftan_pick'], 
            GVfirst=group_data['GVfirst'], 
            GVlast=group_data['GVlast'], 
            GVnval=group_data['GVnval'], 
            yin_filled=group_data['yin_filled'], 
            dist_km=dist_km,
            clr_group=clr_group
        )
        
    if phase_data is not None:
        plot_phase_dispersion(
            ax=ax, 
            itr=itr, 
            bzero_pick=phase_data['bzero_pick'], 
            PVfirst=phase_data['PVfirst'], 
            PVlast=phase_data['PVlast'], 
            PVnval=phase_data['PVnval'], 
            dist_km=dist_km,
            clr_phase=clr_phase
        )

def plot_diagram_main(ax, itr, dist_km, Xii, Yii, Xpp, Ypp, 
                      anchors=None, Zii=None, plot_background=True,
                      group_data=None, phase_data=None, crossings_data2plot=None,
                      clr_group=None, clr_phase=None):
    """
    2. MAIN PLOT ORCHESTRATOR: Handles background, anchors, lambda guidelines (unlabeled), 
    conditionally passes tasks down to group or phase sub-functions, and renders phase crossings.
    """
    # --- AV TRACE ONLY (itr == 0) -> Background & Anchors ---
    if itr == 0:
        if plot_background and (Zii is not None):
            plotZpp = interpolate.griddata(
                (Xii.flatten(), Yii.flatten()), 
                Zii.flatten(), 
                (Xpp, Ypp), 
                method='cubic'
            )
            ax.pcolormesh(Xpp, Ypp, plotZpp, cmap='cividis', vmin=1, vmax=2, alpha=0.6, shading='auto', zorder=1)

        if anchors is not None:
            plot_pickq = np.array(anchors['pickq'])  
            facecolors = np.select(
                [plot_pickq == 1, plot_pickq == 0.25, plot_pickq == 0, plot_pickq == 0.5, plot_pickq == 0.9],
                ['#39ffcc', 'none', 'none', 'none', 'none'],  
                default='none'
            )
            edgecolors = np.select(
                [plot_pickq == 1, plot_pickq == 0.25, plot_pickq == 0, plot_pickq == 0.5, plot_pickq == 0.9],
                ['#02b587', '#02b587', '#02b587', '#02b587', '#02b587'],  
                default='#02b587'
            )
            ax.scatter(
                np.array(anchors['flt4anch']['t_ctr']), 
                anchors['pickv'],
                facecolor=facecolors, 
                edgecolor=edgecolors,
                s=180, 
                marker='*', 
                zorder=29
            )
        ax.scatter([], [], marker='*', facecolor='#39ffcc',edgecolor='#02b587', s=180, label="Anchor") 

     # PHASE CROSSINGS (TRI-CROSS) ---
        if crossings_data2plot is not None:
            pos_x, pos_y, neg_x, neg_y = crossings_data2plot

            # Plot positive crossings (up / ^)
            if len(pos_x) > 0:
                ax.scatter(pos_x, pos_y, marker='2', color='#8f2600', s=30, zorder=3)   #marker tri_up

            # Plot negative crossings (down / v)
            if len(neg_x) > 0:
                ax.scatter(neg_x, neg_y, marker='1', color='#8f2600', s=30, zorder=3)   #marker tri_down
    
        ax.scatter([95], [2.25], marker='2', color='#8f2600', s=30, zorder=99)
        ax.scatter([], [], marker='1', color='#8f2600', s=30, label="Crossings (up/down)")


    # Lambda Guidelines (No Legend) ---
        ax.scatter(Xpp, dist_km / 3 / Xpp, color='dimgrey', s=1, marker=".", label='_nolegend_', zorder=2)
        ax.scatter(Xpp, dist_km / 2 / Xpp, color='grey', s=1, marker=".", label='_nolegend_')
        ax.scatter(Xpp, dist_km / 1 / Xpp, color='darkgrey', s=1, marker=".", label='_nolegend_', zorder=2)

    # DELEGATE TO SUB-DEFS (Group & Phase) ---
    if group_data is not None:
        plot_group_dispersion(
            ax=ax, 
            itr=itr, 
            ftan_pick=group_data['ftan_pick'], 
            GVfirst=group_data['GVfirst'], 
            GVlast=group_data['GVlast'], 
            GVnval=group_data['GVnval'], 
            yin_filled=group_data['yin_filled'], 
            dist_km=dist_km,
            clr_group=clr_group
        )

    if phase_data is not None:
        plot_phase_dispersion(
            ax=ax, 
            itr=itr, 
            bzero_pick=phase_data['bzero_pick'], 
            PVfirst=phase_data['PVfirst'], 
            PVlast=phase_data['PVlast'], 
            PVnval=phase_data['PVnval'], 
            dist_km=dist_km,
            clr_phase=clr_phase
        )        

def plot_group_dispersion(ax, itr, ftan_pick, GVfirst, GVlast, GVnval, yin_filled, dist_km,  clr_group=None):
    """
    Sub-function to draw Group dispersion curves and scatters based on current trace iteration.
    Restored to clean original syntax.
    """
    if itr == 0:  # Average 
        facecolors = np.where(ftan_pick['pick_q'] >= 0.75, clr_group[itr], 'none')
        edgecolors = np.where(ftan_pick['pick_q'] >= 0.75, clr_group[itr], clr_group[itr])
        
        if GVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if GVfirst <= a <= GVlast]),
                    color=clr_group[itr], linestyle="-", linewidth=2.5, label='_nolegend_', zorder=8)
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if (GVlast <= a and 2*a*b < dist_km)]),
                    color=clr_group[itr], linestyle=":", linewidth=1.3, zorder=8)
            ax.scatter(ftan_pick['period'], yin_filled[::-1], label='_nolegend_',
                       facecolor=facecolors, edgecolor=edgecolors, s=30, marker='o', zorder=8)
        
        ax.plot([], [], color=clr_group[itr], marker='o', linestyle='-', linewidth=2.5, label='Group average')

    elif itr == 1:  # Reverse / Acausal
        if GVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if GVfirst <= a <= GVlast]),
                    color=clr_group[itr], linestyle="-", linewidth=1.5, label="_nolegend_", zorder=7)
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if (GVlast <= a and 2*a*b < dist_km)]),
                    color=clr_group[itr], linestyle=":", linewidth=1.0, zorder=7)
        ax.plot([], [], color=clr_group[itr], linestyle='-', linewidth=1.5, label="Group acausal")

    elif itr == 2:  # Forward / Causal
        if GVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if GVfirst <= a <= GVlast]),
                    color=clr_group[itr], linestyle="-", linewidth=1.5, label="_nolegend_", zorder=7)
            ax.plot(*zip(*[(a, b) for a, b in zip(ftan_pick['period'], ftan_pick['poly_v']) if (GVlast <= a and 2*a*b < dist_km)]),
                    color=clr_group[itr], linestyle=":", linewidth=1.0, zorder=7)
        ax.plot([], [], color=clr_group[itr], linestyle='-', linewidth=1.5, label="Group causal")


def plot_phase_dispersion(ax, itr, bzero_pick, PVfirst, PVlast, PVnval, dist_km, clr_phase=None):
    """
    Sub-function to draw Phase dispersion curves and scatters based on current trace iteration.
    Restored to clean original syntax.
    """
    if itr == 0:  # Average 
        facecolors = np.where(bzero_pick['pick_q'] == 1, clr_phase[itr], 'none')
        edgecolors = np.where(bzero_pick['pick_q'] == 1, clr_phase[itr], clr_phase[itr])
        
        if PVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if PVfirst <= a <= PVlast]),
                    color=clr_phase[itr], linestyle="-", linewidth=2.5, label='_nolegend_', zorder=11)
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if (PVlast <= a and 1*a*b < dist_km)]),
                    color=clr_phase[itr], linestyle=":", linewidth=1.3, zorder=11)
            ax.scatter(bzero_pick['period'], bzero_pick['pick_v'],
                       label='_nolegend_', facecolor=facecolors, edgecolor=edgecolors, s=30, marker='d', zorder=11)
        
        ax.plot([], [], color=clr_phase[itr], marker='d', linestyle='--', linewidth=2.5, label="Phase average")

    elif itr == 1:  # Reverse / Acausal
        if PVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if PVfirst <= a <= PVlast]),
                    color=clr_phase[itr], linestyle="-", linewidth=1.5, label="_nolegend_", zorder=10)
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if (PVlast <= a and 1*a*b < dist_km)]),
                    color=clr_phase[itr], linestyle=":", linewidth=1.0, zorder=10)
        ax.plot([], [], color=clr_phase[itr], linestyle='-', linewidth=1.5, label="Phase acausal")

    elif itr == 2:  # Forward / Causal
        if PVnval > 0:
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if PVfirst <= a <= PVlast]),
                    color=clr_phase[itr], linestyle="-", linewidth=1.5, label="_nolegend_", zorder=10)
            ax.plot(*zip(*[(a, b) for a, b in zip(bzero_pick['period'], bzero_pick['poly_v']) if (PVlast <= a and 1*a*b < dist_km)]),
                    color=clr_phase[itr], linestyle=":", linewidth=1.0, zorder=10)
        ax.plot([], [], color=clr_phase[itr], linestyle='-', linewidth=1.5, label="Phase causal")


def plot_diagram_embed(fig, ax, cc, axes_dict, dpi=96):
    """
    3. EMBED & FINALISE: Applies final styling, axes restrictions, builds the fake 
    lambda legend, cleans up main legends via strict indexing, and maps to the master layout.
    """
    # --- 1. Apply layout limits & grids ---
    ax.set_xlim(0, 150)
    ax.set_ylim(1.75, 4.75)  
    ax.set_xlabel("Period (s)")
    ax.set_ylabel("Velocity (km/s)")
    ax.grid(alpha=0.2)
    
    # --- 2. Manual Top-Right Fake Legend (Lambda Cutoffs) ---
    
    # Define the bounding box area based on your text coordinates
    # xmin=76, ymin=4.33, width=54 (up to x=130), height=0.33 (up to y=4.66)
    box = FancyBboxPatch(
        (76, 4.33), 68, 0.33,
        boxstyle="round,pad=0.03,rounding_size=0.04",
        facecolor="#EAEAEA",  # Soft background tint matching default legends
        edgecolor="#CCCCCC",  # # Muted grey frame line
        linewidth=1.0,
        alpha=0.9,            # Slight opacity so it integrates cleanly
        zorder=98,  # Sits perfectly right beneath the text and scatters        
    )
    box.set_zorder(98)
    ax.add_patch(box)
    
    ax.text(80, 4.6, "Velocity cuttoff: ", ha='left', va='center', fontsize=10, color='black',zorder=99)
    ax.text(120, 4.6, "1 lambda", ha='left', va='center', fontsize=10, color='black',zorder=99)
    ax.text(120, 4.5, "2 lambda", ha='left', va='center', fontsize=10, color='black',zorder=99)
    ax.text(120, 4.4, "3 lambda", ha='left', va='center', fontsize=10, color='black',zorder=99)
    
    ax.scatter([114,116,118], [4.6,4.6,4.6], color='darkgrey', s=1, marker="s",zorder=100)
    ax.scatter([114,116,118], [4.5,4.5,4.5], color='grey', s=1, marker="s",zorder=100)
    ax.scatter([114,116,118], [4.4,4.4,4.4], color='dimgrey', s=1, marker="s",zorder=100)

    # --- 3. Dynamic Lower-Right 2-Column Legend ---
    # Deduplicate keeping order, then slice via your exact array order index map
    h, l = zip(*dict(zip(*ax.get_legend_handles_labels())).items())
    ax.legend([h[i] for i in [0, 2, 6, 4, 1, 3, 7, 5] if i < len(h)], 
              [l[i] for i in [0, 2, 6, 4, 1, 3, 7, 5] if i < len(l)], 
              ncol=2, loc='lower right', fontsize=10)
    
    fig.tight_layout()

    # --- 4. Determine master grid destination ---
    grid_map = {'ZZ': 'r3c1', 'RR': 'r3c2', 'TT': 'r3c3'}
    target_ax_name = grid_map.get(cc)
    
    if target_ax_name not in axes_dict:
        print(f"Error: Master axis '{target_ax_name}' not found.")
        plt.close(fig)
        return

    # --- 5. Render to memory and embed ---
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    buf.seek(0)
    img = plt.imread(buf)      

    ax_target = axes_dict[target_ax_name]
    ax_target.imshow(img)
    ax_target.axis("off")
        
    # Free up memory blocks completely
    del img
    buf.close()
    del buf
    plt.close(fig)

### QC ATTRIBUTES - ROW=6

def plot_qcgraphs_init(cc):
    """
    1. INITIALIZE QC GRAPHS: Creates a wide landscape figure for the 
    reliability metrics and hooks up the twin secondary y-axis.
    """
    plt.ioff()  # Turn off pop-ups temporarily
    fig, ax6 = plt.subplots(figsize=(6, 3))
    ax6_r = ax6.twinx()  # Secondary axis for BZQ
    return fig, ax6, ax6_r

def plot_qcgraphs_main(ax6, ax6_r, itr, clr_group, clr_phase, 
                       ftan_pick=None, bzero_pick=None, 
                       GVnval=0, PVnval=0, 
                       ax6_ccSNRmax=40, ax6_ccBZQmax=100):
    """
    2. PLOT QC MAIN: Draws SNR (group, circle markers) on the left axis 
    and BZQ (phase, diamond markers) on the right axis across iterations.
    """
    # Box parameters to mask data points behind the upper right legend box
    xlim1, xlim2 = 50, 999
    
    # --- A. PHASE RELIABILITY (BZQ -> Right Axis) ---
    if PVnval > 0 and bzero_pick is not None:
        # Dynamically bump limits if values clip
        max_bzq = np.nanmax(bzero_pick['bzq_posneg'])
        calculated_bzq_max = math.ceil(max_bzq / 10) * 10
        if calculated_bzq_max > ax6_ccBZQmax:
            ax6_ccBZQmax = calculated_bzq_max
            
        ylim1_bzq, ylim2_bzq = 0.6 * ax6_ccBZQmax, 999 
        mask_phase = ~((bzero_pick['period'] > xlim1) & (bzero_pick['period'] < xlim2) &
                       (bzero_pick['bzq_posneg'] > ylim1_bzq) & (bzero_pick['bzq_posneg'] < ylim2_bzq))
        
        ax6_r.plot(bzero_pick['period'][mask_phase], bzero_pick['bzq_posneg'][mask_phase], 
                   ':', lw=1.3, c=clr_phase[itr], label='_nolegend_', zorder=10-itr)
        ax6_r.scatter(bzero_pick['period'][mask_phase], bzero_pick['bzq_posneg'][mask_phase], 
                      c=clr_phase[itr], s=15, marker='d', label='_nolegend_', zorder=10-itr)

    # --- B. GROUP RELIABILITY (SNR -> Left Axis) ---
    if GVnval > 0 and ftan_pick is not None:
        max_snr = np.nanmax(ftan_pick['pick_snr'])
        calculated_snr_max = math.ceil(max_snr / 10) * 10
        if calculated_snr_max > ax6_ccSNRmax:
            ax6_ccSNRmax = calculated_snr_max
            
        ylim1_snr, ylim2_snr = 0.6 * ax6_ccSNRmax, 999
        mask_group = ~((ftan_pick['period'] > xlim1) & (ftan_pick['period'] < xlim2) &
                       (ftan_pick['pick_snr'] > ylim1_snr) & (ftan_pick['pick_snr'] < ylim2_snr))
        
        ax6.plot(ftan_pick['period'][mask_group], ftan_pick['pick_snr'][mask_group], 
                 ':', lw=1.3, c=clr_group[itr], zorder=10-itr, label='_nolegend_')
        ax6.scatter(ftan_pick['period'][mask_group], ftan_pick['pick_snr'][mask_group], 
                    c=clr_group[itr], s=15, marker='o', zorder=10-itr, label='_nolegend_')

    # --- C. FAKE SCATTERS FOR PROGRESSIVE LEGEND CONSTRUCTION ---
    if itr == 0: 
        ax6.scatter([], [], color=clr_group[itr], marker='o', s=15, label="Group average")
        ax6.scatter([], [], color=clr_phase[itr], marker='d', s=15, label="Phase average")
    elif itr == 1: 
        ax6.scatter([], [], color=clr_group[itr], marker='o', s=15, label="Group acausal")
        ax6.scatter([], [], color=clr_phase[itr], marker='d', s=15, label="Phase acausal")
    elif itr == 2: 
        ax6.scatter([], [], color=clr_group[itr], marker='o', s=15, label="Group causal")
        ax6.scatter([], [], color=clr_phase[itr], marker='d', s=15, label="Phase causal")
        
    return ax6_ccSNRmax, ax6_ccBZQmax

def plot_qcgraphs_embed(fig, ax6, ax6_r, cc, axes_dict, clr_group, clr_phase, ax6_ccSNRmax, ax6_ccBZQmax, dpi=96):
    """
    3. EMBED & FINALISE QC GRAPHS: Sets axes bounds, formats descriptions, 
    orders the 2-column legend, and loads the image into the master canvas grid maps.
    """
    # Global visual layout styling
    ax6.set_xlim(0, 150)
    ax6.set_ylim(-1, ax6_ccSNRmax)
    ax6.set_ylabel('SNR (dB)', color=clr_group[0])
    ax6.tick_params(axis='y', labelcolor=clr_group[0])
    ax6.set_xlabel("Period (s)")
    ax6.set_title(f"Measurement reliability ({cc})")
    ax6.grid(alpha=0.2)

    ax6_r.set_ylim(0, ax6_ccBZQmax)        
    ax6_r.set_ylabel('BZQ (%)', color=clr_phase[0])
    ax6_r.tick_params(axis='y', labelcolor=clr_phase[0])
      
    # Clean deduplication layout strategy while honoring order mapping index configuration
    h, l = zip(*dict(zip(*ax6.get_legend_handles_labels())).items())
    order = [0, 4, 2, 1, 5, 3]
    ax6.legend([h[i] for i in order if i < len(h)], 
               [l[i] for i in order if i < len(l)], 
               ncol=2, loc='upper right', fontsize=10)
    
    fig.tight_layout()

    # Determine master panel column path mapping targeting row 4
    grid_map = {'ZZ': 'r6c1', 'RR': 'r6c2', 'TT': 'r6c3'}
    target_ax_name = grid_map.get(cc)
    
    if target_ax_name not in axes_dict:
        print(f"Error: Master QC axis '{target_ax_name}' not found.")
        plt.close(fig)
        return

    # Render graphics sequence array to binary byte arrays
    buf6 = io.BytesIO()
    fig.savefig(buf6, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    buf6.seek(0)
    img6 = plt.imread(buf6)      
  
    ax_target = axes_dict[target_ax_name]
    ax_target.imshow(img6)
    ax_target.axis("off")
          
    # Total memory lifecycle scrub
    del img6           
    buf6.close()       
    del buf6
    plt.close(fig)    


### REAL SPECTRA - ROW=5
def plot_spec_init(cc):
    """
    1. INITIALIZE SPECTRA PLOTS: Creates the isolated figure canvas 
    and returns its handle alongside the dedicated line and fill styling styles.
    """
    plt.ioff()  # Suppress canvas screen pop-ups
    figspec, ax5 = plt.subplots(figsize=(6, 3))
    
    # Trace styling packages bundled locally during initialization
    clr_trace = ["black", "darkblue", "darkred"]
    clr_trfill = ["lightgrey", "lightblue", "lightcoral"]
    itr_label = ["Average", "Acausal side", "Causal side"]
    
    return figspec, ax5, clr_trace, clr_trfill, itr_label

def plot_spec_main(ax5, itr, freq, spec_detrend, clr_trace, clr_trfill, itr_label):
    """
    2. PLOT SPECTRA MAIN: Processes cross-correlation frequency arrays 
    to build overlapping spectra traces and transparent baseline envelope fills.
    """
    period = 1.0 / (freq + 1e-12)
    spec_plot=spec_detrend.copy()
    
    # Area shade mapping tracking positive real coefficients
    ax5.fill_between(
        period, spec_plot, 0, 
        where=(spec_plot > 0),
        color=clr_trfill[itr], 
        alpha=0.55, 
        zorder=5-itr
    )
    
    # Vector spectrum line path
    ax5.plot(
        period, spec_plot, 
        '-', lw=1.3, 
        c=clr_trace[itr], 
        label=itr_label[itr], 
        zorder=10-itr
    )

def plot_spec_embed(figspec, ax5, cc, axes_dict, dpi=96):
    """
    3. EMBED & FINALISE SPECTRA: Locks down the canvas boundaries, 
    orders the single-column legend list, and embeds into row 5 destination keys.
    """
    ax5.set_ylim(-1.05, 1.05)  # Strict symmetric boundaries
    ax5.set_xlim(0, 150)
    ax5.set_xlabel("Period (s)")
    ax5.set_ylabel("Normalised amplitude")
    ax5.set_title(f"Real part of cross-correlation spectra ({cc})")
    ax5.grid(alpha=0.3)
    
    # Handle single-column dynamic legend list reordering
    h, l = zip(*dict(zip(*ax5.get_legend_handles_labels())).items())
    order = [0, 2, 1]  # Average -> Causal side -> Acausal side
    ax5.legend(
        [h[i] for i in order if i < len(h)], 
        [l[i] for i in order if i < len(l)], 
        ncol=1, loc='lower right', fontsize=10
    )
    
    figspec.tight_layout()

    # Route mapping straight onto Row 5 grids
    grid_map = {'ZZ': 'r5c1', 'RR': 'r5c2', 'TT': 'r5c3'}
    target_ax_name = grid_map.get(cc)
    
    if target_ax_name not in axes_dict:
        print(f"Error: Master Spectra axis '{target_ax_name}' not found.")
        plt.close(figspec)
        return

    # Process and compress to memory image matrix blocks
    buf5 = io.BytesIO()
    figspec.savefig(buf5, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    buf5.seek(0)
    img5 = plt.imread(buf5)      
  
    ax_target = axes_dict[target_ax_name]
    ax_target.imshow(img5)
    ax_target.axis("off")
          
    # Memory footprint destruction cleanup routines
    del img5           
    buf5.close()       
    del buf5
    plt.close(figspec)    


def plot_map_init_default(etopo_nc=None, stations=""):
    """INITIALIZE MAP BASE (DEFAULT MODE)"""
    target_aspect = 10.0 / 9.0

    crnrlon1, crnrlon2, crnrlat1, crnrlat2, lon_0, lat_0 = plot_map_getcorners(
        stations, target_aspect=target_aspect, pad_deg=1.0
    )

    plt.ioff()
    fig_map, ax_map = plt.subplots(figsize=(9, 9))

    # Setup Basemap Instance
    my_map = Basemap(
        projection="lcc",
        lat_0=lat_0,
        lon_0=lon_0,
        resolution="h",
        area_thresh=100.0,
        llcrnrlon=crnrlon1,
        llcrnrlat=crnrlat1,
        urcrnrlon=crnrlon2,
        urcrnrlat=crnrlat2,
        ax=ax_map,
    )

    # Render ETOPO or Fallback Fill + Frame Spines
    plot_map_render_topo_or_fill(my_map, ax_map, etopo_nc)

    # Adaptive Parallels & Meridians Grid
    lat_step = max(1, int(np.round((crnrlat2 - crnrlat1) / 4.0)))
    lon_step = max(1, int(np.round((crnrlon2 - crnrlon1) / 4.0)))

    my_map.drawparallels(
        np.arange(-90, 91, lat_step),
        labels=[1, 0, 0, 0],
        linewidth=1,
        dashes=[5, 5],
        fontsize=10,
        zorder=3,
    )
    my_map.drawmeridians(
        np.arange(-180, 181, lon_step),
        labels=[0, 0, 0, 1],
        linewidth=1,
        dashes=[5, 5],
        fontsize=10,
        zorder=3,
    )

    my_map.drawcountries(linewidth=1.0, color="black", zorder=4)
    my_map.drawcoastlines(linewidth=1.0, color="black", zorder=4)

    return fig_map, ax_map, my_map

def plot_map_render_topo_or_fill(my_map, ax_map, etopo_nc):
    """
    Renders ETOPO elevation pcolormesh if file path is valid and exists.
    Otherwise, fills land and ocean with default Basemap colors.
    Guarantees ocean background fill remains visible while maintaining outer border crispness.
    """
    if etopo_nc and os.path.isfile(etopo_nc):
        # 1. Fill Ocean Background (Layer 1)
        my_map.drawmapboundary(fill_color="dodgerblue", linewidth=0, zorder=1)

        # 2. Topography Mesh (Layer 2)
        crop = Dataset(etopo_nc)
        lons = crop.variables["x"][:]
        lats = crop.variables["y"][:]
        topo = crop.variables["z"][:]
        crop.close()

        lontopo, lattopo = np.meshgrid(lons, lats)
        xtopo, ytopo = my_map(lontopo, lattopo)
        topo_masked = np.ma.masked_less(topo, 0)

        my_map.pcolormesh(
            xtopo,
            ytopo,
            topo_masked,
            cmap="terrain",
            shading="auto",
            vmin=-650,
            vmax=2600,
            zorder=2,
        )
    else:
        # Fallback Ocean Fill + Land Continents
        my_map.drawmapboundary(fill_color="lightskyblue", linewidth=0, zorder=1)
        my_map.fillcontinents(color="coral", lake_color="lightskyblue", zorder=2)

    # 3. Outer Frame Lines & Spines (Layer 10 - High Z-Order Line Only)
    for spine in ax_map.spines.values():
        spine.set_zorder(10)
        spine.set_linewidth(1.5)
        spine.set_edgecolor("black")
        spine.set_visible(True)
 

def plot_pillow_wrapup(fig, image_quality="Preview"):
    """
    Renders matplotlib figure to buffer, converts with Pillow based on quality,
    and returns (processed_image, raw_image_handle, buffer_handle) for cleanup.
    """
    # 1. Set DPI based on quality
    dpi = 300 if image_quality.upper() == "PUBLISH" else 96
    
    # 2. Render matplotlib figure to byte buffer
    fig.tight_layout()
    fig.patch.set_facecolor("white")
    
    buff = io.BytesIO()
    fig.savefig(
        buff,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.05,
        transparent=False
    )
    buff.seek(0)
    
    # 3. Open with PIL and decode into RAM
    imgf = Image.open(buff)
    imgf.load()
    
    # 4. Apply mode conversion
    if image_quality.upper() == "PUBLISH":
        imgout = imgf.convert("RGB") # Full 24-bit color depth
    else:
        imgout = imgf.convert("P", palette=Image.ADAPTIVE, colors=128) # Compressed palette
        
    return imgout, imgf, buff


def plot_pillow_cleanup(imgout, imgf, buff):
    """Closes images and memory buffers safely."""
    if imgout is not None:
        imgout.close()
    if imgf is not None:
        imgf.close()
    if buff is not None:
        buff.close()

def plot_map_getcorners(stations_file, target_aspect=10.0 / 9.0, pad_deg=1.0):
    """
    Scans station CSV to dynamically extract bounding coordinates and projection center.
    Automatically pads the bounding box to match target_aspect (width/height ratio)
    so the resulting map fits the r1c1 grid cell without awkward gaps.
    
    Rule for 'use': Skips ONLY if column 5 exists and equals 'N' (case-insensitive).
    """
    lons, lats = [], []
    with open(stations_file, "r") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0 or not row:
                continue
            try:
                if len(row) >= 5 and str(row[4]).strip().upper() == "N":
                    continue
                lons.append(float(row[1]))
                lats.append(float(row[2]))
            except (ValueError, IndexError):
                continue

    if not lons or not lats:
        raise ValueError(f"No valid stations found in {stations_file}")

    # Raw station bounding box with base padding
    min_lon = min(lons) - pad_deg
    max_lon = max(lons) + pad_deg
    min_lat = max(-90.0, min(lats) - pad_deg)
    max_lat = min(90.0, max(lats) + pad_deg)

    # Reference projection center
    lon_0 = np.mean(lons)
    lat_0 = np.mean(lats)

    # Span in degrees
    dlon = max_lon - min_lon
    dlat = max_lat - min_lat

    # Correct longitude distance for Earth curvature at mean latitude
    cos_lat = np.cos(np.radians(lat_0))
    current_aspect = (dlon * cos_lat) / dlat if dlat > 0 else target_aspect

    # Adjust bounding box to match target aspect ratio (centered on lon_0, lat_0)
    if current_aspect < target_aspect:
        # Map is too narrow -> widen longitude range
        required_dlon = (dlat * target_aspect) / cos_lat
        min_lon = lon_0 - (required_dlon / 2.0)
        max_lon = lon_0 + (required_dlon / 2.0)
    else:
        # Map is too wide -> heighten latitude range
        required_dlat = (dlon * cos_lat) / target_aspect
        min_lat = max(-90.0, lat_0 - (required_dlat / 2.0))
        max_lat = min(90.0, lat_0 + (required_dlat / 2.0))

    return min_lon, max_lon, min_lat, max_lat, lon_0, lat_0

def plot_map_main_default(
    fig_map, ax_map, my_map, lon1, lat1, lon2, lat2, net1, sta1, net2, sta2, dist_km, azim, wgt
):
    """OVERLAY STATION PAIR (DEFAULT MODE)"""
    # 1. Great Circle Path (Geodesic arc on sphere)
    great_circle_lines = my_map.drawgreatcircle(
        lon1, lat1, lon2, lat2,
        color="magenta",
        linestyle="--",
        linewidth=1.5,
        zorder=9,
        ax=ax_map
    )

    # 2. Convert points for station markers
    map_sta1 = my_map(lon1, lat1)
    map_sta2 = my_map(lon2, lat2)

    scatter1 = ax_map.scatter(
        map_sta1[0], map_sta1[1], 80, marker="v", color="magenta", zorder=9
    )
    scatter2 = ax_map.scatter(
        map_sta2[0], map_sta2[1], 80, marker="v", color="magenta", zorder=9
    )

    base_transform = ax_map.transData
    offset1 = offset_copy(base_transform, fig=fig_map, x=0, y=10, units="points")
    offset2 = offset_copy(base_transform, fig=fig_map, x=0, y=10, units="points")

    scattext1 = ax_map.text(
        map_sta1[0],
        map_sta1[1],
        f"{net1}.{sta1}",
        transform=offset1,
        fontsize=10,
        ha="center",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
        color="magenta",
        zorder=9,
    )

    scattext2 = ax_map.text(
        map_sta2[0],
        map_sta2[1],
        f"{net2}.{sta2}",
        transform=offset2,
        fontsize=10,
        ha="center",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
        color="magenta",
        zorder=9,
    )

    label_Pair = f"{net1}.{sta1}_{net2}.{sta2}"
    label_Dist = str(int(np.round(dist_km)))
    label_Az = str(int(np.round(azim)))
    label_Wgt = str(int(wgt))
    label_Text = f"{label_Pair}\nDist: {label_Dist} km | Az: {label_Az}° | Stack: {label_Wgt} d"

    text_info = ax_map.text(
        0.02,
        0.02,
        label_Text,
        transform=ax_map.transAxes,
        fontsize=10,
        va="bottom",
        ha="left",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        color="magenta",
        zorder=9,
    )

    # Return handles (great_circle_lines is a list of line elements)
    return great_circle_lines + [scatter1, scattext1, scatter2, scattext2, text_info]

def plot_map_main_private(
    fig_map, ax_map, my_map, lon1, lat1, lon2, lat2, net1, sta1, net2, sta2, dist_km, azim, wgt
):
    """OVERLAY STATION PAIR (PRIVATE MODE)"""
    # 1. Great Circle Path
    great_circle_lines = my_map.drawgreatcircle(
        lon1, lat1, lon2, lat2,
        color="magenta",
        linestyle="--",
        linewidth=1.5,
        zorder=9,
        ax=ax_map
    )

    # 2. Convert points for station markers
    map_sta1 = my_map(lon1, lat1)
    map_sta2 = my_map(lon2, lat2)

    scatter1 = ax_map.scatter(
        map_sta1[0], map_sta1[1], 80, marker="v", color="magenta", zorder=9
    )
    scattext1 = ax_map.text(
        map_sta1[0] - 40000,
        map_sta1[1] + 20000,
        f"{net1}.{sta1}",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.5),
        color="magenta",
        zorder=9,
    )

    scatter2 = ax_map.scatter(
        map_sta2[0], map_sta2[1], 80, marker="v", color="magenta", zorder=9
    )
    scattext2 = ax_map.text(
        map_sta2[0] - 40000,
        map_sta2[1] + 20000,
        f"{net2}.{sta2}",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.5),
        color="magenta",
        zorder=9,
    )

    label_Pair = f"{net1}.{sta1}_{net2}.{sta2}"
    label_Dist = str(int(np.round(dist_km)))
    label_Az = str(int(np.round(azim)))
    label_Wgt = str(int(wgt))
    label_Text = f"Distance: {label_Dist} km \nPath orientation: {label_Az}°\nStack length: {label_Wgt} d"

    base_transform = ax_map.transAxes
    offset_transform = offset_copy(
        base_transform, fig=fig_map, x=-150, y=8, units="points"
    )
    text = ax_map.text(
        0.99,
        0.01,
        label_Text,
        transform=offset_transform,
        fontsize=10,
        va="bottom",
        ha="left",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.5),
        color="magenta",
        zorder=9,
    )

    offset_transform = offset_copy(
        base_transform, fig=fig_map, x=-105, y=385, units="points"
    )
    text_title = ax_map.text(
        0.99,
        0.01,
        label_Pair,
        transform=offset_transform,
        fontsize=12,
        va="bottom",
        ha="right",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.5),
        color="magenta",
        zorder=9,
    )

    return great_circle_lines + [scatter1, scattext1, scatter2, scattext2, text, text_title]    

def plot_map_main(map_style="Default", **kwargs):
    """Branch Router for Main Overlay Function"""
    if map_style.lower() == "default":
        return plot_map_main_default(**kwargs)
    elif map_style.lower() == "private":
        return plot_map_main_private(**kwargs)
    else:
        raise ValueError(
            f"Invalid map_style '{map_style}'. Expected 'Default' or 'Private'."
        )

def plot_crossvalidation_main(ax1, dispersions):
    """
    PLOTS CROSS-VALIDATED DISPERSION CURVES:
    - Fills strictly bounded between AC, CA, and AV.
    - If AC or CA are NaN or masked, defaults back to the AV poly line value.
    """

    colors = {
        "ZZ": "#4C78A8",       # Blue
        "TT": "#F58518",       # Orange
        "RR": "darkseagreen",  # Greenish-grey tone
    }

    edge_colors = {
        "ZZ": "#2C527B",
        "TT": "#A65300",
        "RR": "#4E724E",       # Darker contour for darkseagreen
    }

    labels = {
        "ZZ": "Rayleigh (ZZ)",
        "RR": "Rayleigh (RR)",
        "TT": "Love (TT)",
    }

    periods = np.array(
        dispersions["period"][0]
        if isinstance(dispersions["period"][0], list)
        else dispersions["period"]
    )

    dist_km = float(dispersions["dist_azim_az_baz"][0])
    comp_indices = {"ZZ": 0, "TT": 6, "RR": 3}
    order_keys = ["ZZ", "TT", "RR"]

    group_poly_data = dispersions.get("group_poly", dispersions["group_v"])
    phase_poly_data = dispersions.get("phase_poly", dispersions["phase_v"])

    # --- 1. PLOT GROUP CURVES & SHADING ZONES ---
    for cc in order_keys:
        idx = comp_indices[cc]
        color = colors[cc]
        edge_color = edge_colors[cc]
        lbl = labels[cc]

        z_layer = 60 if cc == "ZZ" else (40 if cc == "TT" else 20)
        lw = 2.0 if cc == "RR" else 2.5
        alpha_val = 0.85 if cc == "RR" else 1.0
        alpha_fill = 0.25 if cc == "RR" else 0.18

        if "group_v" in dispersions and len(dispersions["group_v"]) > idx:
            gv_av = np.array(group_poly_data[idx])
            g_fln_m = dispersions["group_fln_masked"][idx]
            g_mask_av = np.array(dispersions["group_mask"][idx])

            if g_fln_m is not None and len(g_fln_m) >= 2 and g_fln_m[0] <= g_fln_m[1]:
                min_p_val, max_p_val = g_fln_m[0], g_fln_m[1]
                ifirst = int(np.argmin(np.abs(periods - min_p_val)))
                ilast = int(np.argmin(np.abs(periods - max_p_val)))

                sub_p = periods[ifirst : ilast + 1]
                sub_gv = gv_av[ifirst : ilast + 1]
                sub_mask = g_mask_av[ifirst : ilast + 1]

                valid_g_line = np.isfinite(sub_gv) & (sub_gv > 0) & sub_mask

                if np.any(valid_g_line):
                    has_subversions = (
                        len(group_poly_data) > idx + 2
                        and group_poly_data[idx + 1] is not None
                        and group_poly_data[idx + 2] is not None
                    )

                    if has_subversions:
                        gv_ac = np.array(group_poly_data[idx + 1])[ifirst : ilast + 1]
                        gv_ca = np.array(group_poly_data[idx + 2])[ifirst : ilast + 1]

                        g_mask_ac = np.array(dispersions["group_mask"][idx + 1])[ifirst : ilast + 1]
                        g_mask_ca = np.array(dispersions["group_mask"][idx + 2])[ifirst : ilast + 1]

                        # Fallback to AV value if AC or CA is NaN, non-positive, or unmasked
                        valid_ac_pts = np.isfinite(gv_ac) & (gv_ac > 0) & g_mask_ac
                        valid_ca_pts = np.isfinite(gv_ca) & (gv_ca > 0) & g_mask_ca

                        ac_clean = np.where(valid_ac_pts, gv_ac, sub_gv)
                        ca_clean = np.where(valid_ca_pts, gv_ca, sub_gv)

                        min_b = np.minimum.reduce([sub_gv, ac_clean, ca_clean])
                        max_b = np.maximum.reduce([sub_gv, ac_clean, ca_clean])
                        # Fill Zone (Tightened to AV curve where AC/CA drops out)
                        ax1.fill_between(
                            sub_p[valid_g_line],
                            min_b[valid_g_line],
                            max_b[valid_g_line],
                            color=color,
                            alpha=alpha_fill,
                            linewidth=0,
                            label="_nolegend_",
                            zorder=z_layer - 3,
                        )

                        # Plot AC subversion line
                        if np.any(valid_ac_pts & valid_g_line):
                            ax1.plot(
                                sub_p[valid_ac_pts & valid_g_line],
                                gv_ac[valid_ac_pts & valid_g_line],
                                color=color,
                                linestyle="-",
                                linewidth=0.8,
                                alpha=0.4,
                                label="_nolegend_",
                                zorder=z_layer - 2,
                            )

                        # Plot CA subversion line
                        if np.any(valid_ca_pts & valid_g_line):
                            ax1.plot(
                                sub_p[valid_ca_pts & valid_g_line],
                                gv_ca[valid_ca_pts & valid_g_line],
                                color=color,
                                linestyle="-",
                                linewidth=0.8,
                                alpha=0.4,
                                label="_nolegend_",
                                zorder=z_layer - 1,
                            )

                    # Main Group Line
                    ax1.plot(
                        sub_p[valid_g_line],
                        sub_gv[valid_g_line],
                        color=color,
                        linestyle="-",
                        linewidth=lw,
                        alpha=alpha_val,
                        label="_nolegend_",
                        zorder=z_layer,
                    )

                    # Scatterers for strictly valid crossvalidation points
                    ax1.scatter(
                        sub_p[valid_g_line],
                        sub_gv[valid_g_line],
                        facecolor=color,
                        edgecolor=edge_color,
                        linewidth=0.8,
                        marker="o",
                        s=20,
                        alpha=alpha_val,
                        label="_nolegend_",
                        zorder=z_layer + 1,
                    )

                    # Legend entry
                    ax1.plot(
                        [],
                        [],
                        color=color,
                        marker="o",
                        markeredgecolor=edge_color,
                        markeredgewidth=0.8,
                        linestyle="-",
                        linewidth=lw,
                        label=f"Group {lbl}",
                    )

    # --- 2. PLOT PHASE CURVES & SHADING ZONES ---
    for cc in order_keys:
        idx = comp_indices[cc]
        color = colors[cc]
        edge_color = edge_colors[cc]
        lbl = labels[cc]

        z_layer = 30 if cc == "ZZ" else (20 if cc == "TT" else 10)
        lw = 2.0 if cc == "RR" else 2.5
        alpha_val = 0.85 if cc == "RR" else 1.0
        alpha_fill = 0.25 if cc == "RR" else 0.18

        if "phase_v" in dispersions and len(dispersions["phase_v"]) > idx:
            pv_av = np.array(phase_poly_data[idx])
            p_fln_m = dispersions["phase_fln_masked"][idx]
            p_mask_av = np.array(dispersions["phase_mask"][idx])

            if p_fln_m is not None and len(p_fln_m) >= 2 and p_fln_m[0] <= p_fln_m[1]:
                min_p_val, max_p_val = p_fln_m[0], p_fln_m[1]
                ifirst = int(np.argmin(np.abs(periods - min_p_val)))
                ilast = int(np.argmin(np.abs(periods - max_p_val)))

                sub_p = periods[ifirst : ilast + 1]
                sub_pv = pv_av[ifirst : ilast + 1]
                sub_mask = p_mask_av[ifirst : ilast + 1]

                valid_p_line = np.isfinite(sub_pv) & (sub_pv > 0) & sub_mask

                if np.any(valid_p_line):
                    has_subversions = (
                        len(phase_poly_data) > idx + 2
                        and phase_poly_data[idx + 1] is not None
                        and phase_poly_data[idx + 2] is not None
                    )

                    if has_subversions:
                        pv_ac = np.array(phase_poly_data[idx + 1])[ifirst : ilast + 1]
                        pv_ca = np.array(phase_poly_data[idx + 2])[ifirst : ilast + 1]

                        p_mask_ac = np.array(dispersions["phase_mask"][idx + 1])[ifirst : ilast + 1]
                        p_mask_ca = np.array(dispersions["phase_mask"][idx + 2])[ifirst : ilast + 1]

                        # Fallback to AV value if AC or CA is NaN, non-positive, or unmasked
                        valid_ac_pts = np.isfinite(pv_ac) & (pv_ac > 0) & p_mask_ac
                        valid_ca_pts = np.isfinite(pv_ca) & (pv_ca > 0) & p_mask_ca

                        ac_clean = np.where(valid_ac_pts, pv_ac, sub_pv)
                        ca_clean = np.where(valid_ca_pts, pv_ca, sub_pv)

                        min_b = np.minimum.reduce([sub_pv, ac_clean, ca_clean])
                        max_b = np.maximum.reduce([sub_pv, ac_clean, ca_clean])

                        # Fill Zone (Tightened to AV curve where AC/CA drops out)
                        ax1.fill_between(
                            sub_p[valid_p_line],
                            min_b[valid_p_line],
                            max_b[valid_p_line],
                            color=color,
                            alpha=alpha_fill,
                            linewidth=0,
                            label="_nolegend_",
                            zorder=z_layer - 3,
                        )

                        # Plot AC subversion line
                        if np.any(valid_ac_pts & valid_p_line):
                            ax1.plot(
                                sub_p[valid_ac_pts & valid_p_line],
                                pv_ac[valid_ac_pts & valid_p_line],
                                color=color,
                                linestyle=":",
                                linewidth=0.8,
                                alpha=0.4,
                                label="_nolegend_",
                                zorder=z_layer - 2,
                            )

                        # Plot CA subversion line
                        if np.any(valid_ca_pts & valid_p_line):
                            ax1.plot(
                                sub_p[valid_ca_pts & valid_p_line],
                                pv_ca[valid_ca_pts & valid_p_line],
                                color=color,
                                linestyle=":",
                                linewidth=0.8,
                                alpha=0.4,
                                label="_nolegend_",
                                zorder=z_layer - 1,
                            )

                    # Main Phase Line
                    ax1.plot(
                        sub_p[valid_p_line],
                        sub_pv[valid_p_line],
                        color=color,
                        linestyle=":",
                        linewidth=lw,
                        alpha=alpha_val,
                        label="_nolegend_",
                        zorder=z_layer,
                    )

                    # Scatterers for strictly valid crossvalidation points
                    ax1.scatter(
                        sub_p[valid_p_line],
                        sub_pv[valid_p_line],
                        facecolor=color,
                        edgecolor=edge_color,
                        linewidth=0.8,
                        marker="d",
                        s=20,
                        alpha=alpha_val,
                        label="_nolegend_",
                        zorder=z_layer + 1,
                    )

                    # Legend entry
                    ax1.plot(
                        [],
                        [],
                        color=color,
                        marker="d",
                        markeredgecolor=edge_color,
                        markeredgewidth=0.8,
                        linestyle=":",
                        linewidth=lw,
                        label=f"Phase {lbl}",
                    )

    # --- 3. VELOCITY CUTOFF GUIDELINES & ANNOTATIONS ---
    cutoff_p = np.linspace(5, 150, 200)
    ax1.plot(cutoff_p, dist_km / (3 * cutoff_p), color="darkgrey", linestyle="--", linewidth=0.8, label="_nolegend_")
    ax1.plot(cutoff_p, dist_km / (2 * cutoff_p), color="grey", linestyle="--", linewidth=0.8, label="_nolegend_")
    ax1.plot(cutoff_p, dist_km / (1 * cutoff_p), color="dimgrey", linestyle="--", linewidth=0.8, label="_nolegend_")

    # --- 4. CROSS-VALIDATION STATUS TEXT ---
    raw_tag = dispersions.get("crossvalidation_tag", ["failed"])
    tag_str = str(raw_tag[0] if isinstance(raw_tag, (list, tuple)) and raw_tag else raw_tag)
    clean_tag = re.sub(r"[\[\]'\" ]", "", tag_str).lower()

    if clean_tag in ["z1rt0", "z2rt0"]:
        cv_status_text = "One-component (Z)"
    elif clean_tag in ["z1rt1", "z2rt1", "z1rt2", "z2rt2"]:
        cv_status_text = "Three-component (Z-R-T)"
    else:
        cv_status_text = "No valid picks"

    ax1.text(105, 2.12, f"Cross-validation status: {cv_status_text}", ha="center", va="center", fontsize=10, color="black", zorder=70)
    ax1.text(100, 4.6, "Velocity cutoff: ", ha="left", va="center", fontsize=10, color="black")
    ax1.text(129, 4.6, "1 lambda", ha="left", va="center", fontsize=10, color="dimgrey")
    ax1.text(129, 4.52, "2 lambda", ha="left", va="center", fontsize=10, color="grey")
    ax1.text(129, 4.44, "3 lambda", ha="left", va="center", fontsize=10, color="darkgrey")

    ax1.scatter([125, 126, 127], [4.6, 4.6, 4.6], color="dimgrey", s=4, marker="s", label="_nolegend_")
    ax1.scatter([125, 126, 127], [4.52, 4.52, 4.52], color="grey", s=4, marker="s", label="_nolegend_")
    ax1.scatter([125, 126, 127], [4.44, 4.44, 4.44], color="darkgrey", s=4, marker="s", label="_nolegend_")

    # --- 5. AXES FORMATTING & LEGEND ---
    ax1.set_xlim(0, 150)
    ax1.set_ylim(1.75, 4.75)
    ax1.set_xlabel("Period (s)")
    ax1.set_ylabel("Velocity (km/s)")
    ax1.set_title("Final cross-validated dispersion curves")
    ax1.grid(alpha=0.2)

    handles, labels_list = ax1.get_legend_handles_labels()
    ax1.legend(handles, labels_list, ncol=2, loc="lower right", fontsize=10)


def phase_crossings4plot_updown(crossings_tuple, bzero_pick, dist_km, cc="ZZ", params=None):
#def phase_crossings4plot_updown(crossings_tuple, bzero_pick, dist_km, coefT=1.0):
# Determine dynamic scaling factor: 1.1 for TT if specified in params, otherwise 1.0
    if params and cc == "TT":
        coefT = params.get("harmo_coeft", 1.1)
    else:
        coefT = 1.0
    """
    Extracts positive (up) and negative (down) Bessel zero crossings within the 
    finely-tuned dynamic phase velocity corridor, removing duplicates from pos points.
    
    Returns:
        pos_x, pos_y, neg_x, neg_y: Arrays of isolated positive and negative crossing points.
    """
    # CORRECT INDEXING BASED ON REAL TUPLE OUTPUT:
    # tuple[0]: pos velocities
    # tuple[1]: pos frequencies
    # tuple[2]: bessel order / n
    # tuple[3]: neg frequencies
    # tuple[5]: neg velocities
    pos_vels = crossings_tuple[0]
    pos_freqs = crossings_tuple[1]
    
    neg_freqs = crossings_tuple[3] if len(crossings_tuple) > 3 else None
    neg_vels = crossings_tuple[5] if len(crossings_tuple) > 5 else None

    # Extract xou (periods) and you1 (reference velocities)
    xou = np.asarray(bzero_pick.get('period', []))
    you1 = np.asarray(bzero_pick.get('refV', []))

    if len(xou) == 0 or len(you1) == 0:
        return np.array([]), np.array([]), np.array([]), np.array([])

    # Clean NaNs/Infs from reference arrays
    valid_ref = np.isfinite(xou) & np.isfinite(you1)
    xou = xou[valid_ref]
    you1 = you1[valid_ref]

    if len(xou) == 0:
        return np.array([]), np.array([]), np.array([]), np.array([])

    # np.interp REQUIRES x-coordinates to be strictly increasing.
    if xou[0] > xou[-1]:
        xou = xou[::-1]
        you1 = you1[::-1]

    # Safe evaluation helper (renamed)
    def safepoints(freqs, vels):
        if freqs is None or vels is None:
            return np.array([]), np.array([])
        f = np.asarray(freqs).ravel()
        v = np.asarray(vels).ravel()
        min_len = min(f.size, v.size)
        f, v = f[:min_len], v[:min_len]
        valid = (f > 0) & np.isfinite(f) & np.isfinite(v)
        if not np.any(valid):
            return np.array([]), np.array([])
        return 1.0 / f[valid], v[valid]

    pos_x, pos_v = safepoints(pos_freqs, pos_vels)
    neg_x, neg_v = safepoints(neg_freqs, neg_vels)

    epsilon = 1e-12

    # Inner helper function to filter point sets (renamed)
    def filterpoints(x_vals, y_vals):
        if len(x_vals) == 0:
            return np.array([]), np.array([])

        you1_at_x = np.interp(x_vals, xou, you1)
        xs = []
        ys = []

        for x, y, y1 in zip(x_vals, y_vals, you1_at_x):
            if not np.isfinite(y1) or y1 <= 0:
                continue

            # Lower bound calculation
            lower = dist_km / (dist_km / y1 + 2.499 * x)
            if lower < 1.8 * coefT: 
                lower = 1.8 * coefT

            # Upper bound calculation
            denom_upper = dist_km / y1 - 2.499 * x
            if abs(denom_upper) < epsilon:
                upper = dist_km / epsilon
            else:
                upper = dist_km / denom_upper

            if upper <= 0 or upper > 4.0 * coefT: 
                upper = 4.0 * coefT

            # Corridor filter
            if lower < y < upper:
                xs.append(x)
                ys.append(y)

        return np.array(xs), np.array(ys)

    # Process positive (up) and negative (down) completely independently
    pos_x_out, pos_y_out = filterpoints(pos_x, pos_v)
    neg_x_out, neg_y_out = filterpoints(neg_x, neg_v)

    # Fast drop of duplicated points from positive set if present in negative set
    if len(pos_x_out) > 0 and len(neg_x_out) > 0:
        neg_set = set(zip(neg_x_out, neg_y_out))
        keep_mask = np.array([(px, py) not in neg_set for px, py in zip(pos_x_out, pos_y_out)], dtype=bool)
        pos_x_out = pos_x_out[keep_mask]
        pos_y_out = pos_y_out[keep_mask]

    return pos_x_out, pos_y_out, neg_x_out, neg_y_out

def plot_crossvalidation_embed(fig1, ax_r1c2, dpi=96):
    """EMBED & FINALIZE: Renders fig1 into memory and displays it on target ax_r1c2."""
    fig1.tight_layout()
    
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    buf1.seek(0)
    img1 = plt.imread(buf1)
    
    ax_r1c2.imshow(img1)
    ax_r1c2.axis("off")
    
    del img1
    buf1.close()
    del buf1
    plt.close(fig1)

### ATTENUATION ATTRIBUTES - ROW=4
def plot_attenuation_init(cc):
    """
    1. INITIALIZE ATTENUATION GRAPHS: Creates a wide landscape figure for the 
    attenuation metrics.
    """
    plt.ioff()  # Turn off pop-ups temporarily
    fig, ax4 = plt.subplots(figsize=(6, 3))
    return fig, ax4

def plot_attenuation_main(
    ax4,
    itr,
    clr_group,
    ftan_pick=None,
    dist_km=None,
    GVnval=0,
    ax4_ccALPHAMAX=3e-5,
):
    """2. PLOT ATTENUATION MAIN: Draws attenuation across iterations.

    Connects all valid points with a dotted line and uses filled circles for
    high-quality picks (pick_q >= 0.75) and hollow circles for lower-quality
    picks (pick_q < 0.75).
    """
    # --- GROUP RELIABILITY (Attenuation -> Left Axis) ---
    if GVnval > 0 and ftan_pick is not None and dist_km is not None:
        period, alpha_app = group_amp2atten(ftan_pick, dist_km)
        pick_q = np.array(ftan_pick["pick_q"])

        # Filter out invalid / NaN points
        valid = (
            np.isfinite(period) & np.isfinite(alpha_app) & np.isfinite(pick_q)
        )
        p_valid, a_valid, q_valid = (
            period[valid],
            alpha_app[valid],
            pick_q[valid],
        )

        if len(a_valid) > 0:
            max_alpha = np.nanmax(a_valid)
            if max_alpha > ax4_ccALPHAMAX:
                ax4_ccALPHAMAX = max_alpha

            # 1. Line connects ALL points regardless of quality
            ax4.plot(
                p_valid,
                a_valid,
                ":",
                lw=1.3,
                c=clr_group[itr],
                zorder=10 - itr,
                label="_nolegend_",
            )

            # 2. Quality masks
            mask_hq = q_valid >= 0.75
            mask_lq = ~mask_hq

            # High-quality picks (>= 0.75): Filled circles
            if np.any(mask_hq):
                ax4.scatter(
                    p_valid[mask_hq],
                    a_valid[mask_hq],
                    c=clr_group[itr],
                    s=15,
                    marker="o",
                    zorder=10 - itr,
                    label="_nolegend_",
                )

            # Low-quality picks (< 0.75): Hollow circles (no fill)
            if np.any(mask_lq):
                ax4.scatter(
                    p_valid[mask_lq],
                    a_valid[mask_lq],
                    facecolors="none",
                    edgecolors=clr_group[itr],
                    linewidths=1.0,
                    s=15,
                    marker="o",
                    zorder=10 - itr,
                    label="_nolegend_",
                )

    # --- FAKE SCATTERS FOR PROGRESSIVE LEGEND CONSTRUCTION ---
    if itr == 0:
        ax4.scatter(
            [], [], color=clr_group[itr], marker="o", s=15, label="Average"
        )
    elif itr == 1:
        ax4.scatter(
            [], [], color=clr_group[itr], marker="o", s=15, label="Acausal side"
        )
    elif itr == 2:
        ax4.scatter(
            [], [], color=clr_group[itr], marker="o", s=15, label="Causal side"
        )

    return ax4_ccALPHAMAX


def plot_attenuation_embed(fig, ax4, cc, axes_dict, clr_group, ax4_ccALPHAMAX, dpi=96):
    """3. EMBED & FINALISE ATTENUATION GRAPHS: Sets standard tiered axis bounds,

    scale type (linear vs log), formats descriptions, places legend, and loads
    image into master canvas.
    """
    # Automatic Y-range and scale selection based on maximum alpha
    if ax4_ccALPHAMAX <= 3e-5:
        ax4.set_yscale("linear")
        ylim_range = (0.5e-5, 3e-5)
    elif ax4_ccALPHAMAX <= 5e-5:
        ax4.set_yscale("linear")
        ylim_range = (0.5e-5, 5e-5)
    elif ax4_ccALPHAMAX <= 1e-4:
        ax4.set_yscale("linear")
        ylim_range = (0.5e-5, 1e-4)
    elif ax4_ccALPHAMAX <= 1e-3:  # 10e-4 (1e-3)
        ax4.set_yscale("linear")
        ylim_range = (0.5e-4, 1e-3)
    else:
        ax4.set_yscale("linear")
        ylim_range = (0.5e-3, ax4_ccALPHAMAX)

    # Global visual layout styling
    ax4.set_xlim(0, 150)
    ax4.set_ylim(ylim_range)
    ax4.set_ylabel("Apparent Attenuation (1/m)")
    ax4.set_xlabel("Period (s)")
    ax4.set_title(f"Instantaneous amplitute measurement ({cc})")

    # Grid styling adapted for scale
    if ax4.get_yscale() == "log":
        ax4.grid(True, which="both", alpha=0.2)
    else:
        ax4.grid(True, which="major", alpha=0.2)

# Force scientific notation on y-axis for ALL powers of 10       
    ax4.ticklabel_format(style='sci', axis='y', scilimits=(0, 0), useMathText=True)       

    # Clean deduplicated legend with opaque white background frame
    h, l = zip(*dict(zip(*ax4.get_legend_handles_labels())).items())
    legend = ax4.legend(
        h,
        l,
        ncol=1,
        loc="upper right",
        fontsize=10,
        frameon=True,
        facecolor="white",
        framealpha=0.85,
    )
    legend.set_zorder(20)

    fig.tight_layout()

    # Determine master panel column path mapping targeting row 4
    grid_map = {"ZZ": "r4c1", "RR": "r4c2", "TT": "r4c3"}
    target_ax_name = grid_map.get(cc)

    if target_ax_name not in axes_dict:
        print(f"Error: Master Attenuation axis '{target_ax_name}' not found.")
        plt.close(fig)
        return

    # Render graphics array to buffer
    buf4 = io.BytesIO()
    fig.savefig(
        buf4, format="png", dpi=dpi, bbox_inches="tight", pad_inches=0.05
    )
    buf4.seek(0)
    img4 = plt.imread(buf4)

    ax_target = axes_dict[target_ax_name]
    ax_target.imshow(img4)
    ax_target.axis("off")

    # Cleanup memory
    del img4
    buf4.close()
    del buf4
    plt.close(fig)    
    

