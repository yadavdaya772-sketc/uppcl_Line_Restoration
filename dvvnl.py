import base64
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Line Restoration Portal", layout="wide")

VOLTAGES = ["132 kV", "220 kV", "400 kV"]
TOWER_TYPES = ["Suspension", "Tension", "Angle", "Dead End", "Special / River Crossing"]
STATUS = ["Reported", "Removal in Progress", "Removed", "Material Mobilized", "Erection in Progress", "Erected", "Stringing in Progress", "Restored / Charged"]
MATERIAL_TYPES = ["Tower", "Tension Fittings", "Suspension Fittings", "Conductor", "Mid Span Joint"]
UNITS = ["Nos", "Set", "Kg", "Meter", "Drum"]

# ------------------------ Session state ------------------------
if "events" not in st.session_state:
    st.session_state.events = []
if "materials" not in st.session_state:
    st.session_state.materials = []
if "photos" not in st.session_state:
    st.session_state.photos = []

# ------------------------ Helpers ------------------------
def new_id():
    return str(uuid.uuid4())[:8]

def event_label(e):
    return f"{e.get('event_name','Unnamed')} | {e.get('voltage','')} | {e.get('line_name','')} | Tower {e.get('tower_no','')}"

def get_event_options():
    return {event_label(e): e["id"] for e in st.session_state.events}

def selected_event_id(prefix):
    options = get_event_options()
    if not options:
        st.info("Please create one event first from Event Entry tab.")
        return None
    label = st.selectbox("Select Event", list(options.keys()), key=f"{prefix}_select_event")
    return options[label]

def file_to_b64(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

def as_dataframe(rows):
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ------------------------ Header ------------------------
st.title("Tower Damage & Restoration Monitoring System")
st.caption("For voltage-wise monitoring of tower damage, removal, material requirement, erection progress and site photographs.")

tab_dashboard, tab_event, tab_material, tab_photo, tab_report = st.tabs([
    "Dashboard", "Event Entry", "Material Entry", "Photos", "Report"
])

# ------------------------ Dashboard ------------------------
with tab_dashboard:
    st.subheader("Voltage-wise Dashboard")
    rows = []
    for v in VOLTAGES:
        ev = [e for e in st.session_state.events if e["voltage"] == v]
        rows.append({
            "Voltage": v,
            "Damaged Towers": len(ev),
            "Avg Removal %": round(sum(e.get("removal_progress", 0) for e in ev) / len(ev), 1) if ev else 0,
            "Avg Erection %": round(sum(e.get("erection_progress", 0) for e in ev) / len(ev), 1) if ev else 0,
            "Restored": len([e for e in ev if e.get("status") == "Restored / Charged"]),
        })
    df_dash = pd.DataFrame(rows)
    st.dataframe(df_dash, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.bar_chart(df_dash.set_index("Voltage")[["Damaged Towers"]])
    with c2:
        st.bar_chart(df_dash.set_index("Voltage")[["Avg Removal %", "Avg Erection %"]])

# ------------------------ Event Entry ------------------------
with tab_event:
    st.subheader("Event Entry - Damaged Tower Details")
    with st.form("event_entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            event_name = st.text_input("Event Name", key="event_name_new")
            voltage = st.selectbox("Voltage", VOLTAGES, key="event_voltage_new")
            line_name = st.text_input("Line Name", key="event_line_new")
            tower_no = st.text_input("Tower Number", key="event_tower_no_new")
            tower_type = st.selectbox("Type of Tower Damaged", TOWER_TYPES, key="event_tower_type_new")
        with c2:
            damage_date = st.date_input("Date of Damage", value=date.today(), key="event_damage_date_new")
            location = st.text_input("Location / Village / District", key="event_location_new")
            status = st.selectbox("Current Status", STATUS, key="event_status_new")
            removal_progress = st.slider("Damaged Tower Removal Progress (%)", 0, 100, 0, key="event_removal_new")
            erection_progress = st.slider("Erection Progress (%)", 0, 100, 0, key="event_erection_new")
        remarks = st.text_area("Remarks", key="event_remarks_new")
        submitted = st.form_submit_button("Save Event")
        if submitted:
            st.session_state.events.append({
                "id": new_id(),
                "event_name": event_name or "Restoration Event",
                "voltage": voltage,
                "line_name": line_name,
                "tower_no": tower_no,
                "tower_type": tower_type,
                "damage_date": str(damage_date),
                "location": location,
                "status": status,
                "removal_progress": removal_progress,
                "erection_progress": erection_progress,
                "remarks": remarks,
                "created_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
            })
            st.success("Event saved successfully.")

    st.markdown("### Existing Events")
    if st.session_state.events:
        for idx, e in enumerate(st.session_state.events):
            with st.expander(event_label(e)):
                c1, c2, c3 = st.columns(3)
                e["status"] = c1.selectbox("Update Status", STATUS, index=STATUS.index(e.get("status", STATUS[0])), key=f"update_status_{e['id']}_{idx}")
                e["removal_progress"] = c2.slider("Update Removal %", 0, 100, int(e.get("removal_progress", 0)), key=f"update_removal_{e['id']}_{idx}")
                e["erection_progress"] = c3.slider("Update Erection %", 0, 100, int(e.get("erection_progress", 0)), key=f"update_erection_{e['id']}_{idx}")
                e["remarks"] = st.text_area("Update Remarks", e.get("remarks", ""), key=f"update_remarks_{e['id']}_{idx}")
                if st.button("Delete Event", key=f"delete_event_{e['id']}_{idx}"):
                    eid = e["id"]
                    st.session_state.events = [x for x in st.session_state.events if x["id"] != eid]
                    st.session_state.materials = [x for x in st.session_state.materials if x["event_id"] != eid]
                    st.session_state.photos = [x for x in st.session_state.photos if x["event_id"] != eid]
                    st.rerun()
    else:
        st.warning("No event added yet.")

# ------------------------ Material Entry ------------------------
with tab_material:
    st.subheader("Material Requirement")
    eid = selected_event_id("material")
    if eid:
        with st.form("material_entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                # Unique keys added to avoid StreamlitDuplicateElementId
                mat_voltage = st.selectbox("Voltage", VOLTAGES, key="material_voltage_new")
                mat_type = st.selectbox("Material Type", MATERIAL_TYPES, key="material_type_new")
                description = st.text_input("Material Description", key="material_desc_new")
            with c2:
                required_qty = st.number_input("Required Quantity", min_value=0.0, step=1.0, key="material_required_new")
                available_qty = st.number_input("Available Quantity", min_value=0.0, step=1.0, key="material_available_new")
                unit = st.selectbox("Unit", UNITS, key="material_unit_new")
            mat_submit = st.form_submit_button("Add Material")
            if mat_submit:
                st.session_state.materials.append({
                    "id": new_id(),
                    "event_id": eid,
                    "voltage": mat_voltage,
                    "material_type": mat_type,
                    "description": description,
                    "required_qty": required_qty,
                    "available_qty": available_qty,
                    "shortage": max(required_qty - available_qty, 0),
                    "unit": unit,
                })
                st.success("Material entry saved.")

        st.markdown("### Material List for Selected Event")
        mats = [m for m in st.session_state.materials if m["event_id"] == eid]
        st.dataframe(as_dataframe(mats), use_container_width=True, hide_index=True)

# ------------------------ Photo Upload ------------------------
with tab_photo:
    st.subheader("Photographs of Each Event")
    eid = selected_event_id("photo")
    if eid:
        caption = st.text_input("Photo Caption / Stage", placeholder="Before removal / During erection / After restoration", key="photo_caption_new")
        uploaded_files = st.file_uploader(
            "Upload Photographs",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="photo_uploader_new"
        )
        if st.button("Save Photographs", key="save_photos_button"):
            if uploaded_files:
                for f in uploaded_files:
                    st.session_state.photos.append({
                        "id": new_id(),
                        "event_id": eid,
                        "name": f.name,
                        "caption": caption,
                        "data": file_to_b64(f),
                        "uploaded_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    })
                st.success("Photographs uploaded successfully.")
            else:
                st.warning("Please select photographs first.")

        st.markdown("### Uploaded Photographs")
        cols = st.columns(3)
        for i, p in enumerate([x for x in st.session_state.photos if x["event_id"] == eid]):
            with cols[i % 3]:
                st.image(base64.b64decode(p["data"]), caption=f"{p['caption']} - {p['uploaded_at']}", use_container_width=True)

# ------------------------ Report ------------------------
with tab_report:
    st.subheader("Consolidated Report")
    event_df = as_dataframe(st.session_state.events)
    mat_df = as_dataframe(st.session_state.materials)

    st.markdown("### Event Report")
    st.dataframe(event_df, use_container_width=True, hide_index=True)
    if not event_df.empty:
        st.download_button("Download Event Report CSV", event_df.to_csv(index=False), "event_report.csv", "text/csv", key="download_event_csv")

    st.markdown("### Material Report")
    st.dataframe(mat_df, use_container_width=True, hide_index=True)
    if not mat_df.empty:
        st.download_button("Download Material Report CSV", mat_df.to_csv(index=False), "material_report.csv", "text/csv", key="download_material_csv")

    st.info("Note: This version stores entries in Streamlit session memory. For permanent multi-user departmental use, connect it with Google Sheets, SQLite, PostgreSQL or Firebase.")
