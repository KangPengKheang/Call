import uuid
from datetime import date, datetime, timedelta
import os
import re

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Call Activity Tracking System", page_icon="📞", layout="wide")

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

DEMO_USERS = [
    {"user_id": "90020759", "password": "123456", "name": "Demo User", "role": "Sales Executive"},
    {"user_id": "10010203", "password": "123456", "name": "Rina", "role": "Sales Executive"},
    {"user_id": "10010204", "password": "123456", "name": "Dara", "role": "Sales Executive"},
]


def make_id() -> str:
    return uuid.uuid4().hex[:10].upper()


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def plus_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def fmt_datetime(value: str) -> str:
    try:
        return pd.to_datetime(value).strftime("%d %b %Y %H:%M")
    except Exception:
        return str(value)


def clean_phone(phone: str) -> str:
    phone = str(phone).strip()
    phone = re.sub(r"[^0-9+]", "", phone)
    phone = re.sub(r"^\+?855", "0", phone)
    phone = re.sub(r"^855", "0", phone)
    if phone and not phone.startswith("0"):
        phone = f"0{phone}"
    return phone


def seed_logs():
    return [
        {
            "call_id": make_id(),
            "call_datetime": (datetime.now() - timedelta(hours=2)).isoformat(),
            "staff_id": "90020759",
            "caller_name": "Demo User",
            "phone_number": "012345678",
            "customer_name": "Sok Vanna",
            "call_purpose": "Promotion",
            "call_status": "Pick Up",
            "remark": "Customer answered and listened to promotion.",
            "callback_date": "",
            "queue_status": "Closed",
        },
        {
            "call_id": make_id(),
            "call_datetime": (datetime.now() - timedelta(hours=26)).isoformat(),
            "staff_id": "90020759",
            "caller_name": "Demo User",
            "phone_number": "098888222",
            "customer_name": "Chan Dara",
            "call_purpose": "Reminder",
            "call_status": "Not Pick Up",
            "remark": "No answer on first try.",
            "callback_date": today_str(),
            "queue_status": "Pending Callback",
        },
        {
            "call_id": make_id(),
            "call_datetime": (datetime.now() - timedelta(hours=49)).isoformat(),
            "staff_id": "10010203",
            "caller_name": "Rina",
            "phone_number": "011222333",
            "customer_name": "Pich Sreypov",
            "call_purpose": "Survey",
            "call_status": "Busy",
            "remark": "Asked us to call back tomorrow.",
            "callback_date": plus_days(1),
            "queue_status": "Pending Callback",
        },
        {
            "call_id": make_id(),
            "call_datetime": (datetime.now() - timedelta(hours=5)).isoformat(),
            "staff_id": "10010204",
            "caller_name": "Dara",
            "phone_number": "097777111",
            "customer_name": "Mey Linda",
            "call_purpose": "Welcome Call",
            "call_status": "No Answer",
            "remark": "Need to try again in the afternoon.",
            "callback_date": plus_days(1),
            "queue_status": "Pending Callback",
        },
    ]


def init_state() -> None:
    if "logged_user" not in st.session_state:
        st.session_state.logged_user = None
    if "call_logs" not in st.session_state:
        st.session_state.call_logs = seed_logs()
    if "login_user_id" not in st.session_state:
        st.session_state.login_user_id = "90020759"
    if "login_password" not in st.session_state:
        st.session_state.login_password = "123456"
    if "queue_filter" not in st.session_state:
        st.session_state.queue_filter = "All Pending"
    if "dashboard_scope" not in st.session_state:
        st.session_state.dashboard_scope = "My Calls"
    if "history_search" not in st.session_state:
        st.session_state.history_search = ""
    if "history_status" not in st.session_state:
        st.session_state.history_status = "All"
    if "history_purpose" not in st.session_state:
        st.session_state.history_purpose = "All"
    if "form_phone" not in st.session_state:
        reset_form()


def reset_form() -> None:
    st.session_state.form_phone = ""
    st.session_state.form_name = ""
    st.session_state.form_purpose = "Welcome Call"
    st.session_state.form_other_purpose = ""
    st.session_state.form_status = "Pick Up"
    st.session_state.form_callback_date = plus_days(1)
    st.session_state.form_remark = ""


def get_df() -> pd.DataFrame:
    df = pd.DataFrame(st.session_state.call_logs)
    if df.empty:
        return pd.DataFrame(
            columns=[
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
            ]
        )
    return df


def get_user_df() -> pd.DataFrame:
    df = get_df()
    user = st.session_state.logged_user
    if not user:
        return df.iloc[0:0]
    return df[df["staff_id"].astype(str).str.strip() == str(user["user_id"]).strip()].copy()


def add_log(record: dict) -> None:
    st.session_state.call_logs = [record] + st.session_state.call_logs


def update_queue_item(call_id: str, new_queue_status: str) -> None:
    updated = []
    for row in st.session_state.call_logs:
        if row["call_id"] == call_id:
            row = {**row, "queue_status": new_queue_status}
        updated.append(row)
    st.session_state.call_logs = updated


def metric_box(title: str, value: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_chip(value: str) -> str:
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


def load_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f8fffb 0%, #f1f7f3 45%, #f8fafc 100%);
        }
        .hero-box {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 28px;
            padding: 24px 28px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }
        .login-shell {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 32px;
            padding: 32px;
            box-shadow: 0 20px 40px rgba(22, 101, 52, 0.08);
        }
        .metric-box {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            padding: 16px 18px;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
        }
        .metric-title {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6b7280;
        }
        .metric-value {
            margin-top: 8px;
            font-size: 30px;
            line-height: 1;
            font-weight: 900;
            color: #0f172a;
        }
        .metric-sub {
            margin-top: 6px;
            font-size: 12px;
            color: #6b7280;
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
        .logo-fallback {
            width: 56px;
            height: 56px;
            border-radius: 18px;
            background: linear-gradient(135deg, #166534 0%, #10b981 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 900;
        }
        button[kind="secondaryFormSubmit"] {
            border-radius: 16px !important;
        }
        button[kind="primaryFormSubmit"] {
            border-radius: 16px !important;
        }
        .stButton > button {
            border-radius: 16px;
            height: 44px;
            font-weight: 700;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 28px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 0;
            background: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 54px;
            background: transparent;
            border: none;
            color: #374151;
            font-size: 15px;
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


def render_logo() -> None:
    col1, col2 = st.columns([0.08, 0.92])
    logo_path = "logo-cmcb.png"
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, width=56)
        else:
            st.markdown("<div class='logo-fallback'>C</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(
            """
            <div style='padding-top:4px;'>
                <div style='font-size:20px;font-weight:900;color:#0f172a;'>Chip Mong Call Platform</div>
                <div style='font-size:12px;color:#6b7280;'>Sales calling activity interface preview</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def login_view() -> None:
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.markdown(
            """
            <div style='display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:white;border:1px solid #dcfce7;color:#166534;font-size:13px;font-weight:700;'>
                Modern sales call interface preview
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        render_logo()
        st.markdown(
            """
            <div style='margin-top:18px;font-size:52px;line-height:1.05;font-weight:900;color:#0f172a;max-width:800px;'>
                A cleaner calling workflow for every salesperson.
            </div>
            <div style='margin-top:18px;max-width:720px;font-size:17px;line-height:1.8;color:#475569;'>
                This Python prototype is designed for your future Streamlit production flow. Login can later connect directly to the sheet that stores user ID and password for each salesperson.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_box("Personal Queue", "By Login", "Each salesperson sees only their own callbacks")
        with c2:
            metric_box("Call History", "Per Sale", "History is filtered by logged-in account")
        with c3:
            metric_box("Dashboard", "Live View", "Can switch between personal and overall view")

    with right:
        st.markdown("<div class='login-shell'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Login</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:6px;font-size:14px;color:#6b7280;'>Later, this will connect directly to your user_ID and password sheet.</div>", unsafe_allow_html=True)
        st.write("")
        with st.form("login_form"):
            st.text_input("User ID", key="login_user_id")
            st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Enter Interface", use_container_width=True, type="primary")
            if submitted:
                user = next(
                    (
                        row
                        for row in DEMO_USERS
                        if row["user_id"] == st.session_state.login_user_id.strip()
                        and row["password"] == st.session_state.login_password
                    ),
                    None,
                )
                if user:
                    st.session_state.logged_user = user
                    st.rerun()
                else:
                    st.error("Invalid User ID or password")
        st.info("Demo users: 90020759 / 123456, 10010203 / 123456, 10010204 / 123456")
        st.markdown("</div>", unsafe_allow_html=True)


def render_header(user_df: pd.DataFrame) -> None:
    user = st.session_state.logged_user
    today_calls = len(user_df[user_df["call_datetime"].astype(str).str[:10] == today_str()]) if not user_df.empty else 0
    picked_up = len(user_df[user_df["call_status"] == "Pick Up"]) if not user_df.empty else 0
    pending_queue = len(user_df[user_df["queue_status"] == "Pending Callback"]) if not user_df.empty else 0

    st.markdown("<div class='hero-box'>", unsafe_allow_html=True)
    top_left, top_right = st.columns([0.62, 0.38])
    with top_left:
        st.markdown(
            f"""
            <div style='font-size:34px;font-weight:900;letter-spacing:-0.03em;color:#0f172a;'>Call Activity Tracking System</div>
            <div style='margin-top:8px;font-size:14px;color:#6b7280;'>
                Personal queue and history are filtered by the logged-in salesperson. This matches your future production logic.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_right:
        info1, info2, info3 = st.columns(3)
        with info1:
            metric_box("Today Calls", str(today_calls), user["name"])
        with info2:
            metric_box("Pick Up", str(picked_up), "Answered calls")
        with info3:
            metric_box("Pending Queue", str(pending_queue), "Need callback")
    st.markdown("</div>", unsafe_allow_html=True)


init_state()
load_css()

if not st.session_state.logged_user:
    login_view()
    st.stop()

user = st.session_state.logged_user
all_df = get_df()
user_df = get_user_df()

render_header(user_df)

nav1, nav2, nav3 = st.columns([0.78, 0.11, 0.11])
with nav2:
    if st.button("Reset Demo", use_container_width=True):
        st.session_state.call_logs = seed_logs()
        reset_form()
        st.rerun()
with nav3:
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_user = None
        st.rerun()

call_tab, queue_tab, history_tab, dashboard_tab = st.tabs(
    ["📞 New Call Log", "🗂️ Unpicked Up Queue", "🕘 Call History", "📊 Dashboard"]
)

with call_tab:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    head1, head2 = st.columns([0.75, 0.25])
    with head1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>New Call Log</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:4px;font-size:14px;color:#6b7280;'>This keeps the clean call logging flow you approved.</div>", unsafe_allow_html=True)
    with head2:
        st.markdown(
            f"<div style='margin-top:6px;text-align:right;'><span style='display:inline-block;background:#166534;color:white;padding:8px 14px;border-radius:999px;font-size:13px;font-weight:700;'>{user['name']}</span></div>",
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
            st.text_input("Callback Date", key="form_callback_date")
        st.text_area("Remark", key="form_remark", height=220, placeholder="Write what happened after the call...")
        st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", use_container_width=True, type="primary"):
            phone = clean_phone(st.session_state.form_phone)
            purpose = st.session_state.form_other_purpose.strip() if st.session_state.form_purpose == "Other" else st.session_state.form_purpose
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            else:
                add_log(
                    {
                        "call_id": make_id(),
                        "call_datetime": datetime.now().isoformat(),
                        "staff_id": user["user_id"],
                        "caller_name": user["name"],
                        "phone_number": phone,
                        "customer_name": st.session_state.form_name.strip(),
                        "call_purpose": purpose,
                        "call_status": st.session_state.form_status,
                        "remark": st.session_state.form_remark.strip(),
                        "callback_date": st.session_state.form_callback_date if st.session_state.form_status in CALLBACK_STATUSES else "",
                        "queue_status": "Pending Callback" if st.session_state.form_status in CALLBACK_STATUSES else "Closed",
                    }
                )
                st.success("Saved successfully")
                st.rerun()
    with c2:
        if st.button("Save & New", use_container_width=True):
            phone = clean_phone(st.session_state.form_phone)
            purpose = st.session_state.form_other_purpose.strip() if st.session_state.form_purpose == "Other" else st.session_state.form_purpose
            if not phone or not st.session_state.form_name.strip() or not purpose:
                st.error("Please complete Phone Number, Full Name, and Call Purpose")
            else:
                add_log(
                    {
                        "call_id": make_id(),
                        "call_datetime": datetime.now().isoformat(),
                        "staff_id": user["user_id"],
                        "caller_name": user["name"],
                        "phone_number": phone,
                        "customer_name": st.session_state.form_name.strip(),
                        "call_purpose": purpose,
                        "call_status": st.session_state.form_status,
                        "remark": st.session_state.form_remark.strip(),
                        "callback_date": st.session_state.form_callback_date if st.session_state.form_status in CALLBACK_STATUSES else "",
                        "queue_status": "Pending Callback" if st.session_state.form_status in CALLBACK_STATUSES else "Closed",
                    }
                )
                reset_form()
                st.success("Saved successfully")
                st.rerun()

    st.write("")
    recent = user_df.sort_values("call_datetime", ascending=False).head(8).copy() if not user_df.empty else user_df.copy()
    if not recent.empty:
        recent = recent[["call_datetime", "phone_number", "customer_name", "call_purpose", "call_status", "queue_status"]].copy()
        recent["call_datetime"] = recent["call_datetime"].apply(fmt_datetime)
        st.markdown("<div style='font-size:22px;font-weight:900;color:#0f172a;margin:8px 0 12px 0;'>Recent Calls</div>", unsafe_allow_html=True)
        st.dataframe(recent, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with queue_tab:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    top_left, top_right = st.columns([0.72, 0.28])
    with top_left:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Unpicked Up Queue</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='margin-top:4px;font-size:14px;color:#6b7280;'>This queue is personal. Only {user['name']}'s unpicked-up customers appear after login, so the same salesperson can call them again later.</div>",
            unsafe_allow_html=True,
        )
    with top_right:
        st.selectbox("Queue Filter", ["All Pending", "Overdue", "Due Today", "Upcoming"], key="queue_filter")

    queue_df = user_df[user_df["queue_status"] == "Pending Callback"].copy() if not user_df.empty else user_df.copy()
    if st.session_state.queue_filter == "Overdue":
        queue_df = queue_df[queue_df["callback_date"].astype(str) < today_str()]
    elif st.session_state.queue_filter == "Due Today":
        queue_df = queue_df[queue_df["callback_date"].astype(str) == today_str()]
    elif st.session_state.queue_filter == "Upcoming":
        queue_df = queue_df[queue_df["callback_date"].astype(str) > today_str()]

    st.markdown(
        f"<div style='margin:12px 0 18px 0;display:inline-block;background:#ecfdf5;color:#166534;padding:10px 16px;border-radius:16px;font-size:13px;font-weight:700;border:1px solid #bbf7d0;'>{len(queue_df)} customer(s) in {user['name']}'s queue</div>",
        unsafe_allow_html=True,
    )

    if queue_df.empty:
        st.info("No pending callbacks in this view.")
    else:
        for _, row in queue_df.iterrows():
            with st.expander(f"📞 {row['customer_name']} | {row['phone_number']} | Callback: {row['callback_date'] or '-'}", expanded=False):
                a1, a2, a3, a4 = st.columns(4)
                with a1:
                    st.markdown("**Phone**")
                    st.write(row["phone_number"])
                with a2:
                    st.markdown("**Purpose**")
                    st.write(row["call_purpose"])
                with a3:
                    st.markdown("**Previous Status**")
                    st.markdown(status_chip(row["call_status"]), unsafe_allow_html=True)
                with a4:
                    st.markdown("**Last Call**")
                    st.write(fmt_datetime(row["call_datetime"]))

                if row["remark"]:
                    st.markdown(
                        f"<div style='margin-top:10px;background:#ecfdf5;border:1px solid #bbf7d0;border-radius:18px;padding:14px;color:#334155;font-size:14px;'>{row['remark']}</div>",
                        unsafe_allow_html=True,
                    )

                st.write("")
                form_col1, form_col2 = st.columns([0.5, 0.5])
                callback_status = form_col1.selectbox(
                    "Callback Status",
                    STATUS_OPTIONS,
                    key=f"queue_status_{row['call_id']}",
                )
                next_callback = form_col2.text_input(
                    "Next Callback Date",
                    value=plus_days(1),
                    key=f"queue_date_{row['call_id']}",
                )
                callback_remark = st.text_area(
                    "New Remark",
                    key=f"queue_remark_{row['call_id']}",
                    height=120,
                )
                q1, q2 = st.columns(2)
                with q1:
                    if st.button("Save Result", key=f"save_{row['call_id']}", use_container_width=True, type="primary"):
                        add_log(
                            {
                                "call_id": make_id(),
                                "call_datetime": datetime.now().isoformat(),
                                "staff_id": user["user_id"],
                                "caller_name": user["name"],
                                "phone_number": row["phone_number"],
                                "customer_name": row["customer_name"],
                                "call_purpose": row["call_purpose"],
                                "call_status": callback_status,
                                "remark": callback_remark.strip(),
                                "callback_date": next_callback if callback_status in CALLBACK_STATUSES else "",
                                "queue_status": "Pending Callback" if callback_status in CALLBACK_STATUSES else "Closed",
                            }
                        )
                        update_queue_item(row["call_id"], "Completed")
                        st.success("Callback result saved")
                        st.rerun()
                with q2:
                    if st.button("Close Item", key=f"close_{row['call_id']}", use_container_width=True):
                        update_queue_item(row["call_id"], "Completed")
                        st.success("Queue item closed")
                        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with history_tab:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Call History</div>", unsafe_allow_html=True)
    st.write("")
    h1, h2, h3 = st.columns([1.2, 0.5, 0.5])
    with h1:
        st.text_input("Search Name / Phone", key="history_search")
    with h2:
        st.selectbox("Call Status", ["All"] + STATUS_OPTIONS, key="history_status")
    with h3:
        st.selectbox("Call Purpose", ["All"] + PURPOSE_OPTIONS, key="history_purpose")

    history_df = user_df.copy()
    if st.session_state.history_search.strip():
        q = st.session_state.history_search.strip().lower()
        history_df = history_df[
            history_df["customer_name"].astype(str).str.lower().str.contains(q)
            | history_df["phone_number"].astype(str).str.lower().str.contains(q)
        ]
    if st.session_state.history_status != "All":
        history_df = history_df[history_df["call_status"] == st.session_state.history_status]
    if st.session_state.history_purpose != "All":
        history_df = history_df[history_df["call_purpose"] == st.session_state.history_purpose]

    history_df = history_df.sort_values("call_datetime", ascending=False)
    if history_df.empty:
        st.info("No history found.")
    else:
        view = history_df[["call_datetime", "phone_number", "customer_name", "call_purpose", "call_status", "queue_status", "remark"]].copy()
        view["call_datetime"] = view["call_datetime"].apply(fmt_datetime)
        st.dataframe(view, use_container_width=True, hide_index=True, height=520)
    st.markdown("</div>", unsafe_allow_html=True)

with dashboard_tab:
    st.markdown("<div class='soft-panel'>", unsafe_allow_html=True)
    d1, d2 = st.columns([0.72, 0.28])
    with d1:
        st.markdown("<div style='font-size:28px;font-weight:900;color:#0f172a;'>Dashboard</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:4px;font-size:14px;color:#6b7280;'>Monitor personal performance or switch to overall demo data.</div>", unsafe_allow_html=True)
    with d2:
        st.selectbox("Dashboard Scope", ["My Calls", "All Demo Data"], key="dashboard_scope")

    scope_df = user_df.copy() if st.session_state.dashboard_scope == "My Calls" else all_df.copy()
    if scope_df.empty:
        st.info("No data available.")
    else:
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            metric_box("Total Calls", str(len(scope_df)), "Prototype records")
        with s2:
            metric_box("Pick Up", str(len(scope_df[scope_df["call_status"] == "Pick Up"])), "Answered calls")
        with s3:
            metric_box("Pending Callback", str(len(scope_df[scope_df["queue_status"] == "Pending Callback"])), "Need another try")
        with s4:
            metric_box("Today Calls", str(len(scope_df[scope_df["call_datetime"].astype(str).str[:10] == today_str()])), "Calls today")

        st.write("")
        chart1, chart2 = st.columns(2, gap="large")
        with chart1:
            status_df = scope_df.groupby("call_status", as_index=False).size().rename(columns={"size": "count"})
            st.bar_chart(status_df.set_index("call_status"))
        with chart2:
            purpose_df = scope_df.groupby("call_purpose", as_index=False).size().rename(columns={"size": "count"})
            st.bar_chart(purpose_df.set_index("call_purpose"))

        trend_df = scope_df.copy()
        trend_df["call_day"] = trend_df["call_datetime"].astype(str).str[:10]
        trend_df = trend_df.groupby("call_day", as_index=False).size().rename(columns={"size": "count"})
        st.write("")
        st.line_chart(trend_df.set_index("call_day"))
    st.markdown("</div>", unsafe_allow_html=True)
