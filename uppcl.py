import gspread
from google.oauth2.service_account import Credentials
import base64
import uuid
from datetime import date, datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import pandas as pd
import streamlit as st
import cloudinary
import cloudinary.uploader
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="ddnuwaabx",
    api_key="562415167995455",
    api_secret="HUJR129f-F0vLKKyBn3Si-iyYAs"
)
def upload_to_cloudinary(uploaded_file):

    result = cloudinary.uploader.upload(uploaded_file)

    return result["secure_url"]

PHOTO_FOLDER_ID = "1XbY2-CUHa3TiIz_2JImoSpb60oae2fAj"

def upload_to_drive(uploaded_file):

    creds = Credentials.from_service_account_file(
        "service_account.json",
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    drive_service = build(
        "drive",
        "v3",
        credentials=creds
    )

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [PHOTO_FOLDER_ID]
    }

    file_stream = io.BytesIO(
        uploaded_file.getvalue()
    )

    media = MediaIoBaseUpload(
        file_stream,
        mimetype=uploaded_file.type,
        resumable=True
    )

    try:

        uploaded = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = uploaded.get("id")

        drive_service.permissions().create(
            fileId=file_id,
            body={
                "type": "anyone",
                "role": "reader"
            }
        ).execute()

        return f"https://drive.google.com/file/d/{file_id}/view"

    except Exception as e:

        st.error(str(e))
        raise

    file_id = uploaded.get("id")

    drive_service.permissions().create(
        fileId=file_id,
        body={
            "type": "anyone",
            "role": "reader"
        }
    ).execute()
    return f"https://drive.google.com/file/d/{file_id}/view"
 
st.set_page_config(page_title="Line Restoration Portal", layout="wide") 

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES

)
client = gspread.authorize(creds)

sheet = client.open_by_key("1J6YMS7jaCWp7K8rTnV281V09yCMsg7tiDOMzu8CQ880")

events_ws = sheet.worksheet("Events")
materials_ws = sheet.worksheet("Materials")
photos_ws = sheet.worksheet("Photos")
st.success("Google Sheet Connected Successfully")
VOLTAGES = ["132 kV", "220 kV", "400 kV"]
TOWER_TYPES = ["Suspension", "Tension", "Angle", "Dead End", "Special / River Crossing"]
STATUS = ["Reported", "Removal in Progress", "Removed", "Material Mobilized", "Erection in Progress", "Erected", "Stringing in Progress", "Restored / Charged"]
MATERIAL_TYPES = ["Tower", "Tension Fittings", "Suspension Fittings", "Conductor", "Mid Span Joint"]
UNITS = ["Nos", "Set", "Kg", "Meter", "Drum"]

# ------------------------ Session state ------------------------


# ------------------------ Helpers ------------------------
def new_id():
    return str(uuid.uuid4())[:8]

def event_label(e):
    return f"{e.get('event_name','Unnamed')} | {e.get('voltage','')} | {e.get('line_name','')} | Tower {e.get('tower_no','')}"

def get_event_options():
    return {event_label(e): e["id"] for e in events_ws.get_all_records()}

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

    events = events_ws.get_all_records()

    rows = []

    for v in VOLTAGES:
        ev = [e for e in events if e["voltage"] == v]

        rows.append({
            "Voltage": v,
            "Damaged Towers": len(ev),
            "Avg Removal %": round(
                sum(float(e.get("removal_progress", 0)) for e in ev) / len(ev), 1
            ) if ev else 0,
            "Avg Erection %": round(
                sum(float(e.get("erection_progress", 0)) for e in ev) / len(ev), 1
            ) if ev else 0,
            "Restored": len(
                [e for e in ev if e.get("status") == "Restored / Charged"]
            ),
        })

    df_dash = pd.DataFrame(rows)

    st.dataframe(
        df_dash,
        use_container_width=True,
        hide_index=True
    )

    c1, c2 = st.columns(2)

    with c1:
        st.bar_chart(
            df_dash.set_index("Voltage")[["Damaged Towers"]]
        )

    with c2:
        st.bar_chart(
            df_dash.set_index("Voltage")[["Avg Removal %", "Avg Erection %"]]
        )
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
        events_ws.append_row([
        new_id(),
        event_name or "Restoration Event",
        voltage,
        line_name,
        tower_no,
        tower_type,
        str(damage_date),
        location,
        status,
        removal_progress,
        erection_progress,
        remarks,
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ])

    st.success("Event saved successfully.")
    # st.rerun()

    st.markdown("### Existing Events")
    events = events_ws.get_all_records()

events = events_ws.get_all_records()

if len(events) > 0:
    for idx, e in enumerate(events):
        with st.expander(event_label(e)):
            c1, c2, c3 = st.columns(3)

            e["status"] = c1.selectbox(
                "Update Status",
                STATUS,
                index=STATUS.index(e.get("status", STATUS[0])),
                key=f"update_status_{e['id']}_{idx}"
            )

            e["removal_progress"] = c2.slider(
                "Update Removal %",
                0,
                100,
                int(e.get("removal_progress", 0)),
                key=f"update_removal_{e['id']}_{idx}"
            )

            e["erection_progress"] = c3.slider(
                "Update Erection %",
                0,
                100,
                int(e.get("erection_progress", 0)),
                key=f"update_erection_{e['id']}_{idx}"
            )

            e["remarks"] = st.text_area(
                "Update Remarks",
                e.get("remarks", ""),
                key=f"update_remarks_{e['id']}_{idx}"
            )

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
                mat_voltage = st.selectbox(
                    "Voltage",
                    VOLTAGES,
                    key="material_voltage_new"
                )

                mat_type = st.selectbox(
                    "Material Type",
                    MATERIAL_TYPES,
                    key="material_type_new"
                )

                description = st.text_input(
                    "Material Description",
                    key="material_desc_new"
                )

            with c2:
                required_qty = st.number_input(
                    "Required Quantity",
                    min_value=0.0,
                    step=1.0,
                    key="material_required_new"
                )

                available_qty = st.number_input(
                    "Available Quantity",
                    min_value=0.0,
                    step=1.0,
                    key="material_available_new"
                )

                unit = st.selectbox(
                    "Unit",
                    UNITS,
                    key="material_unit_new"
                )

            mat_submit = st.form_submit_button("Add Material")

            if mat_submit:
                shortage = max(required_qty - available_qty, 0)

                materials_ws.append_row([
                    new_id(),          # id
                    eid,               # event_id
                    mat_voltage,       # voltage
                    mat_type,          # material_type
                    description,       # description
                    required_qty,      # required_qty
                    available_qty,     # available_qty
                    shortage,          # shortage
                    unit               # unit
                ])

                st.success("Material entry saved.")

        st.markdown("### Material List for Selected Event")

        mats = [
            m for m in materials_ws.get_all_records()
            if str(m.get("event_id")) == str(eid)
        ]

        st.dataframe(
            as_dataframe(mats),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning("No event selected.")
# ------------------------ Photo Upload ------------------------
with tab_photo:

    st.subheader("Photographs of Each Event")

    eid = selected_event_id("photo")

    if eid:

        caption = st.text_input(
            "Photo Caption / Stage",
            placeholder="Before removal / During erection / After restoration",
            key="photo_caption_new"
        )

        uploaded_files = st.file_uploader(
            "Upload Photographs",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="photo_uploader_new"
        )

        if st.button("Save Photographs", key="save_photos_button"):

            if uploaded_files:

                for f in uploaded_files:

                    photo_url = upload_to_cloudinary(f)

                    photos_ws.append_row([
                        eid,
                        f.name,
                        caption,
                        photo_url,
                        datetime.now().strftime("%d-%m-%Y %H:%M")
                    ])

                st.success("Photographs uploaded successfully.")
                st.rerun()

            else:
                st.warning("Please select photographs first.") 
                st.markdown("### Uploaded Photographs")

photos = photos_ws.get_all_records()

cols = st.columns(3)

for i, p in enumerate(
    [x for x in photos if str(x.get("event_id")) == str(eid)]
):
    with cols[i % 3]:

        st.image(
            p["photo_url"],
            caption=f"{p['caption']} - {p['uploaded_at']}",
            use_container_width=True
        )   
# ------------------------ Report ------------------------
with tab_report:
    st.subheader("Consolidated Report")

    event_df = pd.DataFrame(events_ws.get_all_records())
    mat_df = pd.DataFrame(materials_ws.get_all_records())

    st.markdown("### Event Report")
    st.dataframe(event_df, use_container_width=True, hide_index=True)

    if not event_df.empty:
        st.download_button(
            "Download Event Report CSV",
            event_df.to_csv(index=False),
            "event_report.csv",
            "text/csv",
            key="download_event_csv"
        )

    st.markdown("### Material Report")
    st.dataframe(mat_df, use_container_width=True, hide_index=True)

    if not mat_df.empty:
        st.download_button(
            "Download Material Report CSV",
            mat_df.to_csv(index=False),
            "material_report.csv",
            "text/csv",
            key="download_material_csv"
        )

    st.success("Data is now being read from Google Sheets ✅")
