"""
Accurate district map of Madhya Pradesh + Maharashtra
-----------------------------------------------------
Renders both states together with district boundaries and district names,
using REAL GIS boundary data (open-source, WGS84 / EPSG:4326).

Run locally (needs internet the first time to fetch the boundaries):

    pip install geopandas matplotlib requests
    python mp_mh_district_map.py

Output: mp_mh_districts.png  (300 DPI)

Data source: https://github.com/datta07/INDIAN-SHAPEFILES  (state-wise district GeoJSON)
"""

import io
import requests
import geopandas as gpd
import matplotlib.pyplot as plt

# Raw GeoJSON URLs (state-wise district polygons)
BASE = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES"
SOURCES = {
    "Madhya Pradesh": f"{BASE}/MADHYA%20PRADESH/MADHYA%20PRADESH_DISTRICTS.geojson",
    "Maharashtra":    f"{BASE}/MAHARASHTRA/MAHARASHTRA_DISTRICTS.geojson",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -------------------------------------------------------------------
# HIGHLIGHT SETS  (edit these lists freely)
# Matching is case/space-insensitive, so spelling variants are handled
# by the ALIASES map below (e.g. "Chindwara" -> "CHHINDPARA").
# -------------------------------------------------------------------
DARK_GREEN = [
    # Madhya Pradesh
    "Seoni", "Balaghat", "Mandla", "Dindori", "Betul", "Chhindwara",
    # Maharashtra
    "Bhandara", "Gondia", "Gadchiroli", "Chandrapur", "Nagpur",
]

WINE_RED = [
    "Jabalpur", "Sagar", "Katni", "Panna", "Satna", "Rewa",
    "Shahdol", "Anuppur", "Umaria", "Sidhi", "Damoh", "Narsinghpur",
]

DARK_GREEN_COLOR = "#1b5e20"   # dark green
WINE_RED_COLOR   = "#7b1e2b"   # wine red

# Handle common spelling differences between your list and the dataset.
ALIASES = {
    "CHINDWARA": "CHHINDWARA",
    "CHHINDWARA": "CHHINDWARA",
    "GONDIYA": "GONDIA",
}


def norm(name):
    n = str(name).strip().upper()
    return ALIASES.get(n, n)


def load_state(url):
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    return gpd.read_file(io.BytesIO(r.content))


def find_name_col(gdf):
    """Auto-detect the column that holds the district name."""
    candidates = ["dtname", "DISTRICT", "district", "NAME_2", "Dist_Name",
                  "DIST_NAME", "name", "NAME", "District"]
    for c in candidates:
        if c in gdf.columns:
            return c
    # fallback: first string/object column
    for c in gdf.columns:
        if gdf[c].dtype == object and c.lower() != "geometry":
            return c
    raise ValueError(f"No name column found. Columns: {list(gdf.columns)}")


def main():
    frames = []
    for state, url in SOURCES.items():
        gdf = load_state(url)
        col = find_name_col(gdf)
        gdf = gdf.rename(columns={col: "district"})[["district", "geometry"]]
        gdf["state"] = state
        frames.append(gdf)

    import pandas as pd
    both = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)

    # ---- Assign fill colour per district ----
    green = {norm(x) for x in DARK_GREEN}
    red = {norm(x) for x in WINE_RED}
    GREY_FILL = "#c8c8c8"   # all non-highlighted districts

    def fill_for(row):
        key = norm(row["district"])
        if key in green:
            return DARK_GREEN_COLOR
        if key in red:
            return WINE_RED_COLOR
        return GREY_FILL

    both["fill"] = both.apply(fill_for, axis=1)
    highlighted = green | red

    # Sanity check: warn about any names that didn't match the dataset
    dataset_names = {norm(n) for n in both["district"]}
    for label, wanted in [("DARK_GREEN", green), ("WINE_RED", red)]:
        missing = wanted - dataset_names
        if missing:
            print(f"[WARN] {label} not matched in data: {sorted(missing)}")

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(16, 16))
    both.plot(ax=ax, color=both["fill"], edgecolor="#444444", linewidth=0.6)

    # Thick black outline around each STATE boundary
    state_borders = both.dissolve(by="state")
    state_borders.boundary.plot(ax=ax, color="black", linewidth=2.5)

    # District name labels (white on highlighted, black elsewhere)
    for _, row in both.iterrows():
        c = row.geometry.representative_point()
        is_hi = norm(row["district"]) in highlighted
        ax.annotate(
            row["district"], xy=(c.x, c.y), ha="center", va="center",
            fontsize=6.5 if is_hi else 6,
            color="white" if is_hi else "black",
            fontweight="bold" if is_hi else "normal",
        )

    ax.set_title("District Map — Madhya Pradesh & Maharashtra",
                 fontsize=18, fontweight="bold")

    # Legend
    from matplotlib.patches import Patch
    legend = [
        Patch(facecolor=DARK_GREEN_COLOR, edgecolor="#444", label="Dark green set"),
        Patch(facecolor=WINE_RED_COLOR, edgecolor="#444", label="Wine red set"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=11, frameon=True)

    ax.axis("off")
    plt.tight_layout()
    plt.savefig("up_districts.png", dpi=300, bbox_inches="tight")
    print("Saved: up_districts.png")


if __name__ == "__main__":
    main()
