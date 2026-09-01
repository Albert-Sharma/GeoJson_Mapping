import io
import re

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from matplotlib.patches import Patch

matplotlib.use("Agg")

BASE_URL = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES"
HEADERS = {"User-Agent": "Mozilla/5.0"}

STATE_FOLDERS = {
    "Andhra Pradesh": "ANDHRA%20PRADESH",
    "Arunachal Pradesh": "ARUNACHAL%20PRADESH",
    "Assam": "ASSAM",
    "Bihar": "BIHAR",
    "Chhattisgarh": "CHHATTISGARH",
    "Goa": "GOA",
    "Gujarat": "GUJARAT",
    "Haryana": "HARYANA",
    "Himachal Pradesh": "HIMACHAL%20PRADESH",
    "Jharkhand": "JHARKHAND",
    "Karnataka": "KARNATAKA",
    "Kerala": "KERALA",
    "Madhya Pradesh": "MADHYA%20PRADESH",
    "Maharashtra": "MAHARASHTRA",
    "Manipur": "MANIPUR",
    "Meghalaya": "MEGHALAYA",
    "Mizoram": "MIZORAM",
    "Nagaland": "NAGALAND",
    "Odisha": "ODISHA",
    "Punjab": "PUNJAB",
    "Rajasthan": "RAJASTHAN",
    "Sikkim": "SIKKIM",
    "Tamil Nadu": "TAMIL%20NADU",
    "Telangana": "TELANGANA",
    "Tripura": "TRIPURA",
    "Uttar Pradesh": "UTTAR%20PRADESH",
    "Uttarakhand": "UTTARAKHAND",
    "West Bengal": "WEST%20BENGAL",
    "Delhi": "DELHI",
    "Jammu and Kashmir": "JAMMU%20AND%20KASHMIR",
}

ALIASES = {
    "CHINDWARA": "CHHINDWARA",
    "CHHINDWARA": "CHHINDWARA",
    "GONDIYA": "GONDIA",
}


def norm(name):
    n = str(name).strip().upper()
    return ALIASES.get(n, n)


def parse_districts(raw_text):
    if raw_text is None:
        return []
    cleaned = raw_text.replace(";", ",").replace("\n", ",")
    parts = [p.strip() for p in cleaned.split(",")]
    return [p for p in parts if p]


def build_state_url(state_name):
    folder = STATE_FOLDERS.get(state_name)
    if folder is None:
        folder = re.sub(r"\s+", "%20", state_name.upper())
    return f"{BASE_URL}/{folder}/{folder}_DISTRICTS.geojson"


@st.cache_data(show_spinner=False)
def load_state_data(state_name):
    url = build_state_url(state_name)
    response = requests.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()
    gdf = gpd.read_file(io.BytesIO(response.content))
    if gdf.empty:
        raise ValueError(f"No district data was returned for {state_name}.")
    return gdf


def find_name_col(gdf):
    candidates = [
        "dtname",
        "DISTRICT",
        "district",
        "NAME_2",
        "Dist_Name",
        "DIST_NAME",
        "name",
        "NAME",
        "District",
    ]
    for col in candidates:
        if col in gdf.columns:
            return col
    for col in gdf.columns:
        if gdf[col].dtype == object and col.lower() != "geometry":
            return col
    raise ValueError(f"No district-name column found. Available columns: {list(gdf.columns)}")


def generate_map(state_names, groups):
    frames = []
    for state_name in state_names:
        gdf = load_state_data(state_name)
        district_col = find_name_col(gdf)
        state_df = gdf.rename(columns={district_col: "district"})[["district", "geometry"]].copy()
        state_df["state"] = state_name
        frames.append(state_df)

    if not frames:
        raise ValueError("Please select at least one state.")

    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)

    district_color_map = {}
    for group in groups:
        for district in group["districts"]:
            district_color_map[norm(district)] = group["color"]

    def fill_for(row):
        key = norm(row["district"])
        return district_color_map.get(key, "#d9d9d9")

    combined["fill"] = combined.apply(fill_for, axis=1)
    highlighted = set(district_color_map.keys())

    fig, ax = plt.subplots(figsize=(16, 16))
    combined.plot(ax=ax, color=combined["fill"], edgecolor="#444444", linewidth=0.6)

    state_borders = combined.dissolve(by="state")
    state_borders.boundary.plot(ax=ax, color="black", linewidth=2.5)

    for _, row in combined.iterrows():
        centroid = row.geometry.representative_point()
        is_highlighted = norm(row["district"]) in highlighted
        ax.annotate(
            row["district"],
            xy=(centroid.x, centroid.y),
            ha="center",
            va="center",
            fontsize=6.5 if is_highlighted else 6,
            color="white" if is_highlighted else "black",
            fontweight="bold" if is_highlighted else "normal",
        )

    ax.set_title(f"District Map — {', '.join(state_names)}", fontsize=18, fontweight="bold")
    ax.axis("off")

    legend_elements = [
        Patch(facecolor=group["color"], edgecolor="#444444", label=group["label"])
        for group in groups
        if group["districts"]
    ]
    if legend_elements:
        ax.legend(handles=legend_elements, loc="lower left", fontsize=11, frameon=True)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf, combined, highlighted


st.set_page_config(page_title="District Map Generator", layout="wide")
st.title("District Map Generator")
st.caption("Choose states, define district groups, assign colors, and download the final image.")

with st.sidebar:
    st.header("Map settings")
    state_options = sorted(STATE_FOLDERS.keys())
    selected_states = st.multiselect(
        "Select states",
        state_options,
        default=["Madhya Pradesh", "Maharashtra"],
    )

    group_count = st.slider("How many district groups?", min_value=1, max_value=5, value=2)

    groups = []
    for i in range(group_count):
        st.subheader(f"Group {i + 1}")
        label = st.text_input(f"Group {i + 1} label", value=f"Group {i + 1}", key=f"label_{i}")
        color = st.color_picker(f"Color for Group {i + 1}", value="#1b5e20", key=f"color_{i}")
        district_text = st.text_area(
            f"District names for Group {i + 1}",
            height=120,
            value="",
            key=f"districts_{i}",
            help="Enter district names separated by commas, semicolons, or new lines.",
        )
        groups.append({
            "label": label,
            "color": color,
            "districts": parse_districts(district_text),
        })

    st.markdown("---")
    st.caption("The app builds the RAW GeoJSON URL from the selected state name and the source folder list.")

if not selected_states:
    st.warning("Please choose at least one state to continue.")
    st.stop()

if st.button("Generate district map", type="primary"):
    non_empty_groups = [group for group in groups if group["districts"]]
    if not non_empty_groups:
        st.warning("Add at least one district name in one of the groups before generating the map.")
        st.stop()

    with st.spinner("Downloading district boundaries and rendering the map..."):
        try:
            image_buffer, combined_df, highlighted = generate_map(selected_states, non_empty_groups)
        except Exception as exc:
            st.error(f"Something went wrong while fetching or plotting the map: {exc}")
            st.stop()

    st.success("Map generated successfully.")
    st.image(image_buffer, caption="District map preview", use_container_width=True)

    all_group_names = {norm(d) for group in non_empty_groups for d in group["districts"]}
    dataset_names = {norm(value) for value in combined_df["district"].tolist()}
    missing = sorted({name for name in all_group_names if name not in dataset_names})
    if missing:
        st.warning("These district names were not found in the selected state data: " + ", ".join(missing[:20]))

    image_buffer.seek(0)
    file_name = "_".join(state.lower().replace(" ", "_") for state in selected_states) + "_district_map.png"
    st.download_button(
        label="Download PNG",
        data=image_buffer.getvalue(),
        file_name=file_name,
        mime="image/png",
    )

else:
    st.info("Set your state and district groups on the left, then click Generate district map.")
