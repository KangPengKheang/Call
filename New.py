import base64
import hashlib
import os
import re
import secrets
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Sale Call Management System",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SHEET_ID = "1FeAYu8jgE_R7IWjcDPjhXsmXvpn79GbVAMa_WU0mxQs"
CALL_LOG_SHEET_NAME = "testing"
PASSWORD_SHEET_NAME = "pw"
STAFF_SHEET_NAME = "call_users"
LOGO_PATH = "Logo-CMCB.png"

CAMBODIA_TZ = ZoneInfo("Asia/Phnom_Penh")

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

CALLBACK_STATUSES = {"Not Pick Up", "No Answer", "Busy"}

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

PASSWORD_HEADERS = [
    "staff_id",
    "password",
    "hashed_password",
    "date_created",
    "status",
]

MOTIVATION_QUOTE = "Every call is a new chance to create trust, solve a need, and open the next opportunity."

# =========================================================
# STYLE
# =========================================================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #f8fffb 0%, #f2f8f4 45%, #f8fafc 100%);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu,
        footer,
        header {
            visibility: hidden !important;
            display: none !important;
            height: 0 !important;
        }

        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 1.6rem !important;
            max-width: 1380px;
        }

        .logo-fallback {
            width: 58px;
            height: 58px;
            border-radius: 18px;
            background: linear-gradient(135deg, #166534 0%, #10b981 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 900;
        }

        .mini-stat-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 14px;
        }

        .mini-stat {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 18px;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 12px 14px;
            font-size: 13px;
            color: #334155;
            font-weight: 700;
        }

        .queue-note {
            margin-top: 10px;
            background: #ecfdf5;
            border: 1px solid #bbf7d0;
            border-radius: 18px;
            padding: 14px;
            color: #334155;
            font-size: 14px;
        }

        .motivation-box {
            margin-top: 24px;
            max-width: 760px;
            font-size: 18px;
            line-height: 1.8;
            color: #475569;
        }

        .motivation-sign {
            margin-top: 10px;
            font-size: 14px;
            font-weight: 700;
            color: #166534;
        }

        .stButton > button {
            border-radius: 16px;
            height: 46px;
            font-weight: 700;
            border: 1px solid #d1d5db;
            box-shadow: none;
        }

        .stButton > button[kind="primary"] {
            background: #ef4444;
            color: white;
            border: none;
        }

        .stButton > button[kind="primary"]:hover {
            background: #dc2626;
            color: white;
        }

        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stDateInput input,
        .stSelectbox [data-baseweb="select"] > div {
            border-radius: 16px !important;
            min-height: 46px;
            background: #f8fafc !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 28px;
            background: transparent;
            border-bottom: 1px solid #e5e7eb;
            padding-left: 2px;
            padding-right: 2px;
            margin-bottom: 18px;
        }

        .stTabs [data-baseweb="tab"] {
            height: 52px;
            background: transparent;
            border: none;
            color: #334155;
            font-size: 16px;
            font-weight: 600;
            padding-left: 0;
            padding-right: 0;
        }

        .stTabs [aria-selected="true"] {
            color: #ef4444 !important;
            border-bottom: 3px solid #ef4444 !important;
        }

        div[data-testid="stImage"] img {
            border-radius: 18px;
        }

        .phone-check-card {
            margin-top: 10px;
            border-radius: 18px;
            padding: 14px 16px;
            border: 1px solid;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }

        .phone-check-exists {
            background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
            border-color: #fdba74;
        }

        .phone-check-new {
            background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
            border-color: #86efac;
        }

        .phone-check-title {
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 6px;
        }

        .phone-check-sub {
            font-size: 13px;
            color: #475569;
            line-height: 1.6;
        }

        .auth-note {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# BASIC HELPERS
# =========================================================
def now_ts() -> datetime:
    return datetime.now(CAMBODIA_TZ)


def cambodia_now_str() -> str:
    return now_ts().strftime("%Y-%m-%d %H:%M:%S")


def clean_phone_number(phone: str) -> str:
    if not phone:
        return ""
    phone = str(phone).strip()
    phone = re.sub(r"[^0-9+]", "", phone)
    phone = re.sub(r"^\+?855", "0", phone)
    phone = re.sub(r"^855", "0", phone)
    if phone and not phone.startswith("0"):
        phone = "0" + phone
    return phone


def safe_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def fmt_datetime(value) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return "-"
    return parsed.strftime("%d %b %Y %H:%M")


def get_logo_base64() -> str:
    if not os.path.exists(LOGO_PATH):
        return ""
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        100000,
    )
    return f"{salt}${pwdhash.hex()}"


# =========================================================
# STREAMLIT STATE
# =========================================================
def ensure_form_state() -> None:
    defaults = {
        "form_phone": "",
        "form_name": "",
        "form_purpose": "Welcome Call",
        "form_other_purpose": "",
        "form_status": "Pick Up",
        "form_remark": "",
        "history_search": "",
        "history_status": "All",
        "history_purpose": "All",
        "_pending_form_reset": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_form() -> None:
    st.session_state.form_phone = ""
    st.session_state.form_name = ""
    st.session_state.form_purpose = "Welcome Call"
    st.session_state.form_other_purpose = ""
    st.session_state.form_status = "Pick Up"
    st.session_state.form_remark = ""


def queue_form_reset() -> None:
    st.session_state["_pending_form_reset"] = True


def apply_pending_form_reset() -> None:
    if st.session_state.get("_pending_form_reset", False):
        reset_form()
        st.session_state["_pending_form_reset"] = False


def init_state() -> None:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "staff_id" not in st.session_state:
        st.session_state.staff_id = ""
    if "caller_name" not in st.session_state:
        st.session_state.caller_name = ""
    if "user_role" not in st.session_state:
        st.session_state.user_role = "sales executive"
    if "branch_name" not in st.session_state:
        st.session_state.branch_name = ""
    if "branch_manager" not in st.session_state:
        st.session_state.branch_manager = ""
    ensure_form_state()


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
        st.error(f"Google Sheets connection error: {e}")
        return None


def get_sheet(sheet_name: str):
    client = setup_gsheets()
    if not client:
        return None
    workbook = client.open_by_key(SHEET_ID)
    try:
        return workbook.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        return None


def ensure_password_sheet():
    client = setup_gsheets()
    if not client:
        return None

    workbook = client.open_by_key(SHEET_ID)
    try:
        worksheet = workbook.worksheet(PASSWORD_SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = workbook.add_worksheet(
            title=PASSWORD_SHEET_NAME,
            rows=1000,
            cols=len(PASSWORD_HEADERS),
        )
        worksheet.append_row(PASSWORD_HEADERS)
        return worksheet

    all_values = worksheet.get_all_values()
    if not all_values:
        worksheet.append_row(PASSWORD_HEADERS)
        return worksheet

    current_headers = [safe_text(h) for h in all_values[0]]
    merged_headers = current_headers[:]
    for header in PASSWORD_HEADERS:
        if header not in merged_headers:
            merged_headers.append(header)

    if merged_headers != current_headers:
        worksheet.resize(rows=max(len(all_values), 1000), cols=len(merged_headers))
        worksheet.update("A1", [merged_headers])

    return worksheet


def ensure_call_log_sheet():
    client = setup_gsheets()
    if not client:
        return None

    workbook = client.open_by_key(SHEET_ID)
    try:
        worksheet = workbook.worksheet(CALL_LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = workbook.add_worksheet(
            title=CALL_LOG_SHEET_NAME,
            rows=1000,
            cols=len(CALL_LOG_HEADERS),
        )
        worksheet.append_row(CALL_LOG_HEADERS)
        return worksheet

    all_values = worksheet.get_all_values()
    if not all_values:
        worksheet.append_row(CALL_LOG_HEADERS)
        return worksheet

    worksheet.resize(rows=max(len(all_values), 1000), cols=len(CALL_LOG_HEADERS))
    worksheet.update("A1", [CALL_LOG_HEADERS])
    return worksheet


def append_row_by_headers(worksheet, record: dict) -> bool:
    try:
        headers = worksheet.row_values(1)
        row = [record.get(header, "") for header in headers]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


# =========================================================
# USER / AUTH
# =========================================================
def load_staff_master_df() -> pd.DataFrame:
    try:
        worksheet = get_sheet(STAFF_SHEET_NAME)
        if worksheet is None:
            return pd.DataFrame()

        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df.columns = [safe_text(c).lower() for c in df.columns]

        def find_col(candidates):
            for col in candidates:
                if col in df.columns:
                    return col
            return None

        id_col = find_col(["id", "staff_id", "staff id"])
        role_col = find_col(["role"])
        branch_col = find_col(["appreviation", "abbreviation", "branch_name", "branch"])
        manager_col = find_col(["team lead", "branch_manager", "manager", "team_lead"])
        name_col = find_col(["name", "full_name", "staff_name", "caller_name"])

        out = pd.DataFrame()
        out["staff_id"] = df[id_col].astype(str).str.strip() if id_col else ""
        out["role"] = df[role_col].astype(str).str.strip().str.lower() if role_col else "sales executive"
        out["branch_name"] = df[branch_col].astype(str).str.strip() if branch_col else ""
        out["branch_manager"] = df[manager_col].astype(str).str.strip() if manager_col else ""
        out["caller_name"] = df[name_col].astype(str).str.strip() if name_col else out["staff_id"]

        return out[["staff_id", "caller_name", "role", "branch_name", "branch_manager"]]
    except Exception:
        return pd.DataFrame()


def load_staff_profile(staff_id: str) -> dict:
    df = load_staff_master_df()
    if df.empty:
        return {
            "staff_id": safe_text(staff_id),
            "caller_name": safe_text(staff_id),
            "role": "sales executive",
            "branch_name": "",
            "branch_manager": "",
        }

    row = df[df["staff_id"] == safe_text(staff_id)]
    if row.empty:
        return {
            "staff_id": safe_text(staff_id),
            "caller_name": safe_text(staff_id),
            "role": "sales executive",
            "branch_name": "",
            "branch_manager": "",
        }

    row = row.iloc[0]
    return {
        "staff_id": safe_text(row.get("staff_id")),
        "caller_name": safe_text(row.get("caller_name")) or safe_text(staff_id),
        "role": safe_text(row.get("role")).lower() or "sales executive",
        "branch_name": safe_text(row.get("branch_name")),
        "branch_manager": safe_text(row.get("branch_manager")),
    }


def user_exists(staff_id: str) -> bool:
    try:
        worksheet = ensure_password_sheet()
        if worksheet is None:
            return False

        records = worksheet.get_all_records()
        target = safe_text(staff_id)
        for record in records:
            if safe_text(record.get("staff_id")) == target:
                return True
        return False
    except Exception:
        return False


def authenticate_user(staff_id: str, password: str) -> bool:
    try:
        worksheet = ensure_password_sheet()
        if worksheet is None:
            st.error("Password sheet not found")
            return False

        records = worksheet.get_all_records()
        target_staff = safe_text(staff_id)
        target_password = safe_text(password)

        for record in records:
            if safe_text(record.get("staff_id")) == target_staff:
                status = safe_text(record.get("status")).lower() or "active"
                stored_password = safe_text(record.get("password"))
                if status != "active":
                    st.error("Account is not active")
                    return False
                if stored_password != target_password:
                    st.error("Invalid password")
                    return False
                return True

        st.error("Staff ID not found")
        return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def register_user(staff_id: str, password: str, confirm_password: str) -> bool:
    try:
        staff_id = safe_text(staff_id)
        password = safe_text(password)
        confirm_password = safe_text(confirm_password)

        if not staff_id or not password or not confirm_password:
            st.error("Please fill all required fields")
            return False

        if password != confirm_password:
            st.error("Passwords do not match")
            return False

        if len(password) < 8:
            st.error("Password must be at least 8 characters")
            return False

        if user_exists(staff_id):
            st.error("Staff ID already exists")
            return False

        worksheet = ensure_password_sheet()
        if worksheet is None:
            return False

        record = {
            "staff_id": staff_id,
            "password": password,
            "hashed_password": hash_password(password),
            "date_created": cambodia_now_str(),
            "status": "active",
        }

        return append_row_by_headers(worksheet, record)
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False


# =========================================================
# CALL LOG DATA
# =========================================================
def get_call_log_data() -> pd.DataFrame:
    worksheet = ensure_call_log_sheet()
    if worksheet is None:
        return pd.DataFrame()

    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()

    headers = [safe_text(h) for h in values[0]]
    rows = values[1:]
    if not rows:
        return pd.DataFrame(columns=headers + ["_row_number"])

    width = len(headers)
    normalized_rows = []
    for row in rows:
        padded = list(row) + [""] * (width - len(row))
        normalized_rows.append(padded[:width])

    df = pd.DataFrame(normalized_rows, columns=headers)
    df["_row_number"] = list(range(2, len(df) + 2))
    return df


def normalize_call_log_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        for col in CALL_LOG_HEADERS:
            if col not in df.columns:
                df[col] = ""
        return df

    df = df.copy()

    for col in df.columns:
        if col == "_row_number":
            continue
        df[col] = df[col].apply(safe_text)

    for col in CALL_LOG_HEADERS:
        if col not in df.columns:
            df[col] = ""

    df["customer_phone"] = df["customer_phone"].apply(clean_phone_number)
    df["call_datetime"] = pd.to_datetime(df["call_datetime"], errors="coerce")
    df["phone_key"] = df["customer_phone"].apply(clean_phone_number)
    df["customer_name"] = df["customer_name"].astype(str).str.strip()
    df["staff_id"] = df["staff_id"].astype(str).str.strip()
    df["caller_name"] = df["caller_name"].where(df["caller_name"] != "", df["staff_id"])

    return df


def get_latest_calls_by_phone(df_user: pd.DataFrame) -> pd.DataFrame:
    if df_user.empty:
        return df_user.copy()

    temp = df_user.copy()
    temp = temp[temp["phone_key"] != ""].copy()
    temp = temp.sort_values("call_datetime", ascending=False, na_position="last")
    temp = temp.drop_duplicates(subset=["phone_key"], keep="first")
    return temp


def save_new_call_to_sheet() -> bool:
    worksheet = ensure_call_log_sheet()
    if worksheet is None:
        return False

    phone_clean = clean_phone_number(st.session_state.form_phone)
    purpose = (
        st.session_state.form_other_purpose.strip()
        if st.session_state.form_purpose == "Other"
        else st.session_state.form_purpose
    )

    record = {
        "call_id": safe_text(pd.Timestamp.now().strftime("%y%m%d%H%M%S%f"))[-10:],
        "call_datetime": cambodia_now_str(),
        "customer_name": st.session_state.form_name.strip(),
        "customer_phone": phone_clean,
        "staff_id": safe_text(st.session_state.staff_id),
        "caller_name": safe_text(st.session_state.caller_name),
        "call_status": st.session_state.form_status,
        "call_purpose": purpose,
        "remark": st.session_state.form_remark.strip(),
    }
    return append_row_by_headers(worksheet, record)


def save_callback_result(row_data: pd.Series, callback_status: str, callback_remark: str) -> bool:
    worksheet = ensure_call_log_sheet()
    if worksheet is None:
        return False

    record = {
        "call_id": safe_text(pd.Timestamp.now().strftime("%y%m%d%H%M%S%f"))[-10:],
        "call_datetime": cambodia_now_str(),
        "customer_name": safe_text(row_data.get("customer_name")),
        "customer_phone": safe_text(row_data.get("customer_phone")),
        "staff_id": safe_text(st.session_state.staff_id),
        "caller_name": safe_text(st.session_state.caller_name),
        "call_status": callback_status,
        "call_purpose": safe_text(row_data.get("call_purpose")),
        "remark": callback_remark.strip(),
    }
    return append_row_by_headers(worksheet, record)


# =========================================================
# UI HELPERS
# =========================================================
def queue_status_chip(value: str) -> str:
    palette = {
        "Pick Up": ("#dcfce7", "#166534"),
        "Not Pick Up": ("#fef3c7", "#92400e"),
        "No Answer": ("#ffedd5", "#9a3412"),
        "Busy": ("#dbeafe", "#1d4ed8"),
        "Wrong Number": ("#fee2e2", "#991b1b"),
        "Rejected": ("#fee2e2", "#991b1b"),
        "Completed": ("#e5e7eb", "#374151"),
    }
    bg, fg = palette.get(value, ("#e5e7eb", "#374151"))
    return f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{bg};color:{fg};font-size:12px;font-weight:700;'>{value}</span>"


def render_logo() -> None:
    logo_data = get_logo_base64()
    col1, col2 = st.columns([0.08, 0.92])
    with col1:
        if logo_data:
            st.markdown(f"<img src='data:image/png;base64,{logo_data}' width='58'>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='logo-fallback'>C</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(
            """
            <div style='padding-top:4px;'>
                <div style='font-size:20px;font-weight:900;color:#0f172a;'>Chip Mong Call Platform</div>
                <div style='font-size:12px;color:#6b7280;'>Sales calling activity system</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_phone_existence_notice(phone_input: str, df_all: pd.DataFrame) -> None:
    phone_clean = clean_phone_number(phone_input)
    if not phone_clean or len(phone_clean) < 8:
        return

    if df_all.empty:
        st.markdown(
            """
            <div class="phone-check-card phone-check-new">
                <div class="phone-check-title">✨ New phone number</div>
                <div class="phone-check-sub">No call record found yet for this number.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    match_df = df_all[df_all["phone_key"] == phone_clean].copy()
    if match_df.empty:
        st.markdown(
            """
            <div class="phone-check-card phone-check-new">
                <div class="phone-check-title">✨ New phone number</div>
                <div class="phone-check-sub">No call record found yet for this number.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    latest = match_df.sort_values("call_datetime", ascending=False, na_position="last").iloc[0]
    count_calls = len(match_df)

    last_time = fmt_datetime(latest.get("call_datetime"))
    last_name = safe_text(latest.get("customer_name")) or "-"
    last_staff = safe_text(latest.get("caller_name")) or safe_text(latest.get("staff_id")) or "-"
    last_status = safe_text(latest.get("call_status")) or "-"

    st.markdown(
        f"""
        <div class="phone-check-card phone-check-exists">
            <div class="phone-check-title">⚠️ Phone number already exists</div>
            <div class="phone-check-sub">
                <b>{phone_clean}</b> already has <b>{count_calls}</b> call record(s).<br>
                Latest: <b>{last_name}</b> • <b>{last_status}</b> • <b>{last_time}</b> • by <b>{last_staff}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PAGES
# =========================================================
def login_page() -> None:
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        render_logo()
        st.markdown(
            f"""
            <div style='margin-top:18px;font-size:52px;line-height:1.05;font-weight:900;color:#0f172a;max-width:780px;'>
                SALE CALL MANAGEMENT SYSTEM
            </div>
            <div class='motivation-box'>{MOTIVATION_QUOTE}</div>
            <div class='motivation-sign'>Start strong. Speak with purpose.</div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;margin-top:20px;'>Access</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='auth-note'>Login or create a new account. Registration will save to the <b>pw</b> sheet.</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register"])

        with login_tab:
            with st.form("login_form"):
                staff_id = st.text_input("Staff ID")
                password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Enter Interface", use_container_width=True, type="primary")

                if login_submitted:
                    if authenticate_user(staff_id, password):
                        profile = load_staff_profile(staff_id)
                        st.session_state.logged_in = True
                        st.session_state.staff_id = profile["staff_id"]
                        st.session_state.caller_name = profile["caller_name"]
                        st.session_state.user_role = profile["role"]
                        st.session_state.branch_name = profile["branch_name"]
                        st.session_state.branch_manager = profile["branch_manager"]
                        st.session_state["_pending_form_reset"] = False
                        reset_form()
                        st.rerun()

        with register_tab:
            with st.form("register_form"):
                new_staff_id = st.text_input("Staff ID")
                new_password = st.text_input("Create Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                register_submitted = st.form_submit_button("Create Account", use_container_width=True)

                if register_submitted:
                    if register_user(new_staff_id, new_password, confirm_password):
                        st.success("Account created successfully. Please login.")


def render_header(df_user: pd.DataFrame) -> None:
    today_local = now_ts().date()
    today_calls = len(df_user[df_user["call_datetime"].dt.date == today_local]) if not df_user.empty else 0
    picked_up = len(df_user[df_user["call_status"] == "Pick Up"]) if not df_user.empty else 0

    latest_calls = get_latest_calls_by_phone(df_user)
    pending_queue = len(latest_calls[latest_calls["call_status"].isin(CALLBACK_STATUSES)]) if not latest_calls.empty else 0

    left, right = st.columns([0.68, 0.32])

    with left:
        st.markdown(
            f"""
            <div style='font-size:34px;font-weight:900;letter-spacing:-0.03em;color:#0f172a;'>Call Activity Tracking System</div>
            <div style='margin-top:8px;font-size:14px;color:#6b7280;'>
                Logged in as <b>{safe_text(st.session_state.caller_name)}</b> ({safe_text(st.session_state.staff_id)}).<br>
                Cambodia time now: <b>{now_ts().strftime("%d %b %Y %H:%M:%S")}</b>
            </div>
            <div class='mini-stat-row'>
                <div class='mini-stat'>Today Calls: {today_calls}</div>
                <div class='mini-stat'>Pick Up: {picked_up}</div>
                <div class='mini-stat'>Need Callback: {pending_queue}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Refresh", use_container_width=True):
                st.rerun()
        with c2:
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.staff_id = ""
                st.session_state.caller_name = ""
                st.rerun()

    st.markdown("<hr style='margin:18px 0 8px 0;border:0;border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)


def page_new_call(df_user: pd.DataFrame, df_all: pd.DataFrame) -> None:
    apply_pending_form_reset()

    top1, top2 = st.columns([0.75, 0.25])

    with top1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>New Call Log</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='margin-top:4px;font-size:14px;color:#6b7280;'>Saved columns: call_id, call_datetime, customer_name, customer_phone, staff_id, caller_name, call_status, call_purpose, remark.</div>",
            unsafe_allow_html=True,
        )

    with top2:
        st.markdown(
            f"<div style='margin-top:6px;text-align:right;'><span style='display:inline-block;background:#166534;color:white;padding:8px 14px;border-radius:999px;font-size:13px;font-weight:700;'>{safe_text(st.session_state.caller_name)}</span></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    left, right = st.columns(2, gap="large")

    with left:
        st.text_input("Phone Number", key="form_phone", placeholder="012345678")
        render_phone_existence_notice(st.session_state.form_phone, df_all)
        st.text_input("Full Name", key="form_name", placeholder="Customer full name")
        st.selectbox("Call Purpose", PURPOSE_OPTIONS, key="form_purpose")
        if st.session_state.form_purpose == "Other":
            st.text_input("Specify Purpose", key="form_other_purpose")

    with right:
        st.selectbox("Call Status", STATUS_OPTIONS, key="form_status")
        st.text_area("Remark", key="form_remark", height=265, placeholder="Write what happened after the call.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Save", use_container_width=True, type="primary"):
            phone = clean_phone_number(st.session_state.form_phone)
            purpose = (
                st.session_state.form_other_purpose.strip()
                if st.session_state.form_purpose == "Other"
                else st.session_state.form_purpose
            )
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            elif save_new_call_to_sheet():
                st.rerun()

    with b2:
        if st.button("Save & New", use_container_width=True):
            phone = clean_phone_number(st.session_state.form_phone)
            purpose = (
                st.session_state.form_other_purpose.strip()
                if st.session_state.form_purpose == "Other"
                else st.session_state.form_purpose
            )
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            elif save_new_call_to_sheet():
                queue_form_reset()
                st.rerun()

    st.write("")
    st.markdown("<div style='font-size:22px;font-weight:900;color:#0f172a;margin:8px 0 12px 0;'>Recent Calls</div>", unsafe_allow_html=True)

    recent = df_user.sort_values("call_datetime", ascending=False).head(8).copy() if not df_user.empty else df_user.copy()
    if recent.empty:
        st.info("No calls yet.")
    else:
        recent_view = recent[
            [
                "call_datetime",
                "customer_phone",
                "customer_name",
                "call_purpose",
                "call_status",
                "remark",
            ]
        ].copy()
        recent_view["call_datetime"] = recent_view["call_datetime"].apply(fmt_datetime)
        recent_view = recent_view.rename(
            columns={
                "call_datetime": "Date",
                "customer_phone": "Phone",
                "customer_name": "Name",
                "call_purpose": "Purpose",
                "call_status": "Status",
                "remark": "Remark",
            }
        )
        st.dataframe(recent_view, use_container_width=True, hide_index=True)


def page_callback_queue(df_user: pd.DataFrame) -> None:
    st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Need Callback</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='margin-top:4px;font-size:14px;color:#6b7280;'>This list shows the latest customer record per phone number for {safe_text(st.session_state.caller_name)}. If the latest status is Not Pick Up, No Answer, or Busy, it stays here.</div>",
        unsafe_allow_html=True,
    )

    latest_calls = get_latest_calls_by_phone(df_user)
    queue_df = latest_calls[latest_calls["call_status"].isin(CALLBACK_STATUSES)].copy() if not latest_calls.empty else latest_calls.copy()
    queue_df = queue_df.sort_values("call_datetime", ascending=False, na_position="last")

    st.markdown(
        f"<div class='queue-note'>{len(queue_df)} customer(s) currently need callback.</div>",
        unsafe_allow_html=True,
    )

    if queue_df.empty:
        st.info("No pending callbacks.")
    else:
        for _, row in queue_df.iterrows():
            with st.expander(
                f"📞 {safe_text(row['customer_name'])} | {safe_text(row['customer_phone'])} | Last: {fmt_datetime(row['call_datetime'])}",
                expanded=False,
            ):
                a1, a2, a3, a4 = st.columns(4)

                with a1:
                    st.markdown("**Phone**")
                    st.write(safe_text(row["customer_phone"]))

                with a2:
                    st.markdown("**Purpose**")
                    st.write(safe_text(row["call_purpose"]) or "-")

                with a3:
                    st.markdown("**Previous Status**")
                    st.markdown(queue_status_chip(safe_text(row["call_status"])), unsafe_allow_html=True)

                with a4:
                    st.markdown("**Last Call**")
                    st.write(fmt_datetime(row["call_datetime"]))

                if safe_text(row["remark"]):
                    st.markdown(f"<div class='queue-note'>{safe_text(row['remark'])}</div>", unsafe_allow_html=True)

                callback_status = st.selectbox("New Call Status", STATUS_OPTIONS, key=f"queue_status_{row['_row_number']}")
                callback_remark = st.text_area("New Remark", key=f"queue_remark_{row['_row_number']}", height=120)

                if st.button("Save Callback Result", key=f"save_{row['_row_number']}", use_container_width=True, type="primary"):
                    if save_callback_result(row, callback_status, callback_remark):
                        st.success("Callback result saved")
                        st.rerun()


def page_history(df_user: pd.DataFrame) -> None:
    st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Call History</div>", unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns([1.2, 0.5, 0.5])
    with c1:
        st.text_input("Search Name / Phone", key="history_search")
    with c2:
        st.selectbox("Call Status", ["All"] + STATUS_OPTIONS, key="history_status")
    with c3:
        st.selectbox("Call Purpose", ["All"] + PURPOSE_OPTIONS, key="history_purpose")

    history_df = df_user.copy()

    if st.session_state.history_search.strip():
        q = st.session_state.history_search.strip().lower()
        history_df = history_df[
            history_df["customer_name"].astype(str).str.lower().str.contains(q, na=False)
            | history_df["customer_phone"].astype(str).str.lower().str.contains(q, na=False)
        ]

    if st.session_state.history_status != "All":
        history_df = history_df[history_df["call_status"] == st.session_state.history_status]

    if st.session_state.history_purpose != "All":
        history_df = history_df[history_df["call_purpose"] == st.session_state.history_purpose]

    history_df = history_df.sort_values("call_datetime", ascending=False)

    if history_df.empty:
        st.info("No history found.")
    else:
        view = history_df[
            [
                "call_datetime",
                "customer_phone",
                "customer_name",
                "call_purpose",
                "call_status",
                "remark",
            ]
        ].copy()
        view["call_datetime"] = view["call_datetime"].apply(fmt_datetime)
        view = view.rename(
            columns={
                "call_datetime": "Date",
                "customer_phone": "Phone",
                "customer_name": "Name",
                "call_purpose": "Purpose",
                "call_status": "Status",
                "remark": "Remark",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True, height=520)


def main_app() -> None:
    raw_df = get_call_log_data()
    df_all = normalize_call_log_df(raw_df)

    df_user = df_all[df_all["staff_id"] == safe_text(st.session_state.staff_id)].copy() if not df_all.empty else df_all.copy()

    render_header(df_user)

    new_tab, queue_tab, history_tab = st.tabs(
        ["📞 New Call Log", "🗂️ Need Callback", "🕘 Call History"]
    )

    with new_tab:
        page_new_call(df_user, df_all)

    with queue_tab:
        page_callback_queue(df_user)

    with history_tab:
        page_history(df_user)


# =========================================================
# RUN
# =========================================================
init_state()

if not st.session_state.logged_in:
    login_page()
else:
    main_app()
