import uuid
import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date, datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
import re

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Call Activity Tracking System",
    page_icon="📞",
    layout="wide",
)

SHEET_ID = "1FeAYu8jgE_R7IWjcDPjhXsmXvpn79GbVAMa_WU0mxQs"  # <-- replace with your real Google Sheet ID
LOGIN_SHEET = "pw"
CALL_LOG_SHEET = "CallLog"
ADMIN_IDS = {"90020759"}

CALLBACK_STATUSES = {"Not Pick Up", "No Answer", "Busy"}
PURPOSE_OPTIONS = [
    "Welcome Call",
    "Follow Up",
    "Promotion",
    "Reminder",
    "Survey",
    "Service Check",
    "Other",
]
STATUS_OPTIONS = [
    "Pick Up",
    "Not Pick Up",
    "No Answer",
    "Busy",
    "Wrong Number",
    "Rejected",
    "Completed",
]

CALL_LOG_HEADERS = [
    "call_id",
    "call_datetime",
    "staff_id",
    "caller_name",
    "phone_number",
    "customer_name",
    "call_purpose",
    "call_status",
    "remark",
    "callback_date",
    "queue_status",
    "created_at",
    "updated_at",
]


# =========================================================
# STYLE
# =========================================================
st.markdown(
    """
    <style>
        .stApp {
            background: #f7faf8;
        }
        .block-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.04);
        }
        .metric-box {
            background: white;
            border: 1px solid #dbe7df;
            border-left: 5px solid #0f8f4a;
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.04);
        }
        .metric-title {
            color: #166534;
            font-size: 14px;
            font-weight: 600;
        }
        .metric-value {
            color: #0f172a;
            font-size: 28px;
            font-weight: 800;
            margin-top: 4px;
        }
        .small-muted {
            color: #6b7280;
            font-size: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def empty_calllog_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[c.lower() for c in CALL_LOG_HEADERS])


def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="small-muted">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_phone_number(phone: str) -> str:
    if not phone:
        return ""
    phone = str(phone).strip()
    phone = re.sub(r"[()\s-]", "", phone)
    phone = re.sub(r"^\+?855", "0", phone)
    phone = re.sub(r"^855", "0", phone)
    if phone and not phone.startswith("0"):
        phone = "0" + phone
    return phone.strip()


def init_session_state() -> None:
    defaults = {
        "logged_in": False,
        "staff_id": "",
        "caller_name": "",
        "form_phone": "",
        "form_name": "",
        "form_purpose": "Welcome Call",
        "form_other_purpose": "",
        "form_status": "Pick Up",
        "form_remark": "",
        "form_callback_date": date.today() + timedelta(days=1),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_new_call_form() -> None:
    st.session_state.form_phone = ""
    st.session_state.form_name = ""
    st.session_state.form_purpose = "Welcome Call"
    st.session_state.form_other_purpose = ""
    st.session_state.form_status = "Pick Up"
    st.session_state.form_remark = ""
    st.session_state.form_callback_date = date.today() + timedelta(days=1)


# =========================================================
# GOOGLE SHEETS
# =========================================================
def setup_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google Sheets connection failed: {e}")
        return None


def ensure_call_log_sheet(client):
    try:
        sheet = client.open_by_key(SHEET_ID)
        try:
            ws = sheet.worksheet(CALL_LOG_SHEET)
        except WorksheetNotFound:
            ws = sheet.add_worksheet(
                title=CALL_LOG_SHEET,
                rows=5000,
                cols=max(len(CALL_LOG_HEADERS) + 5, 20),
            )
            ws.append_row(CALL_LOG_HEADERS)
            return ws

        current_values = ws.get_all_values()
        if not current_values:
            ws.append_row(CALL_LOG_HEADERS)
        return ws
    except Exception as e:
        st.error(f"❌ Failed to open or create CallLog sheet: {e}")
        raise


@st.cache_data(ttl=120)
def load_call_logs() -> pd.DataFrame:
    try:
        client = setup_gsheets()
        if not client:
            return empty_calllog_df()

        ws = ensure_call_log_sheet(client)
        records = ws.get_all_records()
        if not records:
            return empty_calllog_df()

        df = pd.DataFrame(records)
        df.columns = [str(c).strip().lower() for c in df.columns]

        for col in ["call_datetime", "callback_date", "created_at", "updated_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ["staff_id", "caller_name", "phone_number", "customer_name", "call_purpose", "call_status", "remark", "queue_status"]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna("").str.strip()
            else:
                df[col] = ""

        return df
    except Exception as e:
        st.error(f"❌ Failed to load call logs: {e}")
        return empty_calllog_df()


def append_call_log(record: dict) -> bool:
    try:
        client = setup_gsheets()
        if not client:
            return False

        ws = ensure_call_log_sheet(client)
        row = [record.get(col, "") for col in CALL_LOG_HEADERS]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"❌ Failed to save call log: {e}")
        return False


def update_call_log_by_id(call_id: str, updates: dict) -> bool:
    try:
        client = setup_gsheets()
        if not client:
            return False

        ws = ensure_call_log_sheet(client)
        all_values = ws.get_all_values()
        if not all_values:
            return False

        headers = [str(h).strip().lower() for h in all_values[0]]
        if "call_id" not in headers:
            st.error("❌ Column 'call_id' not found in CallLog sheet")
            return False

        call_id_idx = headers.index("call_id")
        target_row = None
        for row_num, row in enumerate(all_values[1:], start=2):
            if call_id_idx < len(row) and str(row[call_id_idx]).strip() == str(call_id).strip():
                target_row = row_num
                break

        if not target_row:
            st.error("❌ Call record not found")
            return False

        for field, value in updates.items():
            field = str(field).strip().lower()
            if field in headers:
                ws.update_cell(target_row, headers.index(field) + 1, str(value))

        return True
    except Exception as e:
        st.error(f"❌ Failed to update call log: {e}")
        return False


# =========================================================
# AUTH
# =========================================================
def authenticate_user(staff_id: str, password: str):
    try:
        client = setup_gsheets()
        if not client:
            return False, None

        sheet = client.open_by_key(SHEET_ID)
        ws = sheet.worksheet(LOGIN_SHEET)
        records = ws.get_all_records()

        for record in records:
            record = {str(k).strip().lower(): record[k] for k in record.keys()}
            row_staff = str(record.get("staff_id", "")).strip()
            row_password = str(record.get("password", "")).strip()
            row_status = str(record.get("status", "active")).strip().lower()

            if row_staff == str(staff_id).strip():
                if row_status != "active":
                    st.error("❌ Account is not active")
                    return False, None

                if row_password == str(password).strip():
                    caller_name = (
                        str(record.get("caller_name", "")).strip()
                        or str(record.get("name", "")).strip()
                        or str(record.get("full_name", "")).strip()
                        or str(record.get("username", "")).strip()
                        or row_staff
                    )
                    return True, {"staff_id": row_staff, "caller_name": caller_name}

                st.error("❌ Invalid password")
                return False, None

        st.error("❌ Staff ID not found")
        return False, None
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")
        return False, None


def logout() -> None:
    st.session_state.logged_in = False
    st.session_state.staff_id = ""
    st.session_state.caller_name = ""
    reset_new_call_form()
    st.rerun()


# =========================================================
# LOGIN PAGE
# =========================================================
def login_page() -> None:
    st.markdown(
        """
        <div class="block-card" style="max-width: 480px; margin: 40px auto;">
            <h2 style="margin:0; color:#166534;">📞 Call Activity Tracking System</h2>
            <p style="color:#6b7280; margin-top:8px;">
                Login with your Staff ID to record calls and manage unpicked-up customers.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        staff_id = st.text_input("Staff ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            ok, profile = authenticate_user(staff_id, password)
            if ok and profile:
                st.session_state.logged_in = True
                st.session_state.staff_id = profile["staff_id"]
                st.session_state.caller_name = profile["caller_name"]
                st.success("✅ Login successful")
                st.rerun()


# =========================================================
# PAGES
# =========================================================
def page_new_call(df_scope: pd.DataFrame) -> None:
    st.subheader("📞 New Call Log")

    today_mask = pd.Series(dtype=bool)
    if not df_scope.empty and "call_datetime" in df_scope.columns:
        today_mask = df_scope["call_datetime"].dt.date == date.today()

    total_today = int(today_mask.sum()) if len(today_mask) else 0
    picked_today = int((df_scope.loc[today_mask, "call_status"] == "Pick Up").sum()) if len(today_mask) else 0
    pending_callbacks = int((df_scope["queue_status"] == "Pending Callback").sum()) if not df_scope.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Today Calls", str(total_today), "Logged by you today")
    with c2:
        metric_card("Today Pick Up", str(picked_today), "Successful pick-up calls")
    with c3:
        metric_card("Pending Callbacks", str(pending_callbacks), "Need to call again")

    st.markdown("---")

    with st.form("new_call_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Phone Number *", key="form_phone", placeholder="e.g. 012345678")
            customer_name = st.text_input("Full Name *", key="form_name", placeholder="Customer name")
            purpose = st.selectbox("Call Purpose *", PURPOSE_OPTIONS, key="form_purpose")
            if purpose == "Other":
                other_purpose = st.text_input("Specify Call Purpose *", key="form_other_purpose")
            else:
                other_purpose = ""

        with col2:
            status = st.selectbox("Call Status *", STATUS_OPTIONS, key="form_status")
            if status in CALLBACK_STATUSES:
                callback_date = st.date_input(
                    "Callback Date *",
                    key="form_callback_date",
                    min_value=date.today(),
                )
            else:
                callback_date = None

        remark = st.text_area(
            "Remark",
            key="form_remark",
            height=140,
            placeholder="Example: Customer was busy, asked to call tomorrow morning.",
        )

        save_col1, save_col2 = st.columns(2)
        save_clicked = save_col1.form_submit_button("💾 Save")
        save_new_clicked = save_col2.form_submit_button("💾 Save & New")

        if save_clicked or save_new_clicked:
            phone_clean = clean_phone_number(phone)
            purpose_final = other_purpose.strip() if purpose == "Other" else purpose

            if not phone_clean:
                st.error("❌ Phone Number is required")
                return
            if not customer_name.strip():
                st.error("❌ Full Name is required")
                return
            if not purpose_final:
                st.error("❌ Call Purpose is required")
                return
            if status in CALLBACK_STATUSES and callback_date is None:
                st.error("❌ Callback Date is required for unpicked-up customers")
                return

            timestamp = now_str()
            record = {
                "call_id": uuid.uuid4().hex[:12].upper(),
                "call_datetime": timestamp,
                "staff_id": st.session_state.staff_id,
                "caller_name": st.session_state.caller_name,
                "phone_number": phone_clean,
                "customer_name": customer_name.strip(),
                "call_purpose": purpose_final,
                "call_status": status,
                "remark": remark.strip(),
                "callback_date": callback_date.strftime("%Y-%m-%d") if callback_date else "",
                "queue_status": "Pending Callback" if status in CALLBACK_STATUSES else "Closed",
                "created_at": timestamp,
                "updated_at": timestamp,
            }

            if append_call_log(record):
                st.cache_data.clear()
                st.success("✅ Call log saved successfully")
                if save_new_clicked:
                    reset_new_call_form()
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Recent Calls")
    recent = df_scope.sort_values("call_datetime", ascending=False).head(10).copy() if not df_scope.empty else empty_calllog_df()
    if recent.empty:
        st.info("No calls logged yet.")
    else:
        show_cols = [
            "call_datetime",
            "phone_number",
            "customer_name",
            "call_purpose",
            "call_status",
            "queue_status",
            "remark",
        ]
        recent = recent[[c for c in show_cols if c in recent.columns]].copy()
        if "call_datetime" in recent.columns:
            recent["call_datetime"] = recent["call_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(recent, use_container_width=True, hide_index=True)


def page_unpicked_queue(df_scope: pd.DataFrame) -> None:
    st.subheader("📋 Unpicked Up Queue")
    st.caption("Customers with status Not Pick Up / No Answer / Busy appear here for later callback.")

    if df_scope.empty:
        st.info("No queue records found.")
        return

    queue_df = df_scope[df_scope["queue_status"].fillna("") == "Pending Callback"].copy()

    if queue_df.empty:
        st.success("🎉 No pending callbacks.")
        return

    view_filter = st.radio("View", ["All Pending", "Overdue", "Due Today", "Upcoming"], horizontal=True)
    today = pd.Timestamp(date.today())

    if "callback_date" in queue_df.columns:
        if view_filter == "Overdue":
            queue_df = queue_df[queue_df["callback_date"].dt.date < today.date()]
        elif view_filter == "Due Today":
            queue_df = queue_df[queue_df["callback_date"].dt.date == today.date()]
        elif view_filter == "Upcoming":
            queue_df = queue_df[queue_df["callback_date"].dt.date > today.date()]

    queue_df = queue_df.sort_values(["callback_date", "call_datetime"], ascending=[True, False], na_position="last")

    if queue_df.empty:
        st.info("No records found for this filter.")
        return

    st.info(f"Pending callbacks: {len(queue_df)}")

    for _, row in queue_df.iterrows():
        call_id = row.get("call_id", "")
        customer_name = row.get("customer_name", "Unknown")
        phone_number = row.get("phone_number", "")
        purpose = row.get("call_purpose", "")
        call_status = row.get("call_status", "")
        callback_date = row.get("callback_date")
        last_call = row.get("call_datetime")

        callback_label = callback_date.strftime("%Y-%m-%d") if pd.notna(callback_date) else "No date"
        last_call_label = last_call.strftime("%Y-%m-%d %H:%M") if pd.notna(last_call) else "No date"

        with st.expander(f"📞 {customer_name} | {phone_number} | Callback: {callback_label}"):
            left, right = st.columns(2)
            with left:
                st.write(f"**Customer Name:** {customer_name}")
                st.write(f"**Phone Number:** {phone_number}")
                st.write(f"**Call Purpose:** {purpose}")
            with right:
                st.write(f"**Previous Status:** {call_status}")
                st.write(f"**Last Call:** {last_call_label}")
                st.write(f"**Current Queue:** Pending Callback")

            old_remark = row.get("remark", "")
            if str(old_remark).strip():
                st.write("**Previous Remark:**")
                st.info(str(old_remark))

            st.markdown("---")
            st.markdown("#### Log Callback Result")

            with st.form(key=f"callback_form_{call_id}"):
                new_status = st.selectbox(
                    "Callback Status",
                    STATUS_OPTIONS,
                    index=0,
                    key=f"callback_status_{call_id}",
                )
                new_remark = st.text_area(
                    "New Remark",
                    key=f"callback_remark_{call_id}",
                    placeholder="Write the result of this callback...",
                )

                if new_status in CALLBACK_STATUSES:
                    next_callback = st.date_input(
                        "Next Callback Date",
                        key=f"next_callback_{call_id}",
                        min_value=date.today(),
                        value=date.today() + timedelta(days=1),
                    )
                else:
                    next_callback = None

                b1, b2 = st.columns(2)
                save_callback = b1.form_submit_button("💾 Save Callback Result")
                close_only = b2.form_submit_button("✅ Close Without New Callback")

                if save_callback:
                    timestamp = now_str()
                    new_record = {
                        "call_id": uuid.uuid4().hex[:12].upper(),
                        "call_datetime": timestamp,
                        "staff_id": st.session_state.staff_id,
                        "caller_name": st.session_state.caller_name,
                        "phone_number": phone_number,
                        "customer_name": customer_name,
                        "call_purpose": purpose,
                        "call_status": new_status,
                        "remark": new_remark.strip(),
                        "callback_date": next_callback.strftime("%Y-%m-%d") if next_callback else "",
                        "queue_status": "Pending Callback" if new_status in CALLBACK_STATUSES else "Closed",
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    }

                    ok1 = append_call_log(new_record)
                    ok2 = update_call_log_by_id(call_id, {"queue_status": "Completed", "updated_at": timestamp})
                    if ok1 and ok2:
                        st.cache_data.clear()
                        st.success("✅ Callback result saved")
                        st.rerun()

                if close_only:
                    ok = update_call_log_by_id(
                        call_id,
                        {"queue_status": "Completed", "updated_at": now_str()},
                    )
                    if ok:
                        st.cache_data.clear()
                        st.success("✅ Queue item closed")
                        st.rerun()


def page_history(df_scope: pd.DataFrame) -> None:
    st.subheader("📜 Call History")

    if df_scope.empty:
        st.info("No call history found.")
        return

    hist = df_scope.copy()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_text = st.text_input("Search Name / Phone")
    with col2:
        start_date = st.date_input("From", value=date.today() - timedelta(days=7))
    with col3:
        end_date = st.date_input("To", value=date.today())
    with col4:
        status_filter = st.multiselect(
            "Status",
            options=sorted(hist["call_status"].dropna().astype(str).unique().tolist()),
        )

    purpose_filter = st.multiselect(
        "Call Purpose",
        options=sorted(hist["call_purpose"].dropna().astype(str).unique().tolist()),
    )

    if "call_datetime" in hist.columns:
        hist = hist[
            (hist["call_datetime"].dt.date >= start_date)
            & (hist["call_datetime"].dt.date <= end_date)
        ]

    if search_text.strip():
        q = search_text.strip().lower()
        hist = hist[
            hist["customer_name"].str.lower().str.contains(q, na=False)
            | hist["phone_number"].str.lower().str.contains(q, na=False)
        ]

    if status_filter:
        hist = hist[hist["call_status"].isin(status_filter)]

    if purpose_filter:
        hist = hist[hist["call_purpose"].isin(purpose_filter)]

    hist = hist.sort_values("call_datetime", ascending=False)

    if hist.empty:
        st.info("No records found for the selected filters.")
        return

    display = hist[[
        "call_datetime",
        "staff_id",
        "caller_name",
        "phone_number",
        "customer_name",
        "call_purpose",
        "call_status",
        "queue_status",
        "remark",
    ]].copy()

    display = display.rename(
        columns={
            "call_datetime": "Call DateTime",
            "staff_id": "Staff ID",
            "caller_name": "Caller Name",
            "phone_number": "Phone Number",
            "customer_name": "Customer Name",
            "call_purpose": "Call Purpose",
            "call_status": "Call Status",
            "queue_status": "Queue Status",
            "remark": "Remark",
        }
    )

    if "Call DateTime" in display.columns:
        display["Call DateTime"] = pd.to_datetime(display["Call DateTime"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(display, use_container_width=True, hide_index=True, height=520)


def page_dashboard(df_all: pd.DataFrame, df_user: pd.DataFrame) -> None:
    st.subheader("📊 Dashboard")

    is_admin = st.session_state.staff_id in ADMIN_IDS
    if is_admin:
        view = st.radio("Dashboard Scope", ["My Calls", "All Calls"], horizontal=True)
        df_scope = df_all.copy() if view == "All Calls" else df_user.copy()
    else:
        df_scope = df_user.copy()

    if df_scope.empty:
        st.info("No data available for dashboard.")
        return

    total_calls = len(df_scope)
    picked_up = int((df_scope["call_status"] == "Pick Up").sum())
    pending_callbacks = int((df_scope["queue_status"] == "Pending Callback").sum())
    today_calls = int((df_scope["call_datetime"].dt.date == date.today()).sum())

    a, b, c, d = st.columns(4)
    with a:
        metric_card("Total Calls", f"{total_calls:,}", "All logged calls")
    with b:
        metric_card("Pick Up", f"{picked_up:,}", "Successful answered calls")
    with c:
        metric_card("Pending Callbacks", f"{pending_callbacks:,}", "Need to call again")
    with d:
        metric_card("Today Calls", f"{today_calls:,}", "Calls logged today")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        status_counts = (
            df_scope["call_status"]
            .fillna("Unknown")
            .value_counts()
            .reset_index()
        )
        status_counts.columns = ["Call Status", "Count"]
        fig_status = px.bar(
            status_counts,
            x="Call Status",
            y="Count",
            text="Count",
            title="Call Status Breakdown",
            color="Call Status",
        )
        fig_status.update_traces(textposition="outside")
        fig_status.update_layout(showlegend=False)
        st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        purpose_counts = (
            df_scope["call_purpose"]
            .fillna("Unknown")
            .value_counts()
            .reset_index()
        )
        purpose_counts.columns = ["Call Purpose", "Count"]
        fig_purpose = px.pie(
            purpose_counts,
            names="Call Purpose",
            values="Count",
            hole=0.45,
            title="Call Purpose Distribution",
        )
        st.plotly_chart(fig_purpose, use_container_width=True)

    st.markdown("---")

    trend_df = df_scope.copy()
    trend_df["call_day"] = trend_df["call_datetime"].dt.date
    trend = trend_df.groupby("call_day", as_index=False).size()
    trend.columns = ["Call Day", "Count"]
    fig_trend = px.line(trend, x="Call Day", y="Count", markers=True, title="Daily Call Trend")
    st.plotly_chart(fig_trend, use_container_width=True)

    if is_admin and len(df_scope) > 0 and "All Calls" in locals().get("view", ""):
        pass

    if is_admin and not df_all.empty:
        staff_counts = (
            df_all.groupby(["staff_id", "caller_name"], as_index=False)
            .size()
            .sort_values("size", ascending=False)
        )
        staff_counts.columns = ["Staff ID", "Caller Name", "Count"]
        if not staff_counts.empty:
            fig_staff = px.bar(
                staff_counts,
                x="Staff ID",
                y="Count",
                hover_data=["Caller Name"],
                text="Count",
                title="Calls by Staff",
            )
            fig_staff.update_traces(textposition="outside")
            st.plotly_chart(fig_staff, use_container_width=True)


# =========================================================
# MAIN APP
# =========================================================
def main_app() -> None:
    st.markdown(
        f"""
        <div class="block-card">
            <h2 style="margin:0; color:#166534;">📞 Call Activity Tracking System</h2>
            <p style="margin:8px 0 0 0; color:#4b5563;">
                Logged in as <b>{st.session_state.caller_name}</b> ({st.session_state.staff_id})
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navigation")
    st.sidebar.write(f"**Staff ID:** {st.session_state.staff_id}")
    st.sidebar.write(f"**Caller:** {st.session_state.caller_name}")

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()

    page = st.sidebar.radio(
        "Go to",
        ["📞 New Call Log", "📋 Unpicked Up Queue", "📜 Call History", "📊 Dashboard"],
    )

    df_all = load_call_logs()
    if df_all.empty:
        df_all = empty_calllog_df()

    if "staff_id" in df_all.columns:
        df_all["staff_id"] = df_all["staff_id"].astype(str).str.strip()

    df_user = (
        df_all[df_all["staff_id"] == str(st.session_state.staff_id).strip()].copy()
        if not df_all.empty and "staff_id" in df_all.columns
        else empty_calllog_df()
    )

    if page == "📞 New Call Log":
        page_new_call(df_user)
    elif page == "📋 Unpicked Up Queue":
        page_unpicked_queue(df_user)
    elif page == "📜 Call History":
        page_history(df_user)
    elif page == "📊 Dashboard":
        page_dashboard(df_all, df_user)


# =========================================================
# RUN
# =========================================================
init_session_state()

if not st.session_state.logged_in:
    login_page()
else:
    main_app()
