import base64
import hashlib
import os
import re
import secrets
from datetime import datetime
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

# Put hyper user staff IDs here
HYPER_USER_IDS = {
    "90020759",
}

PURPOSE_OPTIONS = [
    "New Fee Charge",
    "Deliver Card/QR",
    "Inactive Card/Merchant",
    "Annual Fee",
    "Other", 
]

STATUS_OPTIONS = [
    "Pick Up",
    "Not Pick Up",
    "Busy",
    "Wrong Number",
    "Rejected",
]

CALLBACK_STATUSES = {"Not Pick Up", "Busy", "Wrong Number"}

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

        .loading-stage {
            min-height: 72vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .loading-card {
            width: 100%;
            max-width: 520px;
            background: rgba(255, 255, 255, 0.90);
            backdrop-filter: blur(10px);
            border: 1px solid #dbeafe;
            border-radius: 28px;
            padding: 40px 26px;
            text-align: center;
            box-shadow: 0 22px 50px rgba(15, 23, 42, 0.08);
        }

        .loading-illustration {
            position: relative;
            width: 150px;
            height: 150px;
            margin: 0 auto 18px auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .loading-gear {
            font-size: 110px;
            line-height: 1;
            color: #38bdf8;
            filter: drop-shadow(0 10px 20px rgba(56, 189, 248, 0.18));
            animation: spinGear 2.1s linear infinite;
        }

        .loading-core {
            position: absolute;
            width: 60px;
            height: 60px;
            border-radius: 999px;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            border: 6px solid #ffffff;
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.28);
        }

        .loading-lines {
            position: absolute;
            width: 92px;
            height: 92px;
            border-radius: 999px;
            animation: spinGearReverse 2.1s linear infinite;
        }

        .loading-lines::before,
        .loading-lines::after {
            content: "";
            position: absolute;
            left: 50%;
            top: 50%;
            width: 52px;
            height: 4px;
            background: #1f2937;
            border-radius: 999px;
            transform-origin: center;
        }

        .loading-lines::before {
            transform: translate(-50%, -50%) rotate(45deg);
        }

        .loading-lines::after {
            transform: translate(-50%, -50%) rotate(-45deg);
        }

        .loading-title {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 0.06em;
            color: #0f172a;
            margin-top: 10px;
        }

        .loading-subtitle {
            margin-top: 8px;
            font-size: 14px;
            color: #64748b;
            line-height: 1.7;
        }

        div[data-testid="stVerticalBlock"]:has(#save-btn-anchor) div[data-testid="stButton"] > button {
            background: #fecaca !important;
            color: #991b1b !important;
            border: 1px solid #fca5a5 !important;
        }

        div[data-testid="stVerticalBlock"]:has(#save-btn-anchor) div[data-testid="stButton"] > button:hover {
            background: #fca5a5 !important;
            color: #7f1d1d !important;
        }

        div[data-testid="stVerticalBlock"]:has(#save-new-btn-anchor) div[data-testid="stButton"] > button {
            background: #dcfce7 !important;
            color: #166534 !important;
            border: 1px solid #86efac !important;
        }

        div[data-testid="stVerticalBlock"]:has(#save-new-btn-anchor) div[data-testid="stButton"] > button:hover {
            background: #bbf7d0 !important;
            color: #14532d !important;
        }

        div[data-testid="stVerticalBlock"]:has(#save-btn-anchor) div[data-testid="stButton"] > button:disabled,
        div[data-testid="stVerticalBlock"]:has(#save-new-btn-anchor) div[data-testid="stButton"] > button:disabled {
            background: #f8fafc !important;
            color: #9ca3af !important;
            border: 1px solid #d1d5db !important;
        }

        @keyframes spinGear {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        @keyframes spinGearReverse {
            from { transform: rotate(360deg); }
            to { transform: rotate(0deg); }
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


def normalize_id(value) -> str:
    return safe_text(value).strip().lower()


def get_current_staff_id() -> str:
    return normalize_id(st.session_state.get("staff_id", ""))


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


def is_hyper_user() -> bool:
    current_staff_id = safe_text(st.session_state.get("staff_id", "")).strip().lower()
    hyper_ids = {safe_text(x).strip().lower() for x in HYPER_USER_IDS}
    return current_staff_id in hyper_ids


def get_super_user_staff_ids() -> set:
    """
    Super user logic from STAFF_SHEET_NAME = call_users.

    Sheet columns:
        Team Lead | ID | Name | Responsibility

    Rule:
    - Hyper user remains separate and can view all.
    - If current user is a Team Lead, they can view all callers under that Team Lead.
    - If current user has Responsibility = bm, they can view all callers under their Team Lead.
    - Normal user can view only their own calls.
    """
    current_staff_id = get_current_staff_id()

    if not current_staff_id:
        return set()

    staff_df = load_staff_master_df()
    if staff_df.empty:
        return {current_staff_id}

    staff_df = staff_df.copy()
    staff_df["staff_id_norm"] = staff_df["staff_id"].apply(normalize_id)
    staff_df["team_lead_id_norm"] = staff_df["team_lead_id"].apply(normalize_id)
    staff_df["responsibility_norm"] = staff_df["responsibility"].apply(normalize_id)

    current_rows = staff_df[staff_df["staff_id_norm"] == current_staff_id]

    if current_rows.empty:
        return {current_staff_id}

    current_row = current_rows.iloc[0]
    current_team_lead_id = normalize_id(current_row.get("team_lead_id_norm", ""))
    current_responsibility = normalize_id(current_row.get("responsibility_norm", ""))

    managed_team_leads = set()

    # Case 1: current user appears as a Team Lead in the sheet
    if current_staff_id in set(staff_df["team_lead_id_norm"]):
        managed_team_leads.add(current_staff_id)

    # Case 2: current user has Responsibility = bm
    if current_responsibility == "bm":
        if current_team_lead_id:
            managed_team_leads.add(current_team_lead_id)
        managed_team_leads.add(current_staff_id)

    # Not super user
    if not managed_team_leads:
        return {current_staff_id}

    team_members = staff_df[
        staff_df["team_lead_id_norm"].isin(managed_team_leads)
    ]["staff_id_norm"].tolist()

    allowed_ids = set(team_members)
    allowed_ids.add(current_staff_id)

    return allowed_ids


def is_super_user() -> bool:
    """
    Super user is different from Hyper user.
    Hyper user already has full access.
    """
    if is_hyper_user():
        return False

    current_staff_id = get_current_staff_id()
    allowed_ids = get_super_user_staff_ids()

    return len(allowed_ids - {current_staff_id}) > 0


def can_view_caller_columns() -> bool:
    """
    Hyper user and Super user should see Caller and Staff ID in tables.
    Normal caller should not.
    """
    return is_hyper_user() or is_super_user()


def get_scope_label() -> str:
    if is_hyper_user():
        return "All Calls In Sheet"
    if is_super_user():
        return "My Team Calls"
    return "My Calls Only"


def get_scope_df(df_all: pd.DataFrame) -> pd.DataFrame:
    if df_all.empty:
        return df_all.copy()

    # Hyper user keeps the same behavior
    if is_hyper_user():
        return df_all.copy()

    # Super user can view team calls
    if is_super_user():
        allowed_staff_ids = get_super_user_staff_ids()

        temp = df_all.copy()
        temp["staff_id_norm"] = temp["staff_id"].apply(normalize_id)

        scoped_df = temp[temp["staff_id_norm"].isin(allowed_staff_ids)].copy()
        scoped_df = scoped_df.drop(columns=["staff_id_norm"], errors="ignore")

        return scoped_df

    # Normal user can view own calls only
    return df_all[
        df_all["staff_id"].apply(normalize_id) == get_current_staff_id()
    ].copy()


def get_status_palette(status: str):
    palette = {
        "Pick Up": ("#dcfce7", "#166534"),
        "Not Pick Up": ("#fee2e2", "#991b1b"),
        "Busy": ("#dbeafe", "#1d4ed8"),
        "Wrong Number": ("#fce7f3", "#9d174d"),
        "Rejected": ("#fee2e2", "#991b1b"),
        "Completed": ("#e5e7eb", "#374151"),
    }
    return palette.get(status, ("#f1f5f9", "#334155"))


def style_status_dataframe(df: pd.DataFrame, status_col: str = "Status"):
    if df.empty or status_col not in df.columns:
        return df

    def _style_status(value):
        bg, fg = get_status_palette(safe_text(value))
        return (
            f"background-color: {bg};"
            f"color: {fg};"
            f"font-weight: 700;"
            f"text-align: center;"
        )

    try:
        styled = df.style.set_properties(**{
            "border": "none",
            "font-size": "13px",
        })

        if hasattr(styled, "map"):
            styled = styled.map(_style_status, subset=[status_col])
        elif hasattr(styled, "applymap"):
            styled = styled.applymap(_style_status, subset=[status_col])
        else:
            return df

        if hasattr(styled, "hide"):
            styled = styled.hide(axis="index")

        return styled
    except Exception:
        return df


def show_loading_screen(message: str = "Loading your call platform..."):
    placeholder = st.empty()
    placeholder.markdown(
        f"""
        <div class="loading-stage">
            <div class="loading-card">
                <div class="loading-illustration">
                    <div class="loading-gear">⚙</div>
                    <div class="loading-core"></div>
                    <div class="loading-lines"></div>
                </div>
                <div class="loading-title">LOADING</div>
                <div class="loading-subtitle">{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return placeholder


# =========================================================
# STREAMLIT STATE
# =========================================================
def ensure_form_state() -> None:
    defaults = {
        "form_phone": "",
        "form_name": "",
        "form_purpose": PURPOSE_OPTIONS[0],
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
    st.session_state.form_purpose = PURPOSE_OPTIONS[0]
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


@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    return setup_gsheets()


@st.cache_data(ttl=20, show_spinner=False)
def read_sheet_values(sheet_name: str):
    client = get_gsheet_client()
    if not client:
        return []

    workbook = client.open_by_key(SHEET_ID)
    worksheet = workbook.worksheet(sheet_name)
    return worksheet.get_all_values()


def clear_data_cache() -> None:
    st.cache_data.clear()


def ensure_password_sheet():
    client = get_gsheet_client()
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
        clear_data_cache()
        return worksheet

    all_values = worksheet.get_all_values()
    if not all_values:
        worksheet.append_row(PASSWORD_HEADERS)
        clear_data_cache()
        return worksheet

    current_headers = [safe_text(h) for h in all_values[0]]
    if current_headers != PASSWORD_HEADERS:
        worksheet.resize(rows=max(len(all_values), 1000), cols=len(PASSWORD_HEADERS))
        worksheet.update("A1", [PASSWORD_HEADERS])
        clear_data_cache()

    return worksheet


def ensure_call_log_sheet():
    client = get_gsheet_client()
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
        clear_data_cache()
        return worksheet

    all_values = worksheet.get_all_values()
    if not all_values:
        worksheet.append_row(CALL_LOG_HEADERS)
        clear_data_cache()
        return worksheet

    current_headers = [safe_text(h) for h in all_values[0]]
    if current_headers != CALL_LOG_HEADERS:
        worksheet.resize(rows=max(len(all_values), 1000), cols=len(CALL_LOG_HEADERS))
        worksheet.update("A1", [CALL_LOG_HEADERS])
        clear_data_cache()

    return worksheet


def append_row_by_headers(worksheet, record: dict) -> bool:
    try:
        headers = worksheet.row_values(1)
        row = [record.get(header, "") for header in headers]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        clear_data_cache()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


# =========================================================
# USER / AUTH
# =========================================================
def load_staff_master_df() -> pd.DataFrame:
    """
    Load staff master from STAFF_SHEET_NAME = call_users.

    Supported columns:
        Team Lead
        ID
        Name
        Responsibility

    Also supports older fallback names:
        staff_id, staff id, caller_name, role, branch, etc.
    """
    try:
        values = read_sheet_values(STAFF_SHEET_NAME)
        if not values:
            return pd.DataFrame()

        headers = [safe_text(h).lower().strip() for h in values[0]]
        rows = values[1:]
        if not rows:
            return pd.DataFrame()

        width = len(headers)
        normalized_rows = []
        for row in rows:
            padded = list(row) + [""] * (width - len(row))
            normalized_rows.append(padded[:width])

        df = pd.DataFrame(normalized_rows, columns=headers)

        def find_col(candidates):
            for col in candidates:
                if col in df.columns:
                    return col
            return None

        team_lead_col = find_col(["team lead", "team_lead", "teamlead"])
        id_col = find_col(["id", "staff_id", "staff id"])
        name_col = find_col(["name", "full_name", "staff_name", "caller_name"])
        responsibility_col = find_col(["responsibility", "role"])
        branch_col = find_col(["appreviation", "abbreviation", "branch_name", "branch"])

        out = pd.DataFrame()

        out["team_lead_id"] = (
            df[team_lead_col].astype(str).str.strip()
            if team_lead_col else ""
        )

        out["staff_id"] = (
            df[id_col].astype(str).str.strip()
            if id_col else ""
        )

        out["caller_name"] = (
            df[name_col].astype(str).str.strip()
            if name_col else out["staff_id"]
        )

        out["responsibility"] = (
            df[responsibility_col].astype(str).str.strip().str.lower()
            if responsibility_col else ""
        )

        out["role"] = out["responsibility"].replace("", "sales executive")

        out["branch_name"] = (
            df[branch_col].astype(str).str.strip()
            if branch_col else ""
        )

        # Existing code uses branch_manager in session_state.
        # Here we keep it as Team Lead ID.
        out["branch_manager"] = out["team_lead_id"]

        out = out[out["staff_id"] != ""].copy()

        return out[
            [
                "team_lead_id",
                "staff_id",
                "caller_name",
                "responsibility",
                "role",
                "branch_name",
                "branch_manager",
            ]
        ]

    except Exception as e:
        st.error(f"Staff master loading error: {e}")
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

    target_staff = normalize_id(staff_id)
    temp = df.copy()
    temp["staff_id_norm"] = temp["staff_id"].apply(normalize_id)

    row = temp[temp["staff_id_norm"] == target_staff]
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
        ensure_password_sheet()
        values = read_sheet_values(PASSWORD_SHEET_NAME)
        if not values:
            return False

        headers = [safe_text(h) for h in values[0]]
        rows = values[1:]
        if not rows:
            return False

        try:
            staff_idx = headers.index("staff_id")
        except ValueError:
            return False

        target = safe_text(staff_id)
        for row in rows:
            padded = list(row) + [""] * (len(headers) - len(row))
            if safe_text(padded[staff_idx]) == target:
                return True
        return False
    except Exception:
        return False


def authenticate_user(staff_id: str, password: str) -> bool:
    try:
        ensure_password_sheet()
        values = read_sheet_values(PASSWORD_SHEET_NAME)
        if not values:
            st.error("Password sheet not found")
            return False

        headers = [safe_text(h) for h in values[0]]
        rows = values[1:]
        if not rows:
            st.error("No users found")
            return False

        try:
            staff_idx = headers.index("staff_id")
            password_idx = headers.index("password")
            status_idx = headers.index("status")
        except ValueError:
            st.error("Password sheet structure is incorrect")
            return False

        target_staff = safe_text(staff_id)
        target_password = safe_text(password)

        for row in rows:
            padded = list(row) + [""] * (len(headers) - len(row))
            if safe_text(padded[staff_idx]) == target_staff:
                status = safe_text(padded[status_idx]).lower() or "active"
                stored_password = safe_text(padded[password_idx])

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
    try:
        values = read_sheet_values(CALL_LOG_SHEET_NAME)
    except Exception:
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
        df["phone_key"] = ""
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


def get_latest_calls_by_phone(df_scope: pd.DataFrame) -> pd.DataFrame:
    if df_scope.empty:
        return df_scope.copy()

    temp = df_scope.copy()
    temp = temp[temp["phone_key"] != ""].copy()
    temp = temp.sort_values("call_datetime", ascending=False, na_position="last")
    temp = temp.drop_duplicates(subset=["phone_key"], keep="first")
    return temp


def save_new_call_to_sheet(df_all: pd.DataFrame) -> bool:
    worksheet = ensure_call_log_sheet()
    if worksheet is None:
        return False

    phone_clean = clean_phone_number(st.session_state.form_phone)

    record = {
        "call_id": safe_text(pd.Timestamp.now().strftime("%y%m%d%H%M%S%f"))[-10:],
        "call_datetime": cambodia_now_str(),
        "customer_name": st.session_state.form_name.strip(),
        "customer_phone": phone_clean,
        "staff_id": safe_text(st.session_state.staff_id),
        "caller_name": safe_text(st.session_state.caller_name),
        "call_status": st.session_state.form_status,
        "call_purpose": st.session_state.form_purpose,
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
    bg, fg = get_status_palette(value)
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
                <div style='font-size:20px;font-weight:900;color:#0f172a;'>Chip Mong Bank</div>
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
            "<div class='auth-note'>Login to continue your work, or <b>create a new account</b> to get started. Click the <b>Register</b> panel to complete your <b>registration</b>.</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register"])

        with login_tab:
            with st.form("login_form"):
                staff_id = st.text_input("Staff ID")
                password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Enter", use_container_width=True, type="primary")

                if login_submitted:
                    with st.spinner("Authenticating..."):
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
                    with st.spinner("Creating account..."):
                        if register_user(new_staff_id, new_password, confirm_password):
                            st.success("Account created successfully. Please login.")


def render_header(df_scope: pd.DataFrame) -> None:
    today_local = now_ts().date()
    today_calls = len(df_scope[df_scope["call_datetime"].dt.date == today_local]) if not df_scope.empty else 0
    picked_up = len(df_scope[df_scope["call_status"] == "Pick Up"]) if not df_scope.empty else 0

    latest_calls = get_latest_calls_by_phone(df_scope)
    pending_queue = len(latest_calls[latest_calls["call_status"].isin(CALLBACK_STATUSES)]) if not latest_calls.empty else 0

    scope_label = get_scope_label()

    left, right = st.columns([0.68, 0.32])

    with left:
        st.markdown(
            f"""
            <div style='font-size:34px;font-weight:900;letter-spacing:-0.03em;color:#0f172a;'>CUSTOMER CALL ACTIVITY</div>
            <div style='margin-top:8px;font-size:14px;color:#6b7280;'>
                Logged in as <b>{safe_text(st.session_state.caller_name)}</b> ({safe_text(st.session_state.staff_id)}).<br>
                Data Scope: <b>{scope_label}</b><br>
                Cambodia time now: <b>{now_ts().strftime("%d %b %Y %H:%M:%S")}</b>
            </div>
            <div class='mini-stat-row'>
                <div class='mini-stat'>Today Calls: {today_calls}</div>
                <div class='mini-stat'>Pick Up: {picked_up}</div>
                <div class='mini-stat'>Need Callback: {pending_queue}</div>
                <div class='mini-stat'>Scope: {scope_label}</div>
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
            if st.button("Logout", use_container_width=True, type="primary"):
                st.session_state.logged_in = False
                st.session_state.staff_id = ""
                st.session_state.caller_name = ""
                st.session_state.user_role = "sales executive"
                st.session_state.branch_name = ""
                st.session_state.branch_manager = ""
                st.rerun()

    st.markdown("<hr style='margin:18px 0 8px 0;border:0;border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)


def page_new_call(df_scope: pd.DataFrame, df_all: pd.DataFrame) -> None:
    apply_pending_form_reset()

    top1, top2 = st.columns([0.62, 0.38])

    with top1:
        st.markdown(
            "<div style='font-size:28px;font-weight:900;color:#0f172a;'>New Call Log</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='margin-top:4px;font-size:14px;color:#6b7280;'>You can save the same phone number multiple times for follow-up.</div>",
            unsafe_allow_html=True,
        )

    with top2:
        if is_hyper_user():
            scope_badge = "HYPER USER"
        elif is_super_user():
            scope_badge = "SUPER USER / TEAM LEAD"
        else:
            scope_badge = safe_text(st.session_state.caller_name)

        st.markdown(
            f"""
            <div style='margin-top:6px;text-align:right;'>
                <span style='display:inline-block;background:#166534;color:white;padding:8px 14px;border-radius:999px;font-size:13px;font-weight:700;'>
                    {scope_badge}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    left, right = st.columns(2, gap="large")

    with left:
        st.text_input("Phone Number", key="form_phone", placeholder="012345678")
        st.text_input("Full Name", key="form_name", placeholder="Customer full name")
        st.selectbox("Call Purpose", PURPOSE_OPTIONS, key="form_purpose")

    with right:
        st.selectbox("Call Status", STATUS_OPTIONS, key="form_status")
        st.text_area("Remark", key="form_remark", height=265, placeholder="Write what happened after the call.")

    phone = clean_phone_number(st.session_state.form_phone)
    purpose = st.session_state.form_purpose
    form_ready = bool(phone and st.session_state.form_name.strip() and purpose)
    save_disabled = not form_ready

    b1, b2 = st.columns(2)

    with b1:
        st.markdown('<div id="save-btn-anchor"></div>', unsafe_allow_html=True)
        if st.button("Save", use_container_width=True, disabled=save_disabled):
            if not form_ready:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            else:
                with st.spinner("Saving call log..."):
                    if save_new_call_to_sheet(df_all):
                        st.toast("Call saved successfully")
                        st.rerun()

    with b2:
        st.markdown('<div id="save-new-btn-anchor"></div>', unsafe_allow_html=True)
        if st.button("Save & New", use_container_width=True, disabled=save_disabled):
            if not form_ready:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            else:
                with st.spinner("Saving and preparing a new form..."):
                    if save_new_call_to_sheet(df_all):
                        queue_form_reset()
                        st.toast("Call saved successfully")
                        st.rerun()

    st.write("")
    st.markdown(
        "<div style='font-size:22px;font-weight:900;color:#0f172a;margin:8px 0 12px 0;'>Recent Calls</div>",
        unsafe_allow_html=True,
    )

    # Hyper user sees all records; Super user and normal user use df_scope
    source_df = df_all if is_hyper_user() else df_scope

    recent = source_df.sort_values("call_datetime", ascending=False).head(8).copy() if not source_df.empty else source_df.copy()

    if recent.empty:
        st.info("No calls yet.")
    else:
        if can_view_caller_columns():
            recent_view = recent[
                [
                    "call_datetime",
                    "customer_phone",
                    "customer_name",
                    "caller_name",
                    "staff_id",
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
                    "caller_name": "Caller",
                    "staff_id": "Staff ID",
                    "call_purpose": "Purpose",
                    "call_status": "Status",
                    "remark": "Remark",
                }
            )
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

        st.dataframe(style_status_dataframe(recent_view), use_container_width=True)


def page_callback_queue(df_scope: pd.DataFrame) -> None:
    st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Need Callback</div>", unsafe_allow_html=True)

    if is_hyper_user():
        queue_scope_text = "This list shows the latest customer record per phone number across the whole sheet. If the latest status is Not Pick Up, Busy, or Wrong Number, it stays here."
    elif is_super_user():
        queue_scope_text = "This list shows the latest customer record per phone number for your team. If the latest status is Not Pick Up, Busy, or Wrong Number, it stays here."
    else:
        queue_scope_text = f"This list shows the latest customer record per phone number for {safe_text(st.session_state.caller_name)}. If the latest status is Not Pick Up, Busy, or Wrong Number, it stays here."

    st.markdown(
        f"<div style='margin-top:4px;font-size:14px;color:#6b7280;'>{queue_scope_text}</div>",
        unsafe_allow_html=True,
    )

    latest_calls = get_latest_calls_by_phone(df_scope)
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
                if can_view_caller_columns():
                    a1, a2, a3, a4, a5 = st.columns(5)

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

                    with a5:
                        st.markdown("**Last Caller**")
                        st.write(safe_text(row["caller_name"]) or safe_text(row["staff_id"]) or "-")
                else:
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
                    with st.spinner("Saving callback result..."):
                        if save_callback_result(row, callback_status, callback_remark):
                            st.success("Callback result saved")
                            st.rerun()


def page_history(df_scope: pd.DataFrame) -> None:
    st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Call History</div>", unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns([1.2, 0.5, 0.5])
    with c1:
        st.text_input("Search Name / Phone", key="history_search")
    with c2:
        st.selectbox("Call Status", ["All"] + STATUS_OPTIONS, key="history_status")
    with c3:
        st.selectbox("Call Purpose", ["All"] + PURPOSE_OPTIONS, key="history_purpose")

    history_df = df_scope.copy()

    if st.session_state.history_search.strip():
        q = st.session_state.history_search.strip().lower()
        if can_view_caller_columns():
            history_df = history_df[
                history_df["customer_name"].astype(str).str.lower().str.contains(q, na=False)
                | history_df["customer_phone"].astype(str).str.lower().str.contains(q, na=False)
                | history_df["caller_name"].astype(str).str.lower().str.contains(q, na=False)
                | history_df["staff_id"].astype(str).str.lower().str.contains(q, na=False)
            ]
        else:
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
        if can_view_caller_columns():
            view = history_df[
                [
                    "call_datetime",
                    "customer_phone",
                    "customer_name",
                    "caller_name",
                    "staff_id",
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
                    "caller_name": "Caller",
                    "staff_id": "Staff ID",
                    "call_purpose": "Purpose",
                    "call_status": "Status",
                    "remark": "Remark",
                }
            )
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

        st.dataframe(style_status_dataframe(view), use_container_width=True, height=520)


def main_app() -> None:
    loading_placeholder = show_loading_screen("Preparing call records and loading the latest activity...")

    raw_df = get_call_log_data()
    df_all = normalize_call_log_df(raw_df)
    df_scope = get_scope_df(df_all)

    loading_placeholder.empty()

    render_header(df_scope)

    new_tab, queue_tab, history_tab = st.tabs(
        ["📞 New Call Log", "🗂️ Need Callback", "🕘 Call History"]
    )

    with new_tab:
        page_new_call(df_scope, df_all)

    with queue_tab:
        page_callback_queue(df_scope)

    with history_tab:
        page_history(df_scope)


# =========================================================
# RUN
# =========================================================
init_state()

if not st.session_state.logged_in:
    login_page()
else:
    main_app()
