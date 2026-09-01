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

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(16, 16))

    colors = {"Madhya Pradesh": "#e8f4e0", "Maharashtra": "#fdf0e0"}
    for state, grp in both.groupby("state"):
        grp.plot(ax=ax, color=colors[state], edgecolor="#444444", linewidth=0.6)

    # District name labels at polygon centroids
    for _, row in both.iterrows():
        c = row.geometry.representative_point()
        ax.annotate(row["district"], xy=(c.x, c.y),
                    ha="center", va="center", fontsize=6, color="black")

    ax.set_title("District Map — Madhya Pradesh & Maharashtra",
                 fontsize=18, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("mp_mh_districts.png", dpi=300, bbox_inches="tight")
    print("Saved: mp_mh_districts.png")


if __name__ == "__main__":
    main()
