"""Data file paths for PL7 binary data."""
import os

PL7_BIN = os.path.join(os.path.dirname(__file__), "..", "GeoVision", "PL7", "Bin")

EPHEMDAT_PATH = os.path.join(PL7_BIN, "ephemdat.bin")
APPROX_PATH = os.path.join(PL7_BIN, "APPROX.DAT")
DELTAT_PATH = os.path.join(PL7_BIN, "DELTAT.ASC")
JUNCTION_PATH = os.path.join(PL7_BIN, "JUNCTION.DAT")
DE440_PATH = os.path.join(PL7_BIN, "de440.bsp")

# Normalize paths
for _attr in ["EPHEMDAT_PATH", "APPROX_PATH", "DELTAT_PATH", "JUNCTION_PATH", "DE440_PATH"]:
    globals()[_attr] = os.path.normpath(globals()[_attr])
