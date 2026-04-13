from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# =============================
# CONFIGURATION
# =============================
st.set_page_config(
    page_title="Sale Call Management System",
    page_icon="📞",
    layout="wide",
)

APP_TZ = ZoneInfo("Asia/Phnom_Penh")
SHEET_ID = "1FeAYu8jgE_R7IWjcDPjhXsmXvpn79GbVAMa_WU0mxQs"
CALL_LOG_SHEET = "call_log"
PW_SHEET = "pw"
STAFF_SHEET = "call_users"

CALL_LOG_HEADERS = [
    "call_id",
    "call_datetime",
    "customer_name",
    "customer_phone",
    "staff_id",
    "caller_name",
    "call_status",
    "call_purpose",
    "remark",
]

PW_HEADERS = [
    "staff_id",
    "password",
    "hashed_password",
    "date_created",
    "status",
]

CALL_STATUS_OPTIONS = [
    "Pick Up",
    "Not Pick Up",
    "Cannot Contact",
    "Rejected",
    "Wrong Number",
    "Call Back Later",
]

CALL_PURPOSE_OPTIONS = [
    "Loan",
    "TD",
    "CASA",
    "KHQR",
    "Card",
    "Insurance",
    "Follow Up",
    "Other",
]

# =============================
# STYLING
# =============================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f7fbf8 0%, #eef7f1 100%);
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        .hero {
            background: linear-gradient(135deg, #0b7a3c 0%, #14a44d 100%);
            border-radius: 20px;
            padding: 24px 28px;
            color: white;
            box-shadow: 0 10px 30px rgba(16, 119, 60, 0.18);
            margin-bottom: 18px;
        }
        .hero-title {
            font-size: 28px;
            font-weight: 800;
            margin: 0;
            letter-spacing: 0.2px;
        }
        .hero-sub {
            opacity: 0.95;
            margin-top: 6px;
            font-size: 14px;
        }
        .metric-box {
            background: white;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 6px 20px rgba(16, 24, 40, 0.06);
            border: 1px solid rgba(20, 164, 77, 0.12);
        }
        .metric-label {
            color: #256b41;
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            color: #0f5132;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 6px;
        }
        .section-card {
            background: white;
            border-radius: 18px;
            padding: 20px;
            border: 1px solid rgba(20, 164, 77, 0.12);
            box-shadow: 0 6px 20px rgba(16, 24, 40, 0.06);
        }
        .phone-alert-success {
            background: linear-gradient(135deg, #ecfdf3 0%, #dcfce7 100%);
            border: 1px solid #86efac;
            border-left: 6px solid #16a34a;
            color: #14532d;
            padding: 14px 16px;
            border-radius: 14px;
            margin-top: 8px;
            margin-bottom: 10px;
        }
        .phone-alert-warning {
            background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
            border: 1px solid #fdba74;
            border-left: 6px solid #f97316;
            color: #7c2d12;
            padding: 14px 16px;
            border-radius: 14px;
            margin-top: 8px;
            margin-bottom: 10px;
        }
        .small-muted {
            color: #5f6b62;
            font-size: 12px;
        }
        .login-wrap {
            max-width: 520px;
            margin: 0 auto;
            padding-top: 24px;
        }
        .quote-box {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 14px;
            padding: 14px 16px;
            margin-top: 14px;
            backdrop-filter: blur(4px);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# SESSION STATE
# =============================
DEFAULT_SESSION_VALUES = {
    "logged_in": False,
    "staff_id": "",
    "caller_name": "",
}
for k, v in DEFAULT_SESSION_VALUES.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =============================
# HELPERS
# =============================
def cambodia_now() -> datetime:
    return datetime.now(APP_TZ)


def clean_phone_number(phone: str) -> str:
    if phone is None:
        return ""
    phone = str(phone).strip()
    phone = re.sub(r"[^0-9+]", "", phone)
    phone = re.sub(r"^\+?855", "0", phone)
    if phone and not phone.startswith("0"):
        phone = "0" + phone
    return phone


def make_call_id() -> str:
    return f"CALL-{cambodia_now().strftime('%Y%m%d-%H%M%S-%f')[-18:]}"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        100000,
    ).hex()
    return f"{salt}${pwd_hash}"


def verify_hashed_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt, pwd_hash = stored_password.split("$", 1)
        check_hash = hashlib.pbkdf2_hmac(
            "sha256",
            provided_password.encode("utf-8"),
            salt.encode("ascii"),
            100000,
        ).hex()
        return secrets.compare_digest(pwd_hash, check_hash)
    except Exception:
        return False


def read_logo_base64() -> Optional[str]:
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "Logo-CMCB.png"),
        "Logo-CMCB.png",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


# =============================
# GOOGLE SHEETS
# =============================
def setup_gsheets() -> Optional[gspread.Client]:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google Sheets connection error: {e}")
        return None


def get_or_create_worksheet(sheet: gspread.Spreadsheet, title: str, headers: List[str]) -> gspread.Worksheet:
    try:
        ws = sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=1000, cols=max(20, len(headers) + 4))
        ws.append_row(headers)
        return ws

    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers)
    return ws


@st.cache_data(ttl=120)
def load_call_logs() -> pd.DataFrame:
    client = setup_gsheets()
    if not client:
        return pd.DataFrame(columns=CALL_LOG_HEADERS)

    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = get_or_create_worksheet(sheet, CALL_LOG_SHEET, CALL_LOG_HEADERS)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=CALL_LOG_HEADERS)

        for col in CALL_LOG_HEADERS:
            if col not in df.columns:
                df[col] = ""

        df["customer_phone_clean"] = df["customer_phone"].astype(str).apply(clean_phone_number)
        df["call_datetime_dt"] = pd.to_datetime(df["call_datetime"], errors="coerce")
        df = df.sort_values("call_datetime_dt", ascending=False, na_position="last")
        return df
    except Exception as e:
        st.error(f"❌ Failed to load call log data: {e}")
        return pd.DataFrame(columns=CALL_LOG_HEADERS)


@st.cache_data(ttl=120)
def load_users_df() -> pd.DataFrame:
    client = setup_gsheets()
    if not client:
        return pd.DataFrame(columns=PW_HEADERS)

    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = get_or_create_worksheet(sheet, PW_SHEET, PW_HEADERS)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=PW_HEADERS)
        df.columns = df.columns.str.strip().str.lower()
        for col in ["staff_id", "password", "hashed_password", "date_created", "status"]:
            if col not in df.columns:
                df[col] = ""
        df["staff_id"] = df["staff_id"].astype(str).str.strip()
        df["status"] = df["status"].astype(str).str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"❌ Failed to load user data: {e}")
        return pd.DataFrame(columns=PW_HEADERS)


@st.cache_data(ttl=120)
def load_staff_master_df() -> pd.DataFrame:
    client = setup_gsheets()
    if not client:
        return pd.DataFrame()

    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = sheet.worksheet(STAFF_SHEET)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return df
        df.columns = df.columns.str.strip().str.lower()
        return df
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Could not load staff master sheet: {e}")
        return pd.DataFrame()


def user_exists(staff_id: str) -> bool:
    users_df = load_users_df()
    if users_df.empty:
        return False
    return str(staff_id).strip() in users_df["staff_id"].astype(str).str.strip().tolist()


def get_caller_name(staff_id: str) -> str:
    staff_id = str(staff_id).strip()
    staff_df = load_staff_master_df()
    if staff_df.empty:
        return staff_id

    candidate_id_cols = ["staff_id", "id"]
    candidate_name_cols = ["caller_name", "name", "staff_name", "rm", "employee_name"]

    id_col = next((c for c in candidate_id_cols if c in staff_df.columns), None)
    name_col = next((c for c in candidate_name_cols if c in staff_df.columns), None)

    if not id_col or not name_col:
        return staff_id

    match = staff_df[staff_df[id_col].astype(str).str.strip() == staff_id]
    if match.empty:
        return staff_id

    value = str(match.iloc[0][name_col]).strip()
    return value or staff_id


def authenticate_user(staff_id: str, password: str) -> Tuple[bool, str]:
    users_df = load_users_df()
    if users_df.empty:
        return False, "User sheet is empty or unavailable."

    user_row = users_df[users_df["staff_id"] == str(staff_id).strip()]
    if user_row.empty:
        return False, "Staff ID not found."

    user = user_row.iloc[0]
    status = str(user.get("status", "")).strip().lower()
    if status and status != "active":
        return False, "Account is not active."

    plain_password = str(user.get("password", "")).strip()
    hashed_password = str(user.get("hashed_password", "")).strip()

    if plain_password and secrets.compare_digest(plain_password, str(password).strip()):
        return True, "Login successful."

    if hashed_password and verify_hashed_password(hashed_password, str(password).strip()):
        return True, "Login successful."

    return False, "Invalid password."


def register_user(staff_id: str, password: str, confirm_password: str) -> Tuple[bool, str]:
    staff_id = str(staff_id).strip()

    if not staff_id or not password or not confirm_password:
        return False, "Please fill all required fields."
    if password != confirm_password:
        return False, "Passwords do not match."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if user_exists(staff_id):
        return False, "This Staff ID already exists."

    client = setup_gsheets()
    if not client:
        return False, "Cannot connect to Google Sheets."

    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = get_or_create_worksheet(sheet, PW_SHEET, PW_HEADERS)
        ws.append_row(
            [
                staff_id,
                password,
                hash_password(password),
                cambodia_now().strftime("%Y-%m-%d %H:%M:%S"),
                "active",
            ]
        )
        load_users_df.clear()
        return True, "Registration completed."
    except Exception as e:
        return False, f"Registration error: {e}"


def save_call_log(row_data: Dict[str, str]) -> Tuple[bool, str]:
    client = setup_gsheets()
    if not client:
        return False, "Cannot connect to Google Sheets."

    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = get_or_create_worksheet(sheet, CALL_LOG_SHEET, CALL_LOG_HEADERS)

        row = [row_data.get(col, "") for col in CALL_LOG_HEADERS]
        ws.append_row(row)
        load_call_logs.clear()
        return True, "Call log saved successfully."
    except Exception as e:
        return False, f"Save error: {e}"


# =============================
# UI COMPONENTS
# =============================
def render_logo() -> None:
    logo_b64 = read_logo_base64()
    if not logo_b64:
        return

    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;margin-bottom:10px;">
            <img src="data:image/png;base64,{logo_b64}" style="height:90px;width:auto;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_header() -> None:
    render_logo()
    caller = st.session_state.get("caller_name") or st.session_state.get("staff_id", "")
    st.markdown(
        f"""
        <div class="hero">
            <div style="display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;">
                <div>
                    <div class="hero-title">SALE CALL MANAGEMENT SYSTEM</div>
                    <div class="hero-sub">Clean production version for call logging with Cambodia time and duplicate phone checking.</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:13px;opacity:0.95;">Logged in as</div>
                    <div style="font-size:22px;font-weight:800;">{caller}</div>
                    <div style="font-size:13px;opacity:0.95;">Staff ID: {st.session_state.get('staff_id', '')}</div>
                    <div style="font-size:13px;opacity:0.95;margin-top:4px;">{cambodia_now().strftime('%A, %d %B %Y | %H:%M:%S')}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_phone_alert(phone_text: str, df_logs: pd.DataFrame) -> None:
    clean_phone = clean_phone_number(phone_text)
    if not clean_phone:
        st.caption("Type a phone number to check whether it already exists.")
        return

    if df_logs.empty:
        st.markdown(
            f"""
            <div class="phone-alert-success">
                <b>✨ Fresh number</b><br>
                <span>No previous record found for <b>{clean_phone}</b>.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    matches = df_logs[df_logs["customer_phone_clean"] == clean_phone].copy()
    if matches.empty:
        st.markdown(
            f"""
            <div class="phone-alert-success">
                <b>✅ New customer number</b><br>
                <span><b>{clean_phone}</b> does not exist in the call log yet.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    latest_name = str(matches.iloc[0].get("customer_name", "Unknown")).strip() or "Unknown"
    latest_status = str(matches.iloc[0].get("call_status", "-")).strip() or "-"
    latest_dt = str(matches.iloc[0].get("call_datetime", "-")).strip() or "-"

    st.markdown(
        f"""
        <div class="phone-alert-warning">
            <b>⚠️ Existing phone number detected</b><br>
            <span><b>{clean_phone}</b> already exists.</span><br>
            <span>Latest record: <b>{latest_name}</b> • <b>{latest_status}</b> • <b>{latest_dt}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    preview_cols = [
        c for c in ["call_datetime", "customer_name", "call_status", "call_purpose", "remark"] if c in matches.columns
    ]
    st.dataframe(matches[preview_cols].head(5), use_container_width=True, hide_index=True)


def login_page() -> None:
    render_logo()
    st.markdown(
        """
        <div class="login-wrap">
            <div class="hero">
                <div class="hero-title" style="text-align:center;">Welcome Back</div>
                <div class="hero-sub" style="text-align:center;">Log in or register your account to start recording sales calls.</div>
                <div class="quote-box">
                    <b>Daily motivation</b><br>
                    Every call is a new chance. Small consistent actions create big sales results.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

    with tab_login:
        with st.form("login_form"):
            staff_id = st.text_input("Staff ID", placeholder="Enter your Staff ID")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                ok, msg = authenticate_user(staff_id, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.staff_id = str(staff_id).strip()
                    st.session_state.caller_name = get_caller_name(staff_id)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        with st.form("register_form"):
            new_staff_id = st.text_input("Staff ID", placeholder="Enter your Staff ID")
            new_password = st.text_input("Create Password", type="password", placeholder="At least 8 characters")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                ok, msg = register_user(new_staff_id, new_password, confirm_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)


def dashboard_metrics(df_logs: pd.DataFrame, staff_id: str) -> None:
    if df_logs.empty:
        today_count = 0
        total_count = 0
        pickup_count = 0
        unique_phone_count = 0
    else:
        df_staff = df_logs[df_logs["staff_id"].astype(str).str.strip() == str(staff_id).strip()].copy()
        total_count = len(df_staff)
        today_str = cambodia_now().strftime("%Y-%m-%d")
        today_count = df_staff["call_datetime"].astype(str).str.startswith(today_str).sum()
        pickup_count = df_staff["call_status"].astype(str).str.lower().eq("pick up").sum()
        unique_phone_count = df_staff["customer_phone_clean"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Today Calls", f"{today_count}")
    with c2:
        render_metric("Total Calls", f"{total_count}")
    with c3:
        render_metric("Pick Up", f"{pickup_count}")
    with c4:
        render_metric("Unique Phones", f"{unique_phone_count}")


def new_call_tab(df_logs: pd.DataFrame) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📞 New Call Record")
    st.caption("`call_datetime` is automatically saved in Cambodia time.")

    default_phone = st.session_state.get("new_call_phone", "")

    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input("Customer Name", key="new_call_name", placeholder="Enter customer name")
        customer_phone = st.text_input(
            "Customer Phone",
            key="new_call_phone",
            placeholder="e.g. 012345678",
            value=default_phone,
        )
        render_phone_alert(customer_phone, df_logs)
        call_status = st.selectbox("Call Status", CALL_STATUS_OPTIONS, key="new_call_status")
    with col2:
        call_purpose = st.selectbox("Call Purpose", CALL_PURPOSE_OPTIONS, key="new_call_purpose")
        call_datetime_display = cambodia_now().strftime("%Y-%m-%d %H:%M:%S")
        st.text_input("Call Datetime (Cambodia)", value=call_datetime_display, disabled=True)
        remark = st.text_area("Remark", key="new_call_remark", placeholder="Write note / summary / follow-up detail", height=152)

    save_col, clear_col = st.columns([1, 1])
    with save_col:
        if st.button("💾 Save Call", use_container_width=True, type="primary"):
            if not str(customer_name).strip():
                st.error("Customer Name is required.")
            elif not clean_phone_number(customer_phone):
                st.error("Customer Phone is required.")
            else:
                row_data = {
                    "call_id": make_call_id(),
                    "call_datetime": cambodia_now().strftime("%Y-%m-%d %H:%M:%S"),
                    "customer_name": str(customer_name).strip(),
                    "customer_phone": clean_phone_number(customer_phone),
                    "staff_id": st.session_state.get("staff_id", ""),
                    "caller_name": st.session_state.get("caller_name") or st.session_state.get("staff_id", ""),
                    "call_status": call_status,
                    "call_purpose": call_purpose,
                    "remark": str(remark).strip(),
                }
                ok, msg = save_call_log(row_data)
                if ok:
                    st.success(msg)
                    for key in ["new_call_name", "new_call_phone", "new_call_status", "new_call_purpose", "new_call_remark"]:
                        if key in st.session_state:
                            if key in ["new_call_status", "new_call_purpose"]:
                                continue
                            st.session_state[key] = ""
                    st.rerun()
                else:
                    st.error(msg)
    with clear_col:
        if st.button("🧹 Clear Form", use_container_width=True):
            for key in ["new_call_name", "new_call_phone", "new_call_remark"]:
                if key in st.session_state:
                    st.session_state[key] = ""
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def today_log_tab(df_logs: pd.DataFrame) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🗓️ Today Log")

    staff_id = str(st.session_state.get("staff_id", "")).strip()
    today_str = cambodia_now().strftime("%Y-%m-%d")

    if df_logs.empty:
        st.info("No call logs yet.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = df_logs[
        (df_logs["staff_id"].astype(str).str.strip() == staff_id)
        & (df_logs["call_datetime"].astype(str).str.startswith(today_str))
    ].copy()

    if df.empty:
        st.info("No calls recorded today.")
    else:
        st.dataframe(df[CALL_LOG_HEADERS], use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


def history_tab(df_logs: pd.DataFrame) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📜 Call History")

    staff_id = str(st.session_state.get("staff_id", "")).strip()
    search_name = st.text_input("Search customer name", placeholder="Type customer name")
    search_phone = st.text_input("Search phone", placeholder="Type phone number")

    if df_logs.empty:
        st.info("No history found.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = df_logs[df_logs["staff_id"].astype(str).str.strip() == staff_id].copy()

    if search_name:
        df = df[df["customer_name"].astype(str).str.contains(search_name, case=False, na=False)]
    if search_phone:
        df = df[df["customer_phone_clean"].astype(str).str.contains(clean_phone_number(search_phone), case=False, na=False)]

    st.dataframe(df[CALL_LOG_HEADERS], use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(df)} row(s)")
    st.markdown("</div>", unsafe_allow_html=True)


def main_app() -> None:
    df_logs = load_call_logs()
    render_top_header()
    dashboard_metrics(df_logs, st.session_state.get("staff_id", ""))

    st.sidebar.markdown("### Account")
    st.sidebar.write(f"**Caller:** {st.session_state.get('caller_name', '')}")
    st.sidebar.write(f"**Staff ID:** {st.session_state.get('staff_id', '')}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.staff_id = ""
        st.session_state.caller_name = ""
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["📞 New Call", "🗓️ Today Log", "📜 History"])
    with tab1:
        new_call_tab(df_logs)
    with tab2:
        today_log_tab(df_logs)
    with tab3:
        history_tab(df_logs)


# =============================
# APP ENTRY
# =============================
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
