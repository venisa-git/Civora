from difflib import SequenceMatcher
import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import folium
from streamlit_folium import st_folium

DATA_FILE = "complaints.json"

st.set_page_config(
    page_title="CiviFix | From Complaints to Action",
    page_icon="🏙️",
    layout="wide"
)




st.markdown("""
<style>
    /* ===== MAIN APPLICATION ===== */
    .stApp {
        background-color: #FFF5F3;
        color: #49313B;
    }

    /* ===== HEADINGS ===== */
    h1, h2, h3 {
        color: #512638 !important;
        font-family: Arial, sans-serif;
        font-weight: 700;
    }

    p, label, .stMarkdown {
        color: #49313B;
    }

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background-color: #512638;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #FFFFFF !important;
    }

    /* Sidebar navigation */
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        color: #FFFFFF !important;
    }

    /* ===== METRIC CARDS ===== */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DDE2;
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 3px 12px rgba(81, 38, 56, 0.06);
    }

    div[data-testid="stMetric"] label {
        color: #795968 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #963F5C !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button,
    .stFormSubmitButton > button {
        background-color: #963F5C;
        color: #FFFFFF !important;
        border: 1px solid #963F5C;
        border-radius: 9px;
        font-weight: 600;
        transition: background-color 0.2s ease;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #783149;
        border-color: #783149;
        color: #FFFFFF !important;
    }

    /* ===== INPUT FIELDS ===== */
    input, textarea {
        background-color: #FFFFFF !important;
        color: #49313B !important;
        border-color: #E8C9D1 !important;
    }

    /* ===== SELECT BOXES ===== */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF;
        border-color: #E8C9D1;
    }

    div[data-baseweb="select"] * {
        color: #49313B !important;
    }

    /* ===== DATA TABLE ===== */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DDE2;
        border-radius: 12px;
        overflow: hidden;
    }

    /* ===== FORM CONTAINERS ===== */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DDE2;
        padding: 20px;
        border-radius: 14px;
    }

    /* ===== DIVIDERS ===== */
    hr {
        border-color: #E8C9D1;
    }

    /* ===== LINKS ===== */
    a {
        color: #963F5C !important;
    }

</style>
""", unsafe_allow_html=True)





def load_complaints():
    if not os.path.exists(DATA_FILE):
        return {"complaints": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_complaints(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_id(complaints):
    if not complaints:
        return "CL001"
    nums = []
    for c in complaints:
        try:
            nums.append(int(str(c["complaint_id"]).replace("CL", "")))
        except:
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"CL{next_num:03d}"

def analyze_complaint(description, location):
    text = (str(description) + " " + str(location)).lower()

    if any(w in text for w in ["water", "flood", "waterlog", "rain", "drain", "sewage"]):
        category = "Waterlogging"
    elif any(w in text for w in ["road", "pothole", "damage", "crack", "street", "asphalt"]):
        category = "Road Damage"
    elif any(w in text for w in ["garbage", "waste", "bin", "trash", "overflow", "dump"]):
        category = "Garbage Overflow"
    elif any(w in text for w in ["light", "streetlight", "lamp", "dark", "bulb"]):
        category = "Broken Streetlight"
    elif any(w in text for w in ["manhole", "open hole", "cover missing"]):
        category = "Open Manhole"
    else:
        category = "Other"

    high_keywords = ["flood", "waterlog", "manhole", "electric", "danger", "accident", "school", "children", "urgent", "safety", "fire", "exposed"]
    medium_keywords = ["garbage", "overflow", "pothole", "streetlight", "damage", "blocked", "broken"]

    if any(w in text for w in high_keywords):
        priority = "High"
        reason = "High priority because it poses a safety risk or urgent public hazard."
    elif any(w in text for w in medium_keywords):
        priority = "Medium"
        reason = "Medium priority as it affects daily life and convenience of citizens."
    else:
        priority = "Low"
        reason = "Low priority – routine maintenance issue."

    summary = str(description).strip()
    if len(summary) > 90:
        summary = summary[:87] + "..."

    return {
        "category": category,
        "summary": summary,
        "priority": priority,
        "reason": reason
    }

def find_possible_duplicates(description, location, category, complaints):
    possible_duplicates = []

    new_description = str(description).lower().strip()
    new_location = str(location).lower().strip()

    for complaint in complaints:
        old_description = str(complaint.get("description", "")).lower().strip()
        old_location = str(complaint.get("location", "")).lower().strip()

        old_category = complaint.get("category", "")

        similarity = SequenceMatcher(
            None, new_description, old_description
        ).ratio()

        same_location = new_location == old_location

        if old_category == category and (
            similarity >= 0.70 or (same_location and similarity >= 0.45)
        ):
            possible_duplicates.append({
                "complaint_id": complaint.get("complaint_id"),
                "location": complaint.get("location"),
                "similarity": round(similarity * 100)
            })

    return possible_duplicates


data = load_complaints()
complaints = data.get("complaints", [])

# Top Navigation
st.markdown("""
<div style="padding: 10px 0 5px 0;">
    <h1 style="color:#512638; margin-bottom:0;">🏙️ Civora</h1>
    <p style="color:#795968; margin-top:0;">
        Every Voice. One Connected Action.
    </p>
</div>
""", unsafe_allow_html=True)

page = st.radio(
    "Navigation",
    ["Home", "Submit Complaint", "Admin Dashboard", "Track Complaint", "About"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

if page == "Home":
    st.markdown("""
    <div style="
        background: linear-gradient(120deg, #512638, #963F5C);
        padding: 35px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
    ">
        <h1 style="color: #FFFFFF !important; font-size: 42px; font-weight: 800;">
           Welcome to Civora
        </h1>
        <h3 style="color:#FFE5EB !important;">
            Turning Citizen Complaints Into Real Action.
        </h3>
        <p style="color:white !important;">
            A smarter way to report civic problems, identify urgent
            issues and track their progress.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Civic Overview")

    total = len(complaints)
    high = sum(1 for c in complaints if c.get("priority") == "High")
    resolved = sum(1 for c in complaints if c.get("status") == "Resolved")
    pending = total - resolved

    a, b, c, d = st.columns(4)

    a.metric("Total Reports", total)
    b.metric("High Priority", high)
    c.metric("Resolved", resolved)
    d.metric("Pending", pending)

    st.divider()

    st.subheader("How Civora Works")

    x, y, z = st.columns(3)

    with x:
        st.markdown("### 📢 Report")
        st.write("Citizens submit civic complaints with descriptions and locations.")

    with y:
        st.markdown("### 🧠 Analyse")
        st.write("Rule-based analysis categorizes complaints and identifies priority and possible duplicates.")

    with z:
        st.markdown("### 📍 Track")
        st.write("Administrators manage complaint status while citizens track progress.")

    st.divider()
        # Recent Complaints
    st.subheader("Recent Complaints")

    if complaints:
        recent = sorted(
            complaints,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[:5]

        for complaint in recent:
            with st.container(border=True):
                st.write(f"**{complaint.get('complaint_id', 'N/A')}**")
                st.write(complaint.get("description", "No description"))
                st.caption(
                    f"Priority: {complaint.get('priority', 'N/A')} | "
                    f"Status: {complaint.get('status', 'N/A')}"
                )
    else:
        st.info("No complaints submitted yet.")

    st.divider()

    st.subheader("Our Mission")
    st.write(
        "Civora aims to make civic issue reporting more transparent, "
        "organized and actionable by connecting citizen reports "
        "with a clear complaint management workflow."
    )

elif page == "Submit Complaint":
    st.title("📢 Submit a Civic Complaint")
    st.write("Report problems like waterlogging, damaged roads, garbage, broken lights etc.")

    with st.form("complaint_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your Name")
            phone = st.text_input("Phone Number")
        with col2:
            location = st.text_input("Location / Landmark / Address")
            category_choice = st.selectbox("Category (optional)", [
                "Auto-detect", "Waterlogging", "Road Damage", "Garbage Overflow",
                "Broken Streetlight", "Drainage Blockage", "Open Manhole", "Other"
            ])

        description = st.text_area("Describe the problem clearly", height=130)


        col3, col4 = st.columns(2)
        with col3:
            lat = st.number_input("Latitude", value=12.9716, format="%.6f")
        with col4:
            lon = st.number_input("Longitude", value=77.5946, format="%.6f")

        submitted = st.form_submit_button("🚀 Submit Complaint", use_container_width=True)

        if submitted:
            if not description or not location:
                st.error("Please fill both Description and Location.")
            else:
                analysis = analyze_complaint(description, location)
                if category_choice != "Auto-detect":
                    analysis["category"] = category_choice
                duplicates = find_possible_duplicates(
                    description,
                    location,
                    analysis["category"],
                    complaints
                )

                new_id = generate_id(complaints)

                new_complaint = {
                    "complaint_id": new_id,
                    "name": name or "Anonymous",
                    "phone": phone or "Not provided",
                    "description": description,
                    "category": analysis["category"],
                    "summary": analysis["summary"],
                    "priority": analysis["priority"],
                    "reason": analysis["reason"],
                    "location": location,
                    "latitude": lat,
                    "longitude": lon,
                    "status": "Received",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                }

                complaints.append(new_complaint)
                data["complaints"] = complaints
                save_complaints(data)

                st.success(f"Complaint submitted successfully! Your Report ID is **{new_id}**")
                st.balloons()

                if duplicates:
                    st.warning("⚠️ Possible duplicate complaints detected!")

                    for duplicate in duplicates:
                        st.write(
                            f"Possible match: {duplicate['complaint_id']} | "
                            f"Location: {duplicate['location']} | "
                            f"Similarity: {duplicate['similarity']}%"
                        )
                else:
                    st.success("No similar complaints detected.")

                st.subheader("AI Analysis")
                c1, c2, c3 = st.columns(3)
                c1.metric("Priority", analysis["priority"])
                c2.metric("Category", analysis["category"])
                c3.metric("Report ID", new_id)

                st.markdown(f"**Summary:** {analysis['summary']}")
                st.info(f"**Why this priority?** {analysis['reason']}")
                st.warning("Please save your Report ID to track progress later.")


elif page == "Admin Dashboard":
    st.title("🛡️ Admin Dashboard")
    st.caption("All complaints sorted by priority (High → Medium → Low)")

    if not complaints:
        st.warning("No complaints in the system yet.")
    else:
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_complaints = sorted(complaints, key=lambda x: priority_order.get(x.get("priority", "Low"), 3))

        high = sum(1 for c in complaints if c.get("priority") == "High")
        medium = sum(1 for c in complaints if c.get("priority") == "Medium")
        low = sum(1 for c in complaints if c.get("priority") == "Low")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Complaints", len(complaints))
        m2.metric("High Priority", high)
        m3.metric("Medium Priority", medium)
        
        m4.metric("Low Priority", low)

        st.divider()

        # Complaint Analytics
        st.subheader("📊 Complaint Analytics")

        priority_counts = pd.Series(
            [c.get("priority", "Low") for c in complaints]
        ).value_counts().reindex(
            ["High", "Medium", "Low"], fill_value=0
        )

        status_counts = pd.Series(
            [c.get("status", "Received") for c in complaints]
        ).value_counts().reindex(
            ["Received", "Assigned", "In Progress", "Resolved"],
            fill_value=0
        )

        chart1, chart2 = st.columns(2)

        with chart1:
            st.markdown("**Complaints by Priority**")
            st.bar_chart(priority_counts)

        with chart2:
            st.markdown("**Complaints by Status**")
            st.bar_chart(status_counts)

        st.divider()

        df = pd.DataFrame(sorted_complaints)

        show_cols = ["complaint_id", "priority", "category", "status", "location", "summary"]
        available_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, height=380)

        st.subheader("Update Complaint Status")
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            selected_id = st.selectbox("Select Complaint", [c["complaint_id"] for c in sorted_complaints])
        with col_b:
            new_status = st.selectbox("New Status", ["Received", "Assigned", "In Progress", "Resolved"])
        with col_c:
            st.write("")
            st.write("")
            if st.button("Update", use_container_width=True):
                for c in complaints:
                    if c["complaint_id"] == selected_id:
                        c["status"] = new_status
                        break
                data["complaints"] = complaints
                save_complaints(data)
                st.success(f"Updated {selected_id} → {new_status}")
                st.rerun()

        
        st.subheader("Complaints Map")

        m = folium.Map(location=[12.97, 77.59], zoom_start=12)

        color_map = {
            "High": "red",
            "Medium": "orange",
            "Low": "green"
        }

        plotted_count = 0
        missing_location_count = 0

        for c in complaints:

            location_data = c.get("location", {})

            if isinstance(location_data, dict):
                lat = c.get("latitude", location_data.get("latitude"))
                lon = c.get("longitude", location_data.get("longitude"))
            else:
                lat = c.get("latitude")
                lon = c.get("longitude")

            if lat is None or lon is None:
                missing_location_count += 1
                continue

            try:
                lat = float(lat)
                lon = float(lon)

                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    missing_location_count += 1
                    continue

            except (ValueError, TypeError):
                missing_location_count += 1
                continue

            color = color_map.get(c.get("priority", "Low"), "blue")

            folium.Marker(
                [lat, lon],
                popup=f"{c['complaint_id']} | {c.get('priority')} | {c.get('category')}",
                tooltip=f"{c['complaint_id']} ({c.get('priority')})",
                icon=folium.Icon(color=color)
            ).add_to(m)

            plotted_count += 1

        st_folium(m, width=None, height=420)

        st.caption(f"Complaints plotted on map: {plotted_count}")
        st.caption(f"Complaints with missing or invalid coordinates: {missing_location_count}")


elif page == "Track Complaint":
    st.title("Track Your Complaint")
    st.write("Enter your Report ID to see current status and details.")

    track_id = st.text_input("Report ID (example: CL001)", placeholder="CL001")

    if st.button("Track Now", type="primary"):
        if track_id.strip():
            found = None
            for c in complaints:
                if str(c["complaint_id"]).lower() == track_id.strip().lower():
                    found = c
                    break

            if found:
                st.success(f"Found: **{found['complaint_id']}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", found.get("status", "Received"))
                col2.metric("Priority", found.get("priority", "N/A"))
                col3.metric("Category", found.get("category", "N/A"))

                st.write(f"**Summary:** {found.get('summary', found.get('description', 'N/A'))}")
                st.write(f"**Location:** {found.get('location', 'N/A')}")
                st.write(f"**Why this priority:** {found.get('reason', 'N/A')}")
                st.write(f"**Submitted on:** {found.get('created_at', 'N/A')}")
            else:
                st.error("No complaint found with this ID.")

elif page == "About":
    st.title("About CiviFix")
    st.write("CiviFix turns scattered citizen complaints into prioritized, explainable and trackable action.")
    st.write("### What this prototype does")
    st.write("- Citizens can submit complaints quickly")
    st.write("- AI automatically categorizes, summarizes and assigns priority with a clear reason")
    st.write("- Officers see all complaints sorted by urgency on a dashboard + map")
    st.write("- Status can be updated and citizens can track progress using Report ID")
    st.write("### Tech Stack")
    st.write("- Streamlit + Pandas + Folium")
    st.write("- Data stored in JSON file")
    st.write("- Rule-based AI for prioritization")

st.sidebar.markdown("---")
st.sidebar.caption("Built for PromptWars x ASTRA")
