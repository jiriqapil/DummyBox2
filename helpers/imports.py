# ==== imports.py ====

# =====================
# Standard library
# Config & System Environment
# =====================
import csv
import glob
import io
import itertools
import math
import os
import re
import shutil
import sqlite3
from datetime import datetime
import tarfile
import gc
import copy
import sys
import pathlib
from pathlib import Path
from dotenv import load_dotenv

# =====================
# Numerical / scientific
# =====================
import numpy as np

from math import (
    radians, degrees, cos, sin, sqrt,
    atan2, asin, fabs, pi
)

from scipy import interpolate, signal
from scipy.interpolate import interp1d, PchipInterpolator
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
from scipy.signal import freqz, savgol_filter
from scipy.special import jn_zeros, jv

# =====================
# Plotting
# =====================
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.lines as lines

from matplotlib import cm
from matplotlib.collections import PolyCollection
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Polygon
from matplotlib.transforms import offset_copy

from matplotlib.patches import FancyBboxPatch # Fake Legend (rounded corners)

# =====================
# Geospatial / mapping
# =====================
import pyproj
from netCDF4 import Dataset
from mpl_toolkits.basemap import Basemap

# =====================
# ObsPy (seismology)
# =====================
from obspy import read, Stream, UTCDateTime
from obspy.geodetics.base import gps2dist_azimuth as gps2dist
from obspy.signal.filter import envelope
# =====================
# Imaging
# =====================
from PIL import Image

### for instantaneous frequency
from scipy.signal import hilbert
from scipy.ndimage import gaussian_filter1d

