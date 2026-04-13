import base64
import os
import re
from datetime import date, datetime, timedelta

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Sale Call Management System",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SHEET_ID = "1FeAYu8jgE_R7IWjcDPjhXsmXvpn79GbVAMa_WU0mxQs"
FOLLOWUP_SHEET_NAME = "FollowUp"
PASSWORD_SHEET_NAME = "pw"
STAFF_SHEET_NAME = "call_users"
LOGO_PATH = "Logo-CMCB.png"

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

FOLLOWUP_REQUIRED_HEADERS = [
    "call_id",
    "call_datetime",
    "customer_name",
    "customer_phone",
    "staff_id",
    "caller_name",
    "call_status",
    "call_purpose",
    "remark",
    "next_action",
    "callback_date",
    "queue_status",
    "last_updated",
    "customer_id",
    "customer_business",
    "source",
    "product_interest",
    "bank_name",
    "interest",
    "amount_usd",
    "followup_date",
    "appointment_date",
    "status",
    "followup_count",
    "notes",
    "call_notes",
    "action_after_followup",
]

MOTIVATION_QUOTE = "Every call is a new chance to create trust, solve a need, and open the next opportunity."

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #f8fffb 0%, #f2f8f4 45%, #f8fafc 100%);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stAppViewBlockContainer"] > div:first-child > div:first-child > div:first-child:empty,
        #MainMenu,
        footer,
        header {
            visibility: hidden !important;
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 1.6rem !important;
            max-width: 1380px;
        }

        .hero-shell {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 28px;
            padding: 24px 28px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            margin-bottom: 18px;
        }

        .login-shell {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 32px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(22, 101, 52, 0.08);
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

        .soft-panel {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 28px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }

        .sub-panel {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 24px;
            padding: 20px;
        }

        .info-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 999px;
            background: white;
            border: 1px solid #dcfce7;
            color: #166534;
            font-size: 13px;
            font-weight: 700;
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
    </style>
    """,
    unsafe_allow_html=True,
)


def now_ts() -> datetime:
    return datetime.now()


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


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


def ensure_form_state() -> None:
    defaults = {
        "form_phone": "",
        "form_name": "",
        "form_purpose": "Welcome Call",
        "form_other_purpose": "",
        "form_status": "Pick Up",
        "form_callback_date": date.today() + timedelta(days=1),
        "form_remark": "",
        "queue_filter": "All Pending",
        "dashboard_scope": "My Calls",
        "history_search": "",
        "history_status": "All",
        "history_purpose": "All",
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
    st.session_state.form_callback_date = date.today() + timedelta(days=1)
    st.session_state.form_remark = ""


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


def ensure_followup_sheet():
    client = setup_gsheets()
    if not client:
        return None
    workbook = client.open_by_key(SHEET_ID)
    try:
        worksheet = workbook.worksheet(FOLLOWUP_SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = workbook.add_worksheet(title=FOLLOWUP_SHEET_NAME, rows=1000, cols=max(30, len(FOLLOWUP_REQUIRED_HEADERS)))
        worksheet.append_row(FOLLOWUP_REQUIRED_HEADERS)
        return worksheet

    all_values = worksheet.get_all_values()
    if not all_values:
        worksheet.append_row(FOLLOWUP_REQUIRED_HEADERS)
        return worksheet

    current_headers = [safe_text(h) for h in all_values[0]]
    merged_headers = current_headers[:]
    for header in FOLLOWUP_REQUIRED_HEADERS:
        if header not in merged_headers:
            merged_headers.append(header)
    if merged_headers != current_headers:
        worksheet.resize(rows=max(len(all_values), 1000), cols=len(merged_headers))
        worksheet.update("A1", [merged_headers])
    return worksheet


def append_record_to_sheet(worksheet, record: dict) -> bool:
    try:
        headers = worksheet.row_values(1)
        row = [record.get(header, "") for header in headers]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


def authenticate_user(staff_id: str, password: str) -> bool:
    try:
        worksheet = get_sheet(PASSWORD_SHEET_NAME)
        if worksheet is None:
            st.error("Password sheet not found")
            return False
        records = worksheet.get_all_records()
        for record in records:
            if safe_text(record.get("staff_id")) == safe_text(staff_id):
                status = safe_text(record.get("status")).lower()
                stored_password = safe_text(record.get("password"))
                if status != "active":
                    st.error("Account is not active")
                    return False
                if stored_password != safe_text(password):
                    st.error("Invalid password")
                    return False
                return True
        st.error("Staff ID not found")
        return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


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
        return out
    except Exception:
        return pd.DataFrame()


def load_staff_profile(staff_id: str) -> dict:
    df = load_staff_master_df()
    if df.empty:
        return {
            "staff_id": staff_id,
            "caller_name": staff_id,
            "role": "sales executive",
            "branch_name": "",
            "branch_manager": "",
        }
    row = df[df["staff_id"] == safe_text(staff_id)]
    if row.empty:
        return {
            "staff_id": staff_id,
            "caller_name": staff_id,
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


def get_followup_data() -> pd.DataFrame:
    worksheet = ensure_followup_sheet()
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


def normalize_followup_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        if col == "_row_number":
            continue
        df[col] = df[col].apply(safe_text)

    for col in [
        "staff_id",
        "customer_name",
        "customer_phone",
        "call_status",
        "call_purpose",
        "remark",
        "next_action",
        "queue_status",
        "last_updated",
        "call_datetime",
        "callback_date",
        "notes",
        "call_notes",
        "followup_date",
        "caller_name",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["customer_phone"] = df["customer_phone"].where(df["customer_phone"] != "", df.get("phone_number", ""))
    if "phone_number" not in df.columns:
        df["phone_number"] = df["customer_phone"]

    df["remark"] = df["remark"].where(df["remark"] != "", df["notes"])
    df["remark"] = df["remark"].where(df["remark"] != "", df["call_notes"])
    df["call_purpose"] = df["call_purpose"].where(df["call_purpose"] != "", df.get("source", ""))

    df["call_datetime"] = df["call_datetime"].where(df["call_datetime"] != "", df["last_updated"])
    df["call_datetime"] = pd.to_datetime(df["call_datetime"], errors="coerce")
    df["callback_date"] = df["callback_date"].where(df["callback_date"] != "", df["followup_date"])
    df["callback_date"] = pd.to_datetime(df["callback_date"], errors="coerce")
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")

    derived_queue = []
    for _, row in df.iterrows():
        queue_status = safe_text(row.get("queue_status"))
        next_action = safe_text(row.get("next_action")).lower()
        call_status = safe_text(row.get("call_status"))
        action_after = safe_text(row.get("action_after_followup")).lower()
        if queue_status:
            derived_queue.append(queue_status)
        elif call_status in CALLBACK_STATUSES and action_after not in {"completed", "closed"}:
            derived_queue.append("Pending Callback")
        elif next_action in {"call back", "follow up"} and action_after not in {"completed", "closed"}:
            derived_queue.append("Pending Callback")
        else:
            derived_queue.append("Closed")
    df["queue_status"] = derived_queue
    df["staff_id"] = df["staff_id"].astype(str).str.strip()
    df["caller_name"] = df["caller_name"].where(df["caller_name"] != "", df["staff_id"])
    return df


def filter_data_by_role(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    current_id = safe_text(st.session_state.staff_id)
    current_role = safe_text(st.session_state.user_role).lower()
    staff_master = load_staff_master_df()

    is_admin = current_id == "90020759" or "admin" in current_role
    if is_admin:
        return df

    if current_role in ["branch manager", "bm", "branch head"] and not staff_master.empty:
        managed_staff = staff_master[
            (staff_master["branch_manager"] == current_id) | (staff_master["staff_id"] == current_id)
        ]["staff_id"].astype(str).str.strip().unique().tolist()
        return df[df["staff_id"].isin(managed_staff)].copy()

    return df[df["staff_id"] == current_id].copy()


def queue_status_chip(value: str) -> str:
    palette = {
        "Pick Up": ("#dcfce7", "#166534"),
        "Not Pick Up": ("#fef3c7", "#92400e"),
        "No Answer": ("#ffedd5", "#9a3412"),
        "Busy": ("#dbeafe", "#1d4ed8"),
        "Wrong Number": ("#fee2e2", "#991b1b"),
        "Rejected": ("#fee2e2", "#991b1b"),
        "Pending Callback": ("#fef3c7", "#92400e"),
        "Closed": ("#e5e7eb", "#374151"),
        "Completed": ("#e5e7eb", "#374151"),
    }
    bg, fg = palette.get(value, ("#e5e7eb", "#374151"))
    return f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;background:{bg};color:{fg};font-size:12px;font-weight:700;'>{value}</span>"


def save_new_call_to_sheet() -> bool:
    worksheet = ensure_followup_sheet()
    if worksheet is None:
        return False

    phone_clean = clean_phone_number(st.session_state.form_phone)
    purpose = st.session_state.form_other_purpose.strip() if st.session_state.form_purpose == "Other" else st.session_state.form_purpose
    status = st.session_state.form_status
    callback_date = st.session_state.form_callback_date.strftime("%Y-%m-%d") if status in CALLBACK_STATUSES else ""
    now_string = now_ts().strftime("%Y-%m-%d %H:%M:%S")

    record = {
        "call_id": safe_text(pd.Timestamp.now().strftime("%y%m%d%H%M%S%f"))[-10:],
        "call_datetime": now_string,
        "customer_name": st.session_state.form_name.strip(),
        "customer_phone": phone_clean,
        "phone_number": phone_clean,
        "staff_id": safe_text(st.session_state.staff_id),
        "caller_name": safe_text(st.session_state.caller_name),
        "call_status": status,
        "call_purpose": purpose,
        "remark": st.session_state.form_remark.strip(),
        "notes": st.session_state.form_remark.strip(),
        "call_notes": st.session_state.form_remark.strip(),
        "next_action": "Call Back" if status in CALLBACK_STATUSES else "",
        "callback_date": callback_date,
        "followup_date": callback_date,
        "queue_status": "Pending Callback" if status in CALLBACK_STATUSES else "Closed",
        "last_updated": now_string,
        "status": "Pending Callback" if status in CALLBACK_STATUSES else "Closed",
        "followup_count": "1",
        "action_after_followup": "",
        "customer_id": "",
        "customer_business": "",
        "source": "",
        "product_interest": "",
        "bank_name": "",
        "interest": "",
        "amount_usd": "",
        "appointment_date": "",
    }
    return append_record_to_sheet(worksheet, record)


def update_followup_row(row_number: int, updates: dict) -> bool:
    try:
        worksheet = ensure_followup_sheet()
        if worksheet is None:
            return False
        headers = worksheet.row_values(1)
        for key, value in updates.items():
            if key in headers:
                col_idx = headers.index(key) + 1
                worksheet.update_cell(row_number, col_idx, value)
        return True
    except Exception as e:
        st.error(f"Update error: {e}")
        return False


def save_callback_result(row_data: pd.Series, callback_status: str, callback_date, callback_remark: str) -> bool:
    worksheet = ensure_followup_sheet()
    if worksheet is None:
        return False
    now_string = now_ts().strftime("%Y-%m-%d %H:%M:%S")
    next_callback = callback_date.strftime("%Y-%m-%d") if callback_status in CALLBACK_STATUSES else ""

    record = {
        "call_id": safe_text(pd.Timestamp.now().strftime("%y%m%d%H%M%S%f"))[-10:],
        "call_datetime": now_string,
        "customer_name": safe_text(row_data.get("customer_name")),
        "customer_phone": safe_text(row_data.get("customer_phone")),
        "phone_number": safe_text(row_data.get("customer_phone")),
        "staff_id": safe_text(st.session_state.staff_id),
        "caller_name": safe_text(st.session_state.caller_name),
        "call_status": callback_status,
        "call_purpose": safe_text(row_data.get("call_purpose")),
        "remark": callback_remark.strip(),
        "notes": callback_remark.strip(),
        "call_notes": callback_remark.strip(),
        "next_action": "Call Back" if callback_status in CALLBACK_STATUSES else "",
        "callback_date": next_callback,
        "followup_date": next_callback,
        "queue_status": "Pending Callback" if callback_status in CALLBACK_STATUSES else "Closed",
        "last_updated": now_string,
        "status": "Pending Callback" if callback_status in CALLBACK_STATUSES else "Closed",
        "followup_count": "1",
        "action_after_followup": "",
        "customer_id": safe_text(row_data.get("customer_id")),
        "customer_business": safe_text(row_data.get("customer_business")),
        "source": safe_text(row_data.get("source")),
        "product_interest": safe_text(row_data.get("product_interest")),
        "bank_name": safe_text(row_data.get("bank_name")),
        "interest": safe_text(row_data.get("interest")),
        "amount_usd": safe_text(row_data.get("amount_usd")),
        "appointment_date": "",
    }
    created = append_record_to_sheet(worksheet, record)
    if not created:
        return False

    row_number = int(row_data.get("_row_number"))
    return update_followup_row(
        row_number,
        {
            "queue_status": "Completed",
            "status": "Completed",
            "action_after_followup": "Completed",
            "last_updated": now_string,
        },
    )


def complete_queue_item(row_data: pd.Series) -> bool:
    row_number = int(row_data.get("_row_number"))
    now_string = now_ts().strftime("%Y-%m-%d %H:%M:%S")
    return update_followup_row(
        row_number,
        {
            "queue_status": "Completed",
            "status": "Completed",
            "action_after_followup": "Completed",
            "last_updated": now_string,
        },
    )


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
        st.markdown("<div class='login-shell'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Login</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:6px;font-size:14px;color:#6b7280;'>Use your existing User ID and password from the Google Sheet.</div>", unsafe_allow_html=True)
        st.write("")
        with st.form("login_form"):
            staff_id = st.text_input("User ID")
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
                    reset_form()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_header(user_df: pd.DataFrame) -> None:
    today_calls = len(user_df[user_df["call_datetime"].dt.date == date.today()]) if not user_df.empty else 0
    picked_up = len(user_df[user_df["call_status"] == "Pick Up"]) if not user_df.empty else 0
    pending_queue = len(user_df[user_df["queue_status"] == "Pending Callback"]) if not user_df.empty else 0

    st.markdown("<div class='hero-shell'>", unsafe_allow_html=True)
    left, right = st.columns([0.68, 0.32])
    with left:
        st.markdown(
            f"""
            <div style='font-size:34px;font-weight:900;letter-spacing:-0.03em;color:#0f172a;'>Call Activity Tracking System</div>
            <div style='margin-top:8px;font-size:14px;color:#6b7280;'>
                Logged in as <b>{safe_text(st.session_state.caller_name)}</b> ({safe_text(st.session_state.staff_id)}). Personal queue and history are filtered by the logged-in salesperson.
            </div>
            <div class='mini-stat-row'>
                <div class='mini-stat'>Today Calls: {today_calls}</div>
                <div class='mini-stat'>Pick Up: {picked_up}</div>
                <div class='mini-stat'>Pending Queue: {pending_queue}</div>
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
    st.markdown("</div>", unsafe_allow_html=True)


def page_new_call(df_user: pd.DataFrame) -> None:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    top1, top2 = st.columns([0.75, 0.25])
    with top1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>New Call Log</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:4px;font-size:14px;color:#6b7280;'>Only the simplified fields remain: phone, name, purpose, status, callback date, and remark.</div>", unsafe_allow_html=True)
    with top2:
        st.markdown(
            f"<div style='margin-top:6px;text-align:right;'><span style='display:inline-block;background:#166534;color:white;padding:8px 14px;border-radius:999px;font-size:13px;font-weight:700;'>{safe_text(st.session_state.caller_name)}</span></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("<div class='sub-panel'>", unsafe_allow_html=True)
        st.text_input("Phone Number", key="form_phone", placeholder="012345678")
        st.text_input("Full Name", key="form_name", placeholder="Customer full name")
        st.selectbox("Call Purpose", PURPOSE_OPTIONS, key="form_purpose")
        if st.session_state.form_purpose == "Other":
            st.text_input("Specify Purpose", key="form_other_purpose")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='sub-panel'>", unsafe_allow_html=True)
        st.selectbox("Call Status", STATUS_OPTIONS, key="form_status")
        if st.session_state.form_status in CALLBACK_STATUSES:
            st.date_input("Callback Date", key="form_callback_date", min_value=date.today())
        st.text_area("Remark", key="form_remark", height=220, placeholder="Write what happened after the call...")
        st.markdown("</div>", unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Save", use_container_width=True, type="primary"):
            phone = clean_phone_number(st.session_state.form_phone)
            purpose = st.session_state.form_other_purpose.strip() if st.session_state.form_purpose == "Other" else st.session_state.form_purpose
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            elif save_new_call_to_sheet():
                st.success("Call saved successfully")
                st.rerun()
    with b2:
        if st.button("Save & New", use_container_width=True):
            phone = clean_phone_number(st.session_state.form_phone)
            purpose = st.session_state.form_other_purpose.strip() if st.session_state.form_purpose == "Other" else st.session_state.form_purpose
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            elif save_new_call_to_sheet():
                reset_form()
                st.success("Call saved successfully")
                st.rerun()

    st.write("")
    st.markdown("<div style='font-size:22px;font-weight:900;color:#0f172a;margin:8px 0 12px 0;'>Recent Calls</div>", unsafe_allow_html=True)
    recent = df_user.sort_values("call_datetime", ascending=False).head(8).copy() if not df_user.empty else df_user.copy()
    if recent.empty:
        st.info("No calls yet.")
    else:
        recent_view = recent[["call_datetime", "customer_phone", "customer_name", "call_purpose", "call_status", "queue_status", "remark"]].copy()
        recent_view["call_datetime"] = recent_view["call_datetime"].apply(fmt_datetime)
        recent_view = recent_view.rename(
            columns={
                "call_datetime": "Date",
                "customer_phone": "Phone",
                "customer_name": "Name",
                "call_purpose": "Purpose",
                "call_status": "Status",
                "queue_status": "Queue",
                "remark": "Remark",
            }
        )
        st.dataframe(recent_view, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page_unpicked_queue(df_user: pd.DataFrame) -> None:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    top1, top2 = st.columns([0.72, 0.28])
    with top1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Unpicked Up Queue</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='margin-top:4px;font-size:14px;color:#6b7280;'>Only {safe_text(st.session_state.caller_name)} sees this queue after login, so the same salesperson can call the customer again later.</div>",
            unsafe_allow_html=True,
        )
    with top2:
        st.selectbox("Queue Filter", ["All Pending", "Overdue", "Due Today", "Upcoming"], key="queue_filter")

    queue_df = df_user[df_user["queue_status"] == "Pending Callback"].copy() if not df_user.empty else df_user.copy()
    if st.session_state.queue_filter == "Overdue":
        queue_df = queue_df[queue_df["callback_date"].notna() & (queue_df["callback_date"].dt.date < date.today())]
    elif st.session_state.queue_filter == "Due Today":
        queue_df = queue_df[queue_df["callback_date"].notna() & (queue_df["callback_date"].dt.date == date.today())]
    elif st.session_state.queue_filter == "Upcoming":
        queue_df = queue_df[queue_df["callback_date"].notna() & (queue_df["callback_date"].dt.date > date.today())]

    queue_df = queue_df.sort_values(["callback_date", "call_datetime"], ascending=[True, False], na_position="last")

    st.markdown(
        f"<div class='queue-note'>{len(queue_df)} customer(s) in {safe_text(st.session_state.caller_name)}'s queue.</div>",
        unsafe_allow_html=True,
    )

    if queue_df.empty:
        st.info("No pending callbacks in this view.")
    else:
        for _, row in queue_df.iterrows():
            callback_label = row["callback_date"].strftime("%Y-%m-%d") if pd.notna(row["callback_date"]) else "-"
            with st.expander(f"📞 {safe_text(row['customer_name'])} | {safe_text(row['customer_phone'])} | Callback: {callback_label}", expanded=False):
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

                callback_status = st.selectbox("Callback Status", STATUS_OPTIONS, key=f"queue_status_{row['_row_number']}")
                callback_date = st.date_input("Next Callback Date", value=date.today() + timedelta(days=1), min_value=date.today(), key=f"queue_date_{row['_row_number']}")
                callback_remark = st.text_area("New Remark", key=f"queue_remark_{row['_row_number']}", height=120)
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Save Result", key=f"save_{row['_row_number']}", use_container_width=True, type="primary"):
                        if save_callback_result(row, callback_status, callback_date, callback_remark):
                            st.success("Callback result saved")
                            st.rerun()
                with b2:
                    if st.button("Close Item", key=f"close_{row['_row_number']}", use_container_width=True):
                        if complete_queue_item(row):
                            st.success("Queue item closed")
                            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def page_history(df_user: pd.DataFrame) -> None:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
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
            history_df["customer_name"].astype(str).str.lower().str.contains(q)
            | history_df["customer_phone"].astype(str).str.lower().str.contains(q)
        ]
    if st.session_state.history_status != "All":
        history_df = history_df[history_df["call_status"] == st.session_state.history_status]
    if st.session_state.history_purpose != "All":
        history_df = history_df[history_df["call_purpose"] == st.session_state.history_purpose]

    history_df = history_df.sort_values("call_datetime", ascending=False)
    if history_df.empty:
        st.info("No history found.")
    else:
        view = history_df[["call_datetime", "customer_phone", "customer_name", "call_purpose", "call_status", "queue_status", "remark"]].copy()
        view["call_datetime"] = view["call_datetime"].apply(fmt_datetime)
        view = view.rename(
            columns={
                "call_datetime": "Date",
                "customer_phone": "Phone",
                "customer_name": "Name",
                "call_purpose": "Purpose",
                "call_status": "Status",
                "queue_status": "Queue",
                "remark": "Remark",
            }
        )
        st.dataframe(view, use_container_width=True, hide_index=True, height=520)
    st.markdown("</div>", unsafe_allow_html=True)


def page_dashboard(df_all: pd.DataFrame, df_user: pd.DataFrame) -> None:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    top1, top2 = st.columns([0.72, 0.28])
    with top1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Dashboard</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:4px;font-size:14px;color:#6b7280;'>Monitor personal performance or switch to role-based overall view.</div>", unsafe_allow_html=True)
    with top2:
        st.selectbox("Dashboard Scope", ["My Calls", "Role View"], key="dashboard_scope")

    role_df = filter_data_by_role(df_all)
    scope_df = df_user.copy() if st.session_state.dashboard_scope == "My Calls" else role_df.copy()

    if scope_df.empty:
        st.info("No data available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total_calls = len(scope_df)
    picked_up = len(scope_df[scope_df["call_status"] == "Pick Up"])
    pending_callbacks = len(scope_df[scope_df["queue_status"] == "Pending Callback"])
    today_calls = len(scope_df[scope_df["call_datetime"].dt.date == date.today()])

    st.markdown(
        f"""
        <div class='mini-stat-row'>
            <div class='mini-stat'>Total Calls: {total_calls}</div>
            <div class='mini-stat'>Pick Up: {picked_up}</div>
            <div class='mini-stat'>Pending Callback: {pending_callbacks}</div>
            <div class='mini-stat'>Today Calls: {today_calls}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status_counts = scope_df["call_status"].replace("", "Unknown").fillna("Unknown").value_counts().reset_index()
    status_counts.columns = ["Call Status", "Count"]
    fig_status = px.bar(status_counts, x="Call Status", y="Count", text="Count", title="Call Status Breakdown")
    fig_status.update_traces(textposition="outside")
    fig_status.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")

    purpose_counts = scope_df["call_purpose"].replace("", "Unknown").fillna("Unknown").value_counts().reset_index()
    purpose_counts.columns = ["Call Purpose", "Count"]
    fig_purpose = px.pie(purpose_counts, names="Call Purpose", values="Count", hole=0.45, title="Call Purpose Distribution")
    fig_purpose.update_layout(paper_bgcolor="rgba(0,0,0,0)")

    trend_df = scope_df[scope_df["call_datetime"].notna()].copy()
    trend_df["call_day"] = trend_df["call_datetime"].dt.date
    trend_df = trend_df.groupby("call_day", as_index=False).size().rename(columns={"size": "Count"})
    fig_trend = px.line(trend_df, x="call_day", y="Count", markers=True, title="Daily Call Trend")
    fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(fig_status, use_container_width=True)
    with c2:
        st.plotly_chart(fig_purpose, use_container_width=True)

    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def main_app() -> None:
    raw_df = get_followup_data()
    df_all = normalize_followup_df(raw_df)
    df_user = df_all[df_all["staff_id"] == safe_text(st.session_state.staff_id)].copy() if not df_all.empty else df_all.copy()

    render_header(df_user)

    new_tab, queue_tab, history_tab, dashboard_tab = st.tabs(
        ["📞 New Call Log", "🗂️ Unpicked Up Queue", "🕘 Call History", "📊 Dashboard"]
    )

    with new_tab:
        page_new_call(df_user)
    with queue_tab:
        page_unpicked_queue(df_user)
    with history_tab:
        page_history(df_user)
    with dashboard_tab:
        page_dashboard(df_all, df_user)


init_state()

if not st.session_state.logged_in:
    login_page()
else:
    main_app()
