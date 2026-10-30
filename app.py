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

data = load_complaints()
complaints = data.get("complaints", [])

st.sidebar.title("🏙️ CiviFix")
st.sidebar.caption("From Complaints to Action")
page = st.sidebar.radio("Navigation", ["Submit Complaint", "Admin Dashboard", "Track Complaint", "About"])

if page == "Submit Complaint":
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
        color_map = {"High": "red", "Medium": "orange", "Low": "green"}

        for c in complaints:
            lat = c.get("latitude") or 12.97
            lon = c.get("longitude") or 77.59
            color = color_map.get(c.get("priority", "Low"), "blue")
            folium.Marker(
                [lat, lon],
                popup=f"{c['complaint_id']} | {c.get('priority')} | {c.get('category')}",
                tooltip=f"{c['complaint_id']} ({c.get('priority')})",
                icon=folium.Icon(color=color)
            ).add_to(m)

        st_folium(m, width=None, height=420)

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
