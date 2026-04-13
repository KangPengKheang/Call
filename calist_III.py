import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import time
import csv
import os
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from functools import lru_cache
import re

def metric_card(title, value, icon):
    st.markdown(
        f"""
        <div style="
            background: #F0FDF4;
            border-left: 6px solid #15803D;
            padding: 12px 15px;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            font-family: 'Segoe UI';
        ">
            <div style="font-size: 14px; color: #14532D; font-weight: 600;">
                {icon} {title}
            </div>
            <div style="font-size: 22px; font-weight: 700; margin-top:5px; color:#0D442A;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def clean_phone_number(phone):
    """
    Normalize phone number by:
    - Removing spaces, parentheses, and dashes
    - Removing '+855' or '(855)' prefix
    - Ensuring it starts with '0'
    """
    if not phone:
        return ""

    phone = str(phone)
    # Remove non-numeric except '+'
    phone = re.sub(r"[()\s-]", "", phone)

    # Replace +855 or (855) with 0
    phone = re.sub(r"^\+?855", "0", phone)
    phone = re.sub(r"^855", "0", phone)

    # Ensure starts with 0
    if not phone.startswith("0"):
        phone = "0" + phone

    return phone.strip()

@st.cache_data(ttl=300)
def get_followup_data_cached():
    """Load follow-up data without problematic connection tests"""
    try:
        client = setup_gsheets()
        if not client:
            return pd.DataFrame()

        try:
            sheet = client.open_by_key(SHEET_ID)
            followup_sheet = sheet.worksheet("FollowUp")
            data = followup_sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                return df
            else:
                return pd.DataFrame()
                
        except gspread.WorksheetNotFound:
            st.info("📝 'FollowUp' worksheet not found yet - it will be created automatically")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error accessing worksheet: {e}")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Error loading follow-up data: {e}")
        return pd.DataFrame()


def load_customers_from_sheet_cached():
    """Cached version of customer loading"""
    return load_customers_from_sheet()


# Page config
st.set_page_config(page_title="SALE CALL MANAGEMENT PLATFORM", layout="wide", page_icon="📞")
# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 5px;
        text-align: center;
    }
    .call-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        margin-tox: 20px;
        border-left: 5px solid #2E8B57;
    }
    .metric-card {
        background: linear-gradient(135deg, #f0f8ff 0%, #e0f0e0 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .customer-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #2E8B57;
    }
    .call-button {
        background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        margin: 15px;
        width: 100%;
    }
    .call-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .status-completed {
        color: #28a745;
        font-weight: bold;
    }
    .status-pending {
        color: #ffc107;
        font-weight: bold;
    }
    .status-missed {
        color: #dc3545;
        font-weight: bold;
    }
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    .stApp {
    background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
    background-attachment: fixed;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "customers" not in st.session_state:
    st.session_state.customers = []
if "call_log" not in st.session_state:
    st.session_state.call_log = []
if "selected_customer" not in st.session_state:
    st.session_state.selected_customer = None
if "view_customer_history" not in st.session_state:
    st.session_state.view_customer_history = None

# Ensure session dicts exist
if "status_dict" not in st.session_state:
    st.session_state.status_dict = {}
if "product_dict" not in st.session_state:
    st.session_state.product_dict = {}
if "bank_info_dict" not in st.session_state:
    st.session_state.bank_info_dict = {}
if "next_action_dict" not in st.session_state:
    st.session_state.next_action_dict = {}

# File paths
# Get the folder where your main.py is
BASE_DIR = os.path.dirname(__file__)

# Relative path to the logo
LOGO_PATH = os.path.join(BASE_DIR, "Logo-CMCB.png")


# Google Sheets Configuration
SHEET_ID = "1FeAYu8jgE_R7IWjcDPjhXsmXvpn79GbVAMa_WU0mxQs"
WORKSHEET_NAME = "customerdata"


def save_customer_to_sheet(customer_data):
    """Save new customer to Google Sheets"""
    try:
        client = setup_gsheets()
        if not client:
            return False

        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(WORKSHEET_NAME)

        # Prepare row data matching your sheet structure
        row = [
            customer_data["id"],
            customer_data["name"],
            customer_data["business"],
            customer_data["phone"],
            customer_data["status"],
            customer_data["staff_id"],
            customer_data["source"],
            customer_data["created_date"],
        ]

        worksheet.append_row(row)
        return True

    except Exception as e:
        st.error(f"❌ Error saving customer to Google Sheets: {e}")
        return False

def save_followup_to_google_sheets(followup_data):
    """Save follow-up record to Google Sheets 'FollowUp' worksheet - UPDATED for your column structure"""
    try:
        client = setup_gsheets()
        if not client:
            return False

        sheet = client.open_by_key(SHEET_ID)

        # Try to get or create FollowUp worksheet
        try:
            followup_sheet = sheet.worksheet("FollowUp")
        except gspread.WorksheetNotFound:
            # Create new worksheet for follow-ups with YOUR column structure
            followup_sheet = sheet.add_worksheet(title="FollowUp", rows=1000, cols=15)
            headers = [
                "customer_name",
                "customer_id",
                "customer_business",
                "customer_phone",
                "staff_id",
                "source",
                "call_status",
                "product_interest",
                "bank_name",
                "interest",
                "amount_usd",
                "next_action",
                "followup_date",
                "call_notes",
                "status",
                "followup_count",
                "last_updated",
                "appointment_date",
            ]
            followup_sheet.append_row(headers)

        # ✅ Convert date objects to strings
        followup_date = followup_data.get("followup_date", "")
        if followup_date and hasattr(followup_date, "strftime"):
            followup_date = followup_date.strftime("%Y-%m-%d")

        appointment_date = followup_data.get("appointment_date", "")
        if appointment_date and hasattr(appointment_date, "strftime"):
            appointment_date = appointment_date.strftime("%Y-%m-%d")

        # ✅ Set last_updated to today's date
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ✅ Convert amount to string if it's a number
        amount_usd = followup_data.get("amount_usd", "")
        if isinstance(amount_usd, (int, float)):
            amount_usd = str(amount_usd)

        # ✅ Prepare row data matching YOUR exact column structure
        # ✅ Prepare row data matching header structure exactly
        row = [
            followup_data.get("customer_name", ""),
            followup_data.get("customer_id", ""),
            followup_data.get("customer_business", ""),
            followup_data.get("customer_phone", ""),
            followup_data.get("staff_id", ""),
            followup_data.get("source", ""),
            followup_data.get("call_status", ""),  # ✅ Added missing field
            followup_data.get("product_interest", ""),
            followup_data.get("bank_name", ""),
            amount_usd,
            followup_data.get("interest", ""),
            followup_data.get("next_action", ""),
            followup_date,
            followup_data.get("call_notes", ""),
            followup_data.get("status", "Pending"),
            "1",
            last_updated,
            appointment_date,
        ]

        # Save to followup sheet
        followup_sheet.append_row(row)
        st.sidebar.success(
            f"✅ Follow-up saved for {followup_data.get('customer_name')}"
        )

        # DEBUG: Update main sheet status
        try:
            main_sheet = sheet.worksheet(WORKSHEET_NAME)
            customer_id = followup_data.get("customer_id", "")

            st.sidebar.info(
                f"🔍 Looking for customer ID: '{customer_id}' in main sheet"
            )

            if customer_id:
                # Get all data from main sheet
                all_data = main_sheet.get_all_values()
                headers = all_data[0]

                st.sidebar.info(f"📊 Main sheet headers: {headers}")

                # Find column indices with exact names
                try:
                    id_col_index = headers.index("id")
                    status_col_index = headers.index("status")
                    st.sidebar.success(
                        f"✅ Found ID column at index {id_col_index}, Status at {status_col_index}"
                    )
                except ValueError as e:
                    st.sidebar.error(f"❌ Column not found: {e}")
                    st.sidebar.info(f"Available columns: {headers}")
                    return True  # Still return True for follow-up save

                # Find and update the customer row
                found = False
                for row_num, row_data in enumerate(
                    all_data[1:], start=2
                ):  # start=2 because of 1-based indexing and header row
                    if len(row_data) > id_col_index:
                        current_id = str(row_data[id_col_index]).strip()
                        target_id = str(customer_id).strip()

                        st.sidebar.info(
                            f"🔍 Checking row {row_num}: ID '{current_id}' vs target '{target_id}'"
                        )

                        if current_id == target_id:
                            st.sidebar.success(
                                f"🎯 Found matching customer at row {row_num}"
                            )

                            # Update status to "Called"
                            main_sheet.update_cell(
                                row_num, status_col_index + 1, "Called"
                            )  # +1 for 1-based indexing
                            st.sidebar.success(
                                f"✅ Updated status to 'Called' for customer {followup_data.get('customer_name')}"
                            )
                            found = True
                            break

                if not found:
                    st.sidebar.warning(
                        f"⚠️ Customer ID {customer_id} not found in main sheet"
                    )

        except Exception as e:
            st.sidebar.error(f"❌ Error updating main sheet: {str(e)}")
            import traceback

        st.success("✅ Follow-up saved successfully!")
        return True

    except Exception as e:
        st.error(f"❌ Error saving follow-up to Google Sheets: {e}")
        import traceback

        st.error(f"Detailed error: {traceback.format_exc()}")
        return False

def update_customer_in_sheet(customer_id, updates):
    """Update customer data in Google Sheets main worksheet"""
    try:
        client = setup_gsheets()
        if not client:
            return False

        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(WORKSHEET_NAME)

        # Get all data to find the correct row
        all_data = worksheet.get_all_values()
        if len(all_data) <= 1:
            return False

        headers = all_data[0]

        # Find column indices
        try:
            id_col = headers.index("id") + 1
            last_contact_col = headers.index("last_contact") + 1
            call_count_col = headers.index("call_count") + 1
            status_col = headers.index("status") + 1
            potential_col = headers.index("potential") + 1
        except ValueError as e:
            st.error(f"Column not found: {e}")
            return False

        # Find and update the customer row
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > id_col - 1 and str(row[id_col - 1]) == str(customer_id):
                if "last_contact" in updates:
                    worksheet.update_cell(i, last_contact_col, updates["last_contact"])
                if "call_count" in updates:
                    worksheet.update_cell(i, call_count_col, updates["call_count"])
                if "status" in updates:
                    worksheet.update_cell(i, status_col, updates["status"])
                if "potential" in updates:
                    worksheet.update_cell(i, potential_col, updates["potential"])
                return True

        return False
    except Exception as e:
        st.error(f"❌ Error updating customer: {e}")
        return False
        
def setup_gsheets():
    """Initialize Google Sheets connection with proper scopes"""
    try:
        # ✅ Use these scopes instead
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        
        # Check if secrets exist
        if 'gcp_service_account' not in st.secrets:
            st.error("❌ Google Sheets credentials not found in secrets")
            return None
        
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Validate required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds_dict]
        if missing_fields:
            st.error(f"❌ Missing required fields in secrets: {missing_fields}")
            return None

        # Use Credentials from secrets
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # ✅ Remove the connection test that requires extra permissions
        #st.sidebar.success("✅ Google Sheets connection established")
        return client  
    except Exception as e:
        st.error(f"❌ Error setting up Google Sheets: {e}")
        return None

def load_staff_master_df():
    client = setup_gsheets()
    sheet = client.open_by_key(SHEET_ID)
    ws = sheet.worksheet("call_users")

    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df.columns = df.columns.str.strip().str.lower()

    df["staff_id"] = df["id"].astype(str).str.strip()
    df["role"] = df["role"].astype(str).str.strip().str.lower()
    df["branch_name"] = df["appreviation"].astype(str).str.strip()
    df["branch_manager"] = df["team lead"].astype(str).str.strip()

    return df[["staff_id", "role", "branch_name", "branch_manager"]]



@st.cache_data(ttl=300)
def load_customers_from_sheet():
    """Load customers from Google Sheets"""
    try:
        client = setup_gsheets()
        if not client:
            st.error("❌ Failed to connect to Google Sheets")
            return []

        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(WORKSHEET_NAME)

        # Get all records
        records = worksheet.get_all_records()

        if not records:
            st.info("No customer data found in the sheet.")
            return []

        # Convert to list of dictionaries
        customers = []
        for record in records:
            customers.append(
                {
                    "id": record.get("id", ""),
                    "name": record.get("name", ""),
                    "business": record.get("business", ""),
                    "phone": record.get("phone", ""),
                    "email": record.get("email", ""),
                    "potential": record.get("potential", ""),
                    "status": record.get("status", ""),
                    "last_contact": record.get("last_contact", ""),
                    # "call_count": int(record.get("call_count", 0)),  # Convert to int
                    "call_count": int(record.get("call_count", 0)),
                    "rm_code": str(record.get("rm_code", "")).strip(),
                    "sale_name": record.get("rm", ""),
                    "source": record.get("source", ""),
                    "staff_id": record.get("staff_id", ""),
                    "address": record.get("address", ""),
                    "notes": record.get("notes", ""),
                    "created_date": record.get("created_date", ""),
                }
            )

        # st.success(f"✅ Loaded {len(customers)} customers from Google Sheets")
        return customers

    except Exception as e:
        st.error(f"❌ Error loading customers: {e}")
        return []


import hashlib
import secrets

def hash_password(password):
    """Hash a password for storing."""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = pwdhash.hex()
    return f"{salt}${pwdhash}"


import hashlib

def verify_password(stored_password, provided_password):
    """
    Simple password verification (plain-text comparison).
    Only use if passwords are stored directly (not hashed).
    """
    try:
        # Ensure both are strings and strip spaces
        stored_password = str(stored_password).strip()
        provided_password = str(provided_password).strip()

        # Direct equality check
        return stored_password == provided_password

    except Exception as e:
        st.error(f"Password verification error: {e}")
        return False

def get_user_data(username):
    """Fetch user info from Google Sheet"""
    try:
        client = setup_gsheets()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("pw")
        records = worksheet.get_all_records()

        for record in records:
            if str(record["staff_id"]).strip() == str(username).strip():
                # Return useful info for session
                return {
                    "staff_id": record["staff_id"],
                    "status": record["status"],
                    "created": record.get("date_created", ""),
                }
        return None
    except Exception as e:
        st.error(f"Error fetching user data: {e}")
        return None


def user_exists(username):
    """Check if username exists in 'pw' sheet"""
    try:
        client = setup_gsheets()
        if not client:
            st.error("❌ Cannot connect to Google Sheets")
            return False
            
        sheet = client.open_by_key(SHEET_ID)
        
        # Directly use "pw" worksheet
        worksheet = sheet.worksheet("pw")
        records = worksheet.get_all_records()
        
        # Debug: Show what columns exist
        #if records:
            #st.write(f"🔍 Available columns in 'pw' sheet: {list(records[0].keys())}")
        
        for record in records:
            # Check staff_id column (based on your authentication function)
            staff_id = str(record.get("staff_id", "")).strip()
            target_username = str(username).strip()
            
            # Debug each record
            #st.write(f"🔍 Checking: staff_id='{staff_id}' vs username='{target_username}'")
            
            if staff_id == target_username:
                #st.success(f"✅ Username '{username}' found in 'pw' sheet")
                return True
        
        #st.warning(f"❌ Username '{username}' NOT found in 'pw' sheet")
        return False
        
    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ Worksheet 'pw' not found in the Google Sheet")
        return False
    except Exception as e:
        st.error(f"❌ Error checking username: {e}")
        return False

#@st.cache_data(ttl=300)
def authenticate_user(staff_id, password):
    """Authenticate user using plain password"""
    try:
        client = setup_gsheets()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("pw")

        records = worksheet.get_all_records()
        
        # Convert ALL values to strings to avoid type issues
        records = [{k: str(v) if v is not None else "" for k, v in record.items()} for record in records]

        for record in records:
            # Now both are strings for comparison
            if record["staff_id"].strip() == str(staff_id).strip():
                if record["status"].lower() == "active":
                    stored_password = record["password"].strip()
                    provided_password = str(password).strip()
                    
                    if stored_password == provided_password:
                        return True
                    else:
                        st.error(f"❌ Password mismatch. Stored: '{stored_password}' vs Provided: '{provided_password}'")
                        return False
                else:
                    st.error("❌ Account is not active")
                    return False

        st.error("❌ Staff ID not found")
        return False

    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False

def register_user(username, password, confirm_password):
    """Register a new user"""
    try:
        # Validation
        if not all([username, password, confirm_password]):
            st.error("Please fill all required fields")
            return False
        
        if password != confirm_password:
            st.error("Passwords do not match")
            return False
        
        if len(password) < 8:
            st.error("Password must be at least 8 characters")
            return False
        
        # Check if username exists
        if user_exists(username):
            st.error("Username already exists")
            return False
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Save to Google Sheets
        client = setup_gsheets()
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet("pw")
        
        user_data = [
            username,           # username column
            password,           # password column (plain text - consider removing this)
            hashed_password,    # hashed_password column
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at column
            "active"            # status column
        ]
        
        worksheet.append_row(user_data)
        st.success("✅ Registration successful!")
        return True
        
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False

def login_form():
    st.markdown(
        """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .login-card h2 {
            margin-top: 10px;
            color: #2E8B57;
        }
        .stTextInput>div>div>input {
            padding-left: 35px;
        }
        /* Center the login form */
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ---- Bank Logo ----
    st.markdown(
        """
        <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 5px;'>
            <img src='data:image/png;base64,{}' width='120' alt='Bank Logo'>
        </div>
        """.format(
            logo_data
        ),
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <h3 style="color: #038C3E; margin-bottom: 5px; font-size: 18px;">SALE CALL MANAGEMENT SYSTEM</h3>
        <p style="font-size: 13px; color: #666; margin-bottom: 20px; line-height: 1.4;">
            Enter your Staff ID to access the system
        </p>
        """,
        unsafe_allow_html=True,
    )
    # Add debug button to check staff master columns
    if st.sidebar.button("🔍 Debug Staff Master Columns"):
        staff_df = load_staff_master_df()
        st.sidebar.write("📋 Staff Master Columns:", staff_df.columns.tolist())
        st.sidebar.write("📊 Sample Data:")
        st.sidebar.dataframe(staff_df.head(3))
        st.sidebar.write("🔢 Data Types:")
        st.sidebar.write(staff_df.dtypes)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    #st.write("DEBUG staff_df columns:", staff_df.columns.tolist())

    
    with tab1:
        with st.form("login_form", clear_on_submit=False):
            staff_id = st.text_input(
                "👤 Username",
                placeholder="Enter your username",
                help="Your registered username",
            )
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your password",
                help="Your account password",
            )

            # Add debug mode toggle
            # debug_mode = st.checkbox("Enable Debug Mode", value=False)

            login_submitted = st.form_submit_button("Login →", use_container_width=True)

            if login_submitted:
                # if debug_mode:
                #    # Run debug version
                #    auth_result = debug_login(staff_id, password)
                #    if auth_result:
                #        st.session_state.logged_in = True
                #        st.session_state.staff_id = staff_id
                #        st.session_state.username = staff_id
                #        st.session_state.customers = load_customers_from_sheet_cached()
                #        st.rerun()
                # else:
                # Run normal version
                if authenticate_user(staff_id, password):
                    staff_df = load_staff_master_df()

                    staff_info = staff_df[staff_df["staff_id"] == str(staff_id).strip()]
                    if staff_info.empty:
                        st.error("❌ Staff not found in master data")

                    #staff_info = staff_info.iloc[0]

                    st.session_state.user_role = staff_info["role"]
                    st.session_state.branch_name = staff_info["branch_name"]
                    st.session_state.branch_manager = staff_info["branch_manager"]
                    # staff_info = load_staff_master_df(staff_id)
                    st.session_state.logged_in = True
                    st.session_state.staff_id = staff_id
                    st.session_state.username = staff_id
                    st.session_state.customers = load_customers_from_sheet_cached()
                    st.rerun()
                else:
                    st.error("❌ Invalid Staff ID or Password")
    with tab2:
        with st.form("register_form", clear_on_submit=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                new_username = st.text_input(
                    "👤 Staff ID *",
                    placeholder="Input Your Staff ID",
                    help="Must be unique",
                )

            with col2:
                new_password = st.text_input(
                    "🔒 Create Password *",
                    type="password",
                    placeholder="Strong password",
                    help="At least 8 characters",
                )

            with col3:
                confirm_password = st.text_input(
                    "🔒 Confirm Password *",
                    type="password",
                    placeholder="Re-enter password",
                )

            register_submitted = st.form_submit_button(
                "Create Account →", use_container_width=True
            )
            if register_submitted:
                if register_user(new_username, new_password, confirm_password):
                    st.success("✅ Account created successfully! Please login.")
                else:
                    st.error("❌ Registration failed")
    st.markdown("</div></div>", unsafe_allow_html=True)


def update_followup_status(row_key, new_status, new_date, notes, staff_id):
    """Update follow-up status in Google Sheets"""
    try:
        client = setup_gsheets()
        if not client:
            return False

        sheet = client.open_by_key(SHEET_ID)
        followup_sheet = sheet.worksheet("FollowUp")

        all_data = followup_sheet.get_all_values()
        headers = all_data[0]

        customer_id = row_key.split("_")[0]

        for idx, sheet_row in enumerate(all_data[1:], start=2):
            sheet_rm_code = str(sheet_row[headers.index("staff_id")])
            sheet_customer_id = sheet_row[headers.index("customer_id")]

            if sheet_rm_code == staff_id and str(sheet_customer_id) == customer_id:
                # Update status
                followup_sheet.update_cell(
                    idx, headers.index("action_after_followup") + 1, new_status
                )
                followup_sheet.update_cell(
                    idx, headers.index("appointment_date") + 1, str(new_date)
                )
                # Update notes if provided
                if notes:
                    current_notes = (
                        sheet_row[headers.index("notes")]
                        if len(sheet_row) > headers.index("notes")
                        else ""
                    )
                    updated_notes = notes
                    followup_sheet.update_cell(
                        idx, headers.index("notes") + 1, updated_notes.strip()
                    )
                # Update last_updated
                followup_sheet.update_cell(
                    idx,
                    headers.index("last_updated") + 1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return True
        return False
    except Exception as e:
        st.error(f"❌ Error updating follow-up: {e}")
        return False



def update_followup_reschedule(row_key, new_date, new_notes, staff_id):
    """Reschedule a follow-up in Google Sheets."""
    try:
        client = setup_gsheets()
        if not client:
            return False

        sheet = client.open_by_key(SHEET_ID)
        followup_sheet = sheet.worksheet("FollowUp")

        all_data = followup_sheet.get_all_values()
        headers = all_data[0]

        # Extract customer_id from row_key
        customer_id = row_key.split("_")[0]

        for idx, sheet_row in enumerate(all_data[1:], start=2):

            sheet_rm_code = str(sheet_row[headers.index("staff_id")]).strip()
            sheet_customer_id = str(sheet_row[headers.index("customer_id")]).strip()

            # Find correct row
            if sheet_rm_code == str(staff_id).strip() and sheet_customer_id == customer_id:

                # Update next_action back to Follow Up
                followup_sheet.update_cell(
                    idx, headers.index("next_action") + 1, "Follow Up"
                )

                # Update follow-up date
                followup_sheet.update_cell(
                    idx, headers.index("followup_date") + 1, str(new_date)
                )

                # Reset action_after_followup
                followup_sheet.update_cell(
                    idx, headers.index("action_after_followup") + 1, ""
                )

                # Update notes (append or replace)
                if new_notes:
                    existing_notes = (
                        sheet_row[headers.index("notes")]
                        if len(sheet_row) > headers.index("notes")
                        else ""
                    )
                    updated_notes = f"{existing_notes}\n{new_notes}".strip()
                    followup_sheet.update_cell(
                        idx, headers.index("notes") + 1, updated_notes
                    )

                # Update last_updated
                followup_sheet.update_cell(
                    idx,
                    headers.index("last_updated") + 1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    
                )

                return True

        return False

    except Exception as e:
        st.error(f"❌ Error rescheduling follow-up: {e}")
        return False
        

def convert_to_appointment(row_key, appointment_date, appointment_notes, staff_id):
    """Convert follow-up to appointment - FIXED VERSION"""
    try:
    
        customer_name = row_key.split("_")[0] if "_" in row_key else row_key
        client = setup_gsheets()
        if not client:
            st.error("❌ Failed to connect to Google Sheets")
            return False

        sheet = client.open_by_key(SHEET_ID)
        followup_sheet = sheet.worksheet("FollowUp")

        all_data = followup_sheet.get_all_values()
        headers = [h.strip().lower() for h in all_data[0]]  # Normalize headers
        
        
        # Find column indices with flexible naming
        staff_id_idx = find_column_index(headers, ["staff_id", "staffid", "rm_code", "rm", "staff"])
        customer_name_idx = find_column_index(headers, ["customer_name", "customername", "name", "client_name"])
        action_idx = find_column_index(headers, ["action_after_followup", "next_action", "status", "action"])
        appointment_idx = find_column_index(headers, ["appointment_date", "appointment", "appt_date"])
        last_updated_idx = find_column_index(headers, ["last_updated", "timestamp", "updated", "last_updated"])
                
        if staff_id_idx == -1 or customer_name_idx == -1:
            st.error(f"❌ Required columns not found. Check your sheet column names.")
            return False

        found_match = False
        for idx, sheet_row in enumerate(all_data[1:], start=2):
            if len(sheet_row) > max(staff_id_idx, customer_name_idx):
                sheet_rm_code = str(sheet_row[staff_id_idx]).strip().lower()
                sheet_customer_name = str(sheet_row[customer_name_idx]).strip().lower()
                target_staff_id = str(staff_id).strip().lower()
                target_customer_name = str(customer_name).strip().lower()
                
                if sheet_rm_code == target_staff_id and sheet_customer_name == target_customer_name:
                    #st.success(f"✅ MATCH FOUND at row {idx}!")
                    found_match = True
                    
                    # Update the row
                    if action_idx != -1:
                        followup_sheet.update_cell(idx, action_idx + 1, "Appointment")
                    if appointment_idx != -1:
                        followup_sheet.update_cell(idx, appointment_idx + 1, str(appointment_date))
                    if last_updated_idx != -1:
                        followup_sheet.update_cell(idx, last_updated_idx + 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    
                    st.success("✅ Successfully converted to appointment!")
                    return True
        
        if not found_match:
            st.error(f"❌ No match found for customer '{customer_name}' with staff '{staff_id}'")
            
        return False
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

def find_column_index(headers, possible_names):
    """Find column index from list of possible names"""
    for name in possible_names:
        if name in headers:
            return headers.index(name)
    return -1


def debug_followup_data():
    """Debug function to check followup data structure"""
    st.markdown("---")
    st.markdown("### 🐛 DEBUG: FollowUp Data Structure")
    
    df_followup = get_followup_data_cached()
    if not df_followup.empty:
        st.write(f"**Total rows:** {len(df_followup)}")
        st.write(f"**Columns:** {list(df_followup.columns)}")
        
        # Show sample data
        st.write("**Sample data (first 5 rows):**")
        st.dataframe(df_followup.head())
        
        # Check for current RM's data
        current_rm = st.session_state.get("staff_id", "")
        if current_rm:
            formatted_rm = str(current_rm).strip()
            rm_data = df_followup[df_followup["staff_id"].apply(lambda x: str(x).strip()) == formatted_rm]
            st.write(f"**Your data (RM: {formatted_rm}):** {len(rm_data)} rows")
            st.dataframe(rm_data[['customer_name', 'staff_id', 'next_action']].head())
    else:
        st.error("No followup data available")

# Add this somewhere in your tab2_inner for debugging
#if st.checkbox("🐛 Show Debug Info"):
#    debug_followup_data()

def add_followup_note(row_key, new_note, staff_id):
    """Add note to follow-up"""
    return update_followup_status(row_key, "", "", new_note, staff_id)


def display_metric_card(title, value, subtitle):
    st.markdown(
        f"""
        <div style='
            background: linear-gradient(135deg, #e6f4ea 0%, #f4fff8 100%);
            padding: 20px;
            border-radius: 16px;
            border: 1.5px solid rgba(3,140,62,0.3);
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            text-align: center;
            margin: 4px;
            transition: all 0.2s ease-in-out;
            height: 140px;  /* Fixed height */
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        ' 
        onmouseover="this.style.transform='scale(1.03)'; this.style.boxShadow='0 6px 18px rgba(0,0,0,0.12)';" 
        onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 3px 10px rgba(0,0,0,0.08)';">
            <div style='font-size: 22px; color:#047857; font-weight: 600;'>{title}</div>
            <div style='font-size: 36px; font-weight: 800; color:#065f46; margin: 5px 0;'>{value}</div>
            <div style='font-size: 14px; color:#065f46; opacity: 0.8;'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

#def add_followup_note(row_key, new_note, staff_id):
#    """Add note to follow-up"""
#    return update_followup_status(row_key, "Follow Up", new_note, staff_id)

    # Professional Footer
#    st.markdown("---")
#    st.markdown(
#        """
#    <div style="text-align: center; color: #6c757d; margin-top: 40px; padding: 20px;">
#        <p style="margin: 0; font-size: 14px;">
#            <strong>Chip Mong Commercial Bank</strong> • Sales Excellence Platform v2.0<br>
#            Secure • Efficient • Professional
#        </p>
#        <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.7;">
#            Last updated: {} | RM Code: {}
#        </p>
#    </div>
#    """.format(
#            datetime.now().strftime("%d %b %Y %H:%M"), st.session_state.rm_code
#        ),
#        unsafe_allow_html=True,
#    )



# Main app
import base64

with open(
    "Logo-CMCB.png", "rb"
) as f:  # put the PNG file in the same folder as this script
    logo_data = base64.b64encode(f.read()).decode()


# Define callback functions before the tabs
# ✅ Put these at the TOP of your script
def set_followup_state(key):
    st.session_state[key] = True


def clear_followup_state(key):
    st.session_state[key] = False


# --- Initialize session state variables ---
# Initialize session state at the TOP of your script
if "show_tabs" not in st.session_state:
    st.session_state.show_tabs = True
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Customer List"

def main_app():
    # Header with professional design
    # ---- Display the header with embedded logo ----
    st.markdown(
        f"""
    <div style="background: linear-gradient(135deg, #ececec 0%, #d4d4d4 100%);
                padding: 25px; border-radius: 15px; color: white; margin-bottom: 25px;
                border-left: 6px solid #038C3E; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center;">
                <img src="data:image/png;base64,{logo_data}"
                    style="height: 75px; width: auto; margin-right: 25px;"
                    alt="CMCB Logo" />
                <div>
                    <h1 style="margin: 0; font-size: 28px; font-weight: 800; letter-spacing: 0.5px; color:#222 ; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                        SALE CALL MANAGEMENT PLATFORM
                    </h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.95; font-size: 15px; font-weight: 400; color: #333;">
                        Chip Mong Commercial Bank • Customer Engagement System
                    </p>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="background: linear-gradient(135deg,  rgba(3,140,62,0.25) 0%,  rgba(3,140,62,0.25) 100%); 
                            padding: 12px 25px; border-radius: 20px; border: 2px solid  rgba(3,140,62,0.25); 
                            backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                    <div style="font-size: 13px; opacity: 0.9; font-weight: 600; letter-spacing: 0.5px; color:#222 ">RELATIONSHIP MANAGER</div>
                    <div style="font-size: 20px; font-weight: 700; margin-top: 5px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); color: #222">
                        Staff ID {st.session_state.staff_id}
                    </div>
                </div>
                <div style="margin-top: 12px; font-size: 14px; opacity: 0.9; font-weight: 500; 
                            background: rgba(3,140,62,0.15); padding: 8px 15px; border-radius: 12px; 
                            display: inline-block; color: #014d25; border: 1px solid rgba(3,140,62,0.3); 
                            backdrop-filter: blur(6px);">
                    📅 {datetime.now().strftime('%A, %d %B %Y | %H:%M')}
                </div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    @st.cache_data(ttl=120)
    def optimize_customer_data(customers):
        """Pre-process customer data for faster filtering"""
        optimized_customers = []

        # DEBUG: Show original customer data
        #st.write("🔍 DEBUG - Original customers sample:")
        #if customers:
        #    for i, customer in enumerate(customers[:3]):  # Show first 3 customers
        #        st.write(f"  Customer {i}: {customer}")
        #else:
        #    st.write("  ❌ No customers loaded")

        for customer in customers:
            # Pre-process RM code and status once
            optimized_customer = customer.copy()
            
            # DEBUG: Show what staff_id we're working with
            original_staff_id = customer.get("staff_id", "")
            #st.write(f"🔍 DEBUG - Processing customer staff_id: '{original_staff_id}' (type: {type(original_staff_id)})")
            
            optimized_customer["_staff_id_normalized"] = (
                str(customer.get("staff_id", "")).strip()  # REMOVED .zfill(3) - this was the problem!
            )
            optimized_customer["_status"] = customer.get("status", "")
            optimized_customers.append(optimized_customer)
        
        # DEBUG: Show optimized data
        #st.write("🔍 DEBUG - Optimized customers sample:")
        #for i, customer in enumerate(optimized_customers[:3]):
        #    st.write(f"  Optimized {i}: staff_id='{customer.get('staff_id')}', _staff_id_normalized='{customer.get('_staff_id_normalized')}'")
        return optimized_customers

    def get_user_customers_ultra_fast(optimized_customers, staff_id):
        """Ultra-fast filtering with pre-processed data"""
        target_staff = str(staff_id).strip()
        
        # DEBUG: Show what we're looking for
        #st.write(f"🔍 DEBUG - Searching for staff_id: '{target_staff}'")
        #st.write(f"🔍 DEBUG - Total optimized customers: {len(optimized_customers)}")
        
        result = [
            customer
            for customer in optimized_customers
            if customer["_status"] != "Called"
            and customer["_staff_id_normalized"] == target_staff
        ]
        
        # DEBUG: Show matching results
        #st.write(f"🔍 DEBUG - Found {len(result)} matching customers")
        #for i, customer in enumerate(result[:3]):
        #    st.write(f"  Match {i}: {customer.get('name')} - staff_id: '{customer.get('staff_id')}'")
        
        return result

    def get_called_customers_ultra_fast(optimized_customers, staff_id):
        """Get customers that have been called"""
        target_staff = str(staff_id).strip()
        
        result = [
            customer
            for customer in optimized_customers
            if customer.get("_status") == "Called"
            and customer.get("_staff_id_normalized") == target_staff
        ]
        
        # DEBUG: Show called customers
        #st.write(f"🔍 DEBUG - Found {len(result)} called customers for staff {staff_id}")
        
        return result

    def get_uncalled_customers(optimized_customers, staff_id):
        """Get customers with status != 'Called' for specific RM"""
        #target_rm = str(rm_code).strip().zfill(3)
        target_staff = str(staff_id).strip()

        return [
            customer
            for customer in optimized_customers
            if customer["status"] != "Called"
            and customer["_staff_id_normalized"] == target_staff
        ]
    # Add these helper functions if missing
    
    def get_called_customers_ultra_fast(optimized_customers, staff_id):
        """Get customers that have been called"""
        if not optimized_customers:
            return []
        #target_rm = str(rm_code).strip().zfill(3)
        target_staff = str(staff_id).strip()
        return [
            customer
            for customer in optimized_customers
            if customer.get("_status") == "Called"
            and customer.get("_staff_id_normalized") == target_staff
        ]

    # In your main code, add debug section:
    current_staff = str(st.session_state.staff_id).strip()
    

    # Usage - call this once when loading data
    #if "optimized_customers" not in st.session_state:
    #    st.session_state.optimized_customers = optimize_customer_data(
    #        st.session_state.customers
    #    )
    # ALWAYS REBUILD - fastest & safest
    st.session_state.optimized_customers = optimize_customer_data(
        st.session_state.customers
    )

    # Get uncalled customers for display
    #user_customers = get_user_customers_ultra_fast(
    #    st.session_state.optimized_customers, current_staff
    #)
    user_customers = get_user_customers_ultra_fast(
        st.session_state.optimized_customers, current_staff
    )

    # Get called customers for metrics
    called_customers = get_called_customers_ultra_fast(
        st.session_state.optimized_customers, current_staff)

    # Main tabs - Removed Tab 2 as requested
    tab1, tab2 = st.tabs(["🎯 Call Management", "📊 Performance Analysis"])
    with tab1:
        st.markdown("### 📊 CALL OVERVIEW")

        col1, col2, col3, col4, col5 = st.columns(5)
        # Load data once at the start
        df_followup = get_followup_data_cached()
        if (
            hasattr(st.session_state, "optimized_customers")
            and st.session_state.optimized_customers
        ):
            user_customers = get_user_customers_ultra_fast(
                st.session_state.optimized_customers, current_staff
            )
            called_customers = get_called_customers_ultra_fast(
                st.session_state.optimized_customers, current_staff
            )
        else:
            user_customers = []
            called_customers = []
            # st.sidebar.error("❌ Cannot create user_customers - no optimized data")
        # Precompute all metrics
        df_followup = get_followup_data_cached()
        df_followup = pd.DataFrame(df_followup)
        
        # Normalize staff_id in df_followup
        if "staff_id" in df_followup.columns:
            df_followup["staff_id"] = df_followup["staff_id"].astype(str).str.strip()
        
        # Filter followup data for current staff
        df_rm = df_followup[df_followup["staff_id"] == current_staff]
        df_rm["next_action"] = df_rm["next_action"].astype(str).str.lower().str.strip()
        df_rm["action_after_followup"] = df_rm["action_after_followup"].astype(str).str.lower().str.strip()
        total_customers = len(user_customers) + len(called_customers)
        contacted = len(df_rm)
        pick_up = len(df_rm[df_rm["call_status"].str.lower() == "pick up"])
        #contact_rate = (contacted / total_customers * 100) if total_customers else 0
        # Compute follow-ups and appointments once
        follow_up_count = 0
        appointment_count = 0
        if not df_followup.empty and "next_action" in df_followup.columns:
            formatted_rm = current_staff.zfill(3)
            # --- Follow Up (pending follow-ups) ---
            follow_up_count = len(
                df_rm[
                    (df_rm["next_action"] == "follow up") &
                    (df_rm["action_after_followup"] == "")
                ]
            )
            appointment_count = len(
                df_rm[
                    (df_rm["action_after_followup"] == "appointment") |
                    (df_rm["next_action"] == "appointment")
                ]
            )

        with col1:
            display_metric_card("📋 TOTAL ECO-LIST", total_customers, "YOUR CUSTOMER LIST")

        with col2:
            display_metric_card("📞 TOTAL CONTACTED", contacted, f"")

        with col3:
            display_metric_card("📞 TOTAL PICK UP", pick_up, f"")

        with col4:
            display_metric_card("🔄 TOTAL FOLLOW UP", follow_up_count, "")

        with col5:
            display_metric_card("📅 APPOINTMENTS", appointment_count, "Scheduled")

        # Create tabs - ALWAYS VISIBLE
        tab1_inner, tab2_inner, tab3_inner, tab4_inner, tab5_inner = st.tabs(
            [
                "📋 Customer List",
                "🔄 Follow Up",
                "📅 Appointment",
                "📜 History",
                "👥 Add New Customer",
            ]
        )
        
        # Track active tab in session state
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "📋 Customer List"
        
        # Function to set active tab
        def set_active_tab(tab_name):
            st.session_state.active_tab = tab_name
        

        #tab1_inner, tab2_inner, tab3_inner, tab4_inner, tab5_inner = tabs
        with tab1_inner:
            st.session_state.active_tab = "📋 Customer"
            st.markdown("### 👥 Customer List")

            # Initialize ALL session state variables
            if "active_row" not in st.session_state:
                st.session_state.active_row = None
            if "status_dict" not in st.session_state:
                st.session_state.status_dict = {}
            if "product_dict" not in st.session_state:
                st.session_state.product_dict = {}
            if "bank_info_dict" not in st.session_state:
                st.session_state.bank_info_dict = {}
            if "next_action_dict" not in st.session_state:
                st.session_state.next_action_dict = {}
            if "call_notes_dict" not in st.session_state:
                st.session_state.call_notes_dict = {}

            df = pd.DataFrame(user_customers)
            status_options = ["Pick Up", "Not Pick Up", "Cannot Contact", "Rejected"]
            #
            if not df.empty:
                # Add CSS for sticky header
                st.markdown(
                    """
                <style>
                    .sticky-header-container {
                        position: sticky;
                        top: 0;
                        z-index: 100;
                        background: white;
                        padding-bottom: 5px;
                    }
                    .header-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr 1fr;
                        background: #2E8B57;
                        border-radius: 4px;
                        z-index: 101;
                        gap: 0;
                        padding: 8px 0;
                    }
                    .header-item {
                        color: white;
                        font-weight: bold;
                        text-align: center;
                    }
                    .scrollable-table {
                        max-height: 400px;
                        overflow-y: auto;
                        border: 1px solid #ddd;
                        border-radius: 0 0 8px 8px;
                    }
                    .grid-body {
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr;
                        gap: 0;
                    }
                    .grid-cell {
                        padding: 10px 10px;
                        border: 1px solid #1e6b4e;
                        border-top: none;
                        border-left: none;
                        text-align: center;
                        font-size: 12px;
                        min-height: 35px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                        background: white;
                    }
                    /* First cell in each row */
                    .grid-body .grid-cell:nth-child(3n+1) {
                        border-left: 1px solid #1e6b4e;
                    }
                    /* Last row - complete bottom border */
                    .grid-body:last-child .grid-cell {
                        border-bottom: 1px solid #1e6b4e;
                    }
                </style>
                """,
                    unsafe_allow_html=True,
                )

                # Sticky header
                st.markdown(
                    """
                <div class="sticky-header-container">
                    <div class="header-grid">
                        <div class="header-item">Name</div>
                        <div class="header-item">Business</div>
                        <div class="header-item">Source</div>
                        <div class="header-item">Action</div>
                    </div>
                </div>
                <div class="scrollable-table">
                """,
                    unsafe_allow_html=True,
                )

                # Display rows
                for i, row in df.iterrows():
                    customer_id = row["id"]
                    # Create columns for this row
                    cols = st.columns([1, 1, 1, 1])
                    # Customer information - centered
                    with cols[0]:
                        st.markdown(
                            f"<div style='text-align: center; padding: 8px 0;'>{row['name']}</div>",
                            unsafe_allow_html=True,
                        )

                    with cols[1]:
                        st.markdown(
                            f"<div style='text-align: center; padding: 8px 0;'>{row['business']}</div>",
                            unsafe_allow_html=True,
                        )

                    with cols[2]:
                        st.markdown(
                            f"<div style='text-align: center; padding: 8px 0;'>{row.get('source', 'N/A')}</div>",
                            unsafe_allow_html=True,
                        )

                    with cols[3]:
                        if st.button(
                            "📞 Start",
                            key=f"call_{customer_id}",
                            use_container_width=True,
                        ):
                            if st.session_state.active_row == customer_id:
                                st.session_state.active_row = None
                            else:
                                st.session_state.active_row = customer_id

                            # Initialize this customer's data if not exists
                            if customer_id not in st.session_state.status_dict:
                                st.session_state.status_dict[customer_id] = None
                            if customer_id not in st.session_state.product_dict:
                                st.session_state.product_dict[customer_id] = None
                            if customer_id not in st.session_state.bank_info_dict:
                                st.session_state.bank_info_dict[customer_id] = {
                                    "provided": False,
                                    "bank_name": "",
                                    "amount": 0,
                                }
                            if customer_id not in st.session_state.next_action_dict:
                                st.session_state.next_action_dict[customer_id] = {
                                    "action": None,
                                    "date": None,
                                }
                            if customer_id not in st.session_state.call_notes_dict:
                                st.session_state.call_notes_dict[customer_id] = ""
                            st.rerun()
                    # Expanded call form when active
                    if st.session_state.active_row == customer_id:
                        with st.expander(
                            f"📞 Calling: {row['name']} - {row['business']} - {row['phone']}",
                            expanded=True,
                        ):
                            st.markdown("---")

                            # Step 1: Call Outcome with Notes
                            st.markdown("#### 1. 📞 Call Outcome & Notes")

                            # Call status and notes in two columns
                            col_status, col_notes = st.columns([1, 2])

                            with col_status:
                                st.markdown("**Call Status:**")
                                current_status = st.session_state.status_dict.get(
                                    customer_id
                                )
                                selected_status = st.radio(
                                    "Select call status:",
                                    status_options,
                                    index=(
                                        status_options.index(current_status)
                                        if current_status in status_options
                                        else 0
                                    ),
                                    key=f"status_radio_{customer_id}",
                                )
                                # Update session state when selection changes
                                if selected_status != current_status:
                                    st.session_state.status_dict[customer_id] = (
                                        selected_status
                                    )
                                    st.rerun()
                                # Show current status
                                if selected_status:
                                    st.info(f"**Current Status:** {selected_status}")
                            with col_notes:
                                st.markdown("**Call Notes:**")
                                notes_pick_up = st.text_area(
                                    "Enter detailed call notes...",
                                    value=st.session_state.call_notes_dict[customer_id],
                                    key=f"call_notes_{customer_id}",
                                    height=150,
                                    placeholder="Describe the call outcome, customer response, key discussions, and any important details...",
                                    help="Be specific about what was discussed and agreed upon",
                                )
                                st.session_state.call_notes_dict[customer_id] = (
                                    notes_pick_up
                                )
                            st.markdown("---")
                            # Step 2: Product Interest (only for Pick Up)
                            current_status = st.session_state.status_dict.get(
                                customer_id
                            )
                            if "interest_dict" not in st.session_state:
                                st.session_state.interest_dict = {}
                            if current_status == "Pick Up":
                                st.markdown("#### 2. 💼 Product Interest")
                                products = ["No", "Loan", "TD", "KHQR", "VISA", "Other"]
                                product_cols = st.columns(3)
                                for idx, product in enumerate(products):
                                    with product_cols[idx % 3]:
                                        if st.button(
                                            product,
                                            key=f"product_btn_{customer_id}_{product}",
                                            use_container_width=True,
                                            type=(
                                                "primary"
                                                if st.session_state.product_dict.get(
                                                    customer_id
                                                )
                                                == product
                                                else "secondary"
                                            ),
                                        ):
                                            st.session_state.product_dict[
                                                customer_id
                                            ] = product
                                            st.rerun()
                                # Show current selection
                                current_product = st.session_state.product_dict.get(
                                    customer_id
                                )
                                if current_product:
                                    st.success(
                                        f"**Selected Product:** {current_product}"
                                    )
                                # Step 3: Bank Information
                                if current_product and current_product != "No":
                                    st.markdown("#### 3. 🏦 Bank Information")
                                    bank_provided = st.radio(
                                        "Did customer provide bank information?",
                                        ["Yes", "No"],
                                        key=f"bank_radio_{customer_id}",
                                        horizontal=True,
                                    )
                                    st.session_state.bank_info_dict[customer_id][
                                        "provided"
                                    ] = (bank_provided == "Yes")
                                    # Bank details form
                                    if st.session_state.bank_info_dict[customer_id].get(
                                        "provided"
                                    ):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            bank_name = st.text_input(
                                                "Bank Name",
                                                value=st.session_state.bank_info_dict[
                                                    customer_id
                                                ].get("bank_name", ""),
                                                key=f"bank_name_{customer_id}",
                                                placeholder="e.g., ABA Bank, ACLEDA Bank",
                                            )
                                        with col2:
                                            amount = st.number_input(
                                                "Amount (USD)",
                                                min_value=0.0,
                                                step=100.0,
                                                value=float(
                                                    st.session_state.bank_info_dict[
                                                        customer_id
                                                    ].get("amount", 0)
                                                ),
                                                key=f"bank_amount_{customer_id}",
                                                help="Current bank balance or loan amount",
                                            )
                                        st.session_state.bank_info_dict[
                                            customer_id
                                        ].update(
                                            {"bank_name": bank_name, "amount": amount}
                                        )
                                        # --- Interest Rate (NEW) ---
                                        st.markdown("#### 💹 Interest Rate (%)")
                                        
                                        # Initialize dictionary if not exists
                                        #if "interest_dict" not in st.session_state:
                                        #    st.session_state.interest_dict = {}
                                        
                                        # Restore previously typed interest for this customer
                                        current_interest = st.session_state.interest_dict.get(customer_id, "")
                                        
                                        interest_rate = st.text_input(
                                            "Enter interest rate (%)",
                                            value=current_interest,
                                            key=f"interest_rate_{customer_id}",
                                            placeholder="e.g., 10.5",
                                        )
                                        
                                        # Save in session state
                                        st.session_state.interest_dict[customer_id] = interest_rate
                                        

                                # Step 4: Next Action
                                if current_product:
                                    st.markdown("#### 4. 📅 Next Action")

                                    actions = [
                                        "Follow Up",
                                        "Appointment",
                                        "No Action Needed",
                                        "Drop",
                                    ]
                                    next_action = st.radio(
                                        "Select next action:",
                                        actions,
                                        index=(
                                            actions.index(
                                                st.session_state.next_action_dict.get(
                                                    customer_id, {}
                                                ).get("action", "Follow Up")
                                            )
                                            if st.session_state.next_action_dict.get(
                                                customer_id, {}
                                            ).get("action")
                                            in actions
                                            else 0
                                        ),
                                        key=f"next_action_{customer_id}",
                                        horizontal=True,
                                    )
                                    st.session_state.next_action_dict[customer_id] = {
                                        "action": next_action
                                    }

                                    # Date selection for follow-up/appointment
                                    if next_action in ["Follow Up", "Appointment"]:
                                        date = st.date_input(
                                            f"Select {next_action} date:",
                                            value=st.session_state.next_action_dict[
                                                customer_id
                                            ].get("date"),
                                            key=f"date_{customer_id}",
                                        )
                                        st.session_state.next_action_dict[customer_id][
                                            "date"
                                        ] = date
                            elif current_status and current_status != "Pick Up":
                                st.markdown("#### 2. 📅 Next Action")

                                actions = [
                                    "Follow Up",
                                    "No Action Needed",
                                    "Drop",
                                ]
                                next_action = st.radio(
                                    "Select next action:",
                                    actions,
                                    index=(
                                        actions.index(
                                            st.session_state.next_action_dict.get(
                                                customer_id, {}
                                            ).get("action", "Follow Up")
                                        )
                                        if st.session_state.next_action_dict.get(
                                            customer_id, {}
                                        ).get("action")
                                        in actions
                                        else 0
                                    ),
                                    key=f"next_action_{customer_id}",
                                    horizontal=True,
                                )
                                st.session_state.next_action_dict[customer_id] = {
                                    "action": next_action
                                }

                                # Date selection for follow-up
                                if next_action == "Follow Up":
                                    date = st.date_input(
                                        "Select follow-up date:",
                                        value=st.session_state.next_action_dict[
                                            customer_id
                                        ].get("date"),
                                        key=f"date_{customer_id}",
                                    )
                                    st.session_state.next_action_dict[customer_id][
                                        "date"
                                    ] = date

                            # Save and Close buttons
                            st.markdown("---")
                            col_save, col_close = st.columns(2)

                            with col_save:
                                if st.button(
                                    "💾 Save This Call",
                                    key=f"save_single_{customer_id}",
                                    use_container_width=True,
                                    type="primary",
                                ):
                                    st.session_state.status_dict[customer_id] = (
                                        selected_status
                                    )
                                    # Validate required fields
                                    if not st.session_state.status_dict.get(
                                        customer_id
                                    ):
                                        st.error("❌ Please select a call status")
                                    else:
                                        with st.spinner("Saving call data..."):
                                            # Prepare followup data for this single customer
                                            bank_info = (
                                                st.session_state.bank_info_dict.get(
                                                    customer_id, {}
                                                )
                                            )
                                            next_action_data = (
                                                st.session_state.next_action_dict.get(
                                                    customer_id, {}
                                                )
                                            )
                                            current_call_status = (
                                                st.session_state.status_dict.get(
                                                    customer_id, ""
                                                )
                                            )
                                            #st.write(
                                            #    f"🔍 DEBUG: Saving call_status = '{current_call_status}'"
                                            #)
                                            followup_data = {
                                                "customer_name": str(row["name"]),
                                                
                                                "customer_id": str(row["id"]),
                                                
                                                "customer_business": str(
                                                    row["business"]
                                                ),
                                                
                                                "customer_phone": str(
                                                    row.get("phone", "")
                                                ),
                                        
                                                "staff_id": str(
                                                    st.session_state.staff_id
                                                ),

                                                "source": str(
                                                    row.get("source", "")
                                                ),
                                                
                                                "call_status": str(current_call_status),
                                                
                                                "call_notes": str(
                                                    st.session_state.call_notes_dict.get(
                                                        customer_id, ""
                                                    )
                                                ),
                                                
                                                "product_interest": str(
                                                    st.session_state.product_dict.get(
                                                        customer_id, ""
                                                    )
                                                ),
                                                
                                                "bank_name": str(
                                                    bank_info.get("bank_name", "")
                                                ),
                                                
                                                "amount_usd": str(
                                                    bank_info.get("amount", "")
                                                ),
                                                
                                                "next_action": str(
                                                    next_action_data.get("action", "")
                                                ),
                                                
                                                "interest": st.session_state.interest_dict.get(customer_id, ""),
                                                
                                                "followup_date": (
                                                    next_action_data.get(
                                                        "date", ""
                                                    ).strftime("%Y-%m-%d")
                                                    if next_action_data.get("date")
                                                    and next_action_data.get("action")
                                                    in ["Follow Up", "Appointment"]
                                                    else ""
                                                ),
                                                
                                                "appointment_date": (
                                                    next_action_data.get(
                                                        "date", ""
                                                    ).strftime("%Y-%m-%d")
                                                    if next_action_data.get("date")
                                                    and next_action_data.get("action")
                                                    == "Appointment"
                                                    else ""
                                                ),
                                            }

                                            success = save_followup_to_google_sheets(
                                                followup_data
                                            )

                                            if success:
                                                st.success(
                                                    f"✅ Call saved for {row['name']}!"
                                                )
                                                # 🚀 IMMEDIATE UPDATE: Remove from current display without reloading
                                                if (
                                                    "optimized_customers"
                                                    in st.session_state
                                                ):
                                                    # Mark as called in local data
                                                    for (
                                                        customer
                                                    ) in (
                                                        st.session_state.optimized_customers
                                                    ):
                                                        if str(
                                                            customer.get("id")
                                                        ) == str(row["id"]):
                                                            customer["_status"] = (
                                                                "Called"
                                                            )
                                                            customer["status"] = (
                                                                "Called"
                                                            )
                                                            customer["result"] = ()
                                                            break
                                                # Close form and refresh
                                                st.session_state.active_row = None
                                                st.rerun()
                                            else:
                                                st.error("❌ Failed to save call data")

                            with col_close:
                                if st.button(
                                    "❌ Close",
                                    key=f"close_{customer_id}",
                                    use_container_width=True,
                                ):
                                    st.session_state.active_row = None
                                    st.rerun()
    
        
        with tab2_inner:
            # Set active tab when entering
            if st.session_state.active_tab != "🔄 Follow Up":
                set_active_tab("🔄 Follow Up")
            
            st.markdown("### 🔄 Follow Up")
            
            # Create a container to hold all tab2 content
            tab2_container = st.container()
            
            with tab2_container:
                if st.button("🔃 Refresh Follow-Up List", key="refresh_followup_tab2"):
                    st.cache_data.clear()
                    st.rerun()
                
                df_followup = get_followup_data_cached()
                
                if df_followup.empty:
                    st.info("📭 No follow-up data available")
                
                current_rm = st.session_state.get("staff_id", "")
                if not current_rm:
                    st.warning("⚠️ Staff ID not detected")
                
                formatted_rm = str(current_rm).strip()
                
                # Normalize fields safely
                if not df_followup.empty:
                    # Safely handle column normalization
                    for col in ["next_action", "action_after_followup", "staff_id"]:
                        if col in df_followup.columns:
                            df_followup[col] = df_followup[col].astype(str).str.strip()
                        else:
                            # Add missing columns with default values
                            df_followup[col] = ""
                    
                    # Handle interest column
                    if "interest" in df_followup.columns:
                        df_followup["interest_rate"] = df_followup["interest"].astype(str)
                    else:
                        df_followup["interest_rate"] = ""
                    
                    # Ensure date columns are datetime
                    if "followup_date" in df_followup.columns:
                        df_followup["followup_date"] = pd.to_datetime(df_followup["followup_date"], errors="coerce")
                    
                    if "last_updated" in df_followup.columns:
                        df_followup["last_updated"] = pd.to_datetime(df_followup["last_updated"], errors="coerce")
                    
                    # Follow-up condition
                    follow_up_customers = df_followup[
                        (df_followup["next_action"].str.lower() == "follow up") &
                        (
                            (df_followup["action_after_followup"] == "") |
                            (df_followup["action_after_followup"].str.lower() == "follow up")
                        ) &
                        (df_followup["staff_id"] == formatted_rm)
                    ].copy()
                    
                    # Sort by date
                    if "last_updated" in follow_up_customers.columns:
                        follow_up_customers = follow_up_customers.sort_values(by="last_updated", ascending=False)
                    elif "followup_date" in follow_up_customers.columns:
                        follow_up_customers = follow_up_customers.sort_values(by="followup_date", ascending=False)
                    
                    if follow_up_customers.empty:
                        st.success("🎉 No pending follow-ups. Great job!")
                    else:
                        st.info(f"📋 You have **{len(follow_up_customers)} follow-ups**")
                        
                        # Ensure session states exist
                        if "followup_states" not in st.session_state:
                            st.session_state.followup_states = {}
                        
                        # Create a unique session state key for tracking expander states
                        if "expanded_followup" not in st.session_state:
                            st.session_state.expanded_followup = {}
                        
                        for idx, row in follow_up_customers.iterrows():
                            row_key = f"{row.get('customer_id', 'unknown')}_{idx}"
                            
                            # Initialize state container for each row
                            if row_key not in st.session_state.followup_states:
                                st.session_state.followup_states[row_key] = {
                                    "show_reschedule": False,
                                    "show_appointment": False,
                                    "show_note": False,
                                }
                            
                            # Initialize expander state
                            if row_key not in st.session_state.expanded_followup:
                                st.session_state.expanded_followup[row_key] = False
                            
                            # Safely get customer data with defaults
                            customer_name = str(row.get("customer_name", "Unknown Customer")).strip()
                            if not customer_name or customer_name == "nan":
                                customer_name = "Unknown Customer"
                            
                            # Safely format followup date
                            followup_date_val = row.get("followup_date", "")
                            if pd.isna(followup_date_val):
                                followup_date = "No Date Set"
                            else:
                                try:
                                    followup_date = followup_date_val.strftime("%Y-%m-%d")
                                except:
                                    followup_date = str(followup_date_val)
                            
                            # Safely get interest rate
                            interest_rate = str(row.get("interest_rate", "N/A")).strip()
                            if interest_rate == "nan" or interest_rate == "":
                                interest_rate = "N/A"
                            
                            # Determine if expander should be expanded
                            should_expand = (
                                st.session_state.followup_states[row_key]["show_reschedule"] or
                                st.session_state.followup_states[row_key]["show_appointment"] or
                                st.session_state.followup_states[row_key]["show_note"]
                            )
                            
                            # Store current expander state
                            st.session_state.expanded_followup[row_key] = should_expand
                            
                            # Create a safe expander title (truncate if too long)
                            expander_title = f"📞 {customer_name[:30]}{'...' if len(customer_name) > 30 else ''} — Follow Up: {followup_date}"
                            
                            try:
                                # FIXED: Removed 'key' parameter for compatibility with older Streamlit versions
                                with st.expander(
                                    expander_title, 
                                    expanded=should_expand
                                    # Removed: key=f"expander_tab2_{row_key}"  # Not supported in older Streamlit
                                ):
                                    colA, colB = st.columns(2)
                                    
                                    with colA:
                                        phone = str(row.get('customer_phone', 'N/A')).strip()
                                        business = str(row.get('customer_business', 'N/A')).strip()
                                        product = str(row.get('product_interest', 'N/A')).strip()
                                        
                                        st.write(f"**📞 Phone:** {phone if phone != 'nan' else 'N/A'}")
                                        st.write(f"**🏢 Business:** {business if business != 'nan' else 'N/A'}")
                                        st.write(f"**💰 Product:** {product if product != 'nan' else 'N/A'}")
                                    
                                    with colB:
                                        bank = str(row.get('bank_name', 'N/A')).strip()
                                        amount = str(row.get('amount_usd', 'N/A')).strip()
                                        
                                        st.write(f"**🏦 Bank:** {bank if bank != 'nan' else 'N/A'}")
                                        st.write(f"**💵 Amount:** ${amount if amount != 'nan' else 'N/A'}")
                                        st.write(f"**📉 Interest Rate:** {interest_rate}")
                                    
                                    # Notes Section
                                    notes = str(row.get("notes", "")).strip()
                                    st.markdown("---")
                                    st.markdown("### 📝 Notes")
                                    if notes and notes != "nan":
                                        st.info(notes[:500] + ("..." if len(notes) > 500 else ""))
                                    else:
                                        st.caption("No notes available.")
                                    
                                    st.markdown("---")
                                    st.markdown("### ✨ Actions")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    # ===== ACTION BUTTONS WITH CALLBACKS =====
                                    if col1.button("✅ Completed", key=f"done_tab2_{row_key}"):
                                        if update_followup_status(row_key, "Completed", "", "", formatted_rm):
                                            # Clear states after completion
                                            if row_key in st.session_state.followup_states:
                                                st.session_state.followup_states[row_key] = {
                                                    "show_reschedule": False,
                                                    "show_appointment": False,
                                                    "show_note": False,
                                                }
                                            st.session_state.expanded_followup[row_key] = False
                                            st.success("Updated successfully!")
                                            st.cache_data.clear()
                                            set_active_tab("🔄 Follow Up")
                                            st.rerun()
                                    
                                    if col2.button("🔄 Reschedule", key=f"res_tab2_{row_key}"):
                                        # Set reschedule mode
                                        st.session_state.followup_states[row_key]["show_reschedule"] = True
                                        st.session_state.followup_states[row_key]["show_appointment"] = False
                                        st.session_state.followup_states[row_key]["show_note"] = False
                                        st.session_state.expanded_followup[row_key] = True
                                        # Force stay in tab2
                                        set_active_tab("🔄 Follow Up")
                                        st.rerun()
                                    
                                    if col3.button("📅 To Appointment", key=f"appt_tab2_{row_key}"):
                                        # Set appointment mode
                                        st.session_state.followup_states[row_key]["show_appointment"] = True
                                        st.session_state.followup_states[row_key]["show_reschedule"] = False
                                        st.session_state.followup_states[row_key]["show_note"] = False
                                        st.session_state.expanded_followup[row_key] = True
                                        # Force stay in tab2
                                        set_active_tab("🔄 Follow Up")
                                        st.rerun()
                                    
                                    # ===== RESCHEDULE SECTION =====
                                    if st.session_state.followup_states[row_key]["show_reschedule"]:
                                        st.markdown("### 🔄 Reschedule Follow-up")
                                        new_date = st.date_input("New follow-up date", key=f"new_date_tab2_{row_key}")
                                        new_notes = st.text_area("Notes", key=f"new_notes_tab2_{row_key}")
                                        
                                        s1, s2 = st.columns(2)
                                        if s1.button("💾 Save", key=f"save_res_tab2_{row_key}"):
                                            if update_followup_reschedule(row_key, new_date, new_notes, formatted_rm):
                                                # Reset states after save
                                                st.session_state.followup_states[row_key]["show_reschedule"] = False
                                                st.session_state.expanded_followup[row_key] = False
                                                st.success("Updated!")
                                                st.cache_data.clear()
                                                # Force stay in tab2
                                                set_active_tab("🔄 Follow Up")
                                                st.rerun()
                                        
                                        if s2.button("❌ Cancel", key=f"cancel_res_tab2_{row_key}"):
                                            st.session_state.followup_states[row_key]["show_reschedule"] = False
                                            st.session_state.expanded_followup[row_key] = False
                                            # Force stay in tab2
                                            set_active_tab("🔄 Follow Up")
                                            st.rerun()
                                    
                                    # ===== APPOINTMENT SECTION =====
                                    if st.session_state.followup_states[row_key]["show_appointment"]:
                                        st.markdown("### 📅 Convert to Appointment")
                                        appt_date = st.date_input("Appointment date", key=f"appt_date_tab2_{row_key}")
                                        appt_notes = st.text_area("Appointment notes", key=f"appt_notes_tab2_{row_key}")
                                        
                                        a1, a2 = st.columns(2)
                                        if a1.button("🎯 Confirm", key=f"save_appt_tab2_{row_key}"):
                                            if convert_to_appointment(
                                                customer_name,
                                                appt_date,
                                                appt_notes,
                                                formatted_rm,
                                            ):
                                                # Reset states after conversion
                                                st.session_state.followup_states[row_key]["show_appointment"] = False
                                                st.session_state.expanded_followup[row_key] = False
                                                st.success("Converted!")
                                                st.cache_data.clear()
                                                # Force stay in tab2
                                                set_active_tab("🔄 Follow Up")
                                                st.rerun()
                                        
                                        if a2.button("❌ Cancel", key=f"cancel_appt_tab2_{row_key}"):
                                            st.session_state.followup_states[row_key]["show_appointment"] = False
                                            st.session_state.expanded_followup[row_key] = False
                                            # Force stay in tab2
                                            set_active_tab("🔄 Follow Up")
                                            st.rerun()
                            
                            except Exception as e:
                                st.error(f"Error displaying customer {customer_name}: {str(e)}")
                                # Show minimal info without expander
                                st.write(f"**Customer:** {customer_name}")
                                st.write(f"**Follow-up Date:** {followup_date}")
                                
                                # Add a simplified action button
                                if st.button(f"View Details for {customer_name[:20]}", key=f"simple_view_{row_key}"):
                                    st.session_state.followup_states[row_key]["show_reschedule"] = True
                                    set_active_tab("🔄 Follow Up")
                                    st.rerun()
                
                else:
                    st.info("📭 No follow-up data loaded")
        
        
            
        with tab3_inner:
            st.markdown("### 📅 Appointment")
            if st.button("🔃 Refresh Appointment"):
                st.cache_data.clear()
                st.rerun()
        
            df_followup = get_followup_data_cached()
        
            if df_followup.empty:
                st.info("📭 No appointment data available")
                
        
            current_rm = st.session_state.get("staff_id", "")
            #if not current_rm:
            #    st.warning("⚠️ Unable to detect Staff ID")
            #    st.stop()
        
            formatted_rm = str(current_rm).strip()
        
            # Normalize fields
            df_followup["next_action"] = df_followup["next_action"].astype(str).str.lower().str.strip()
            df_followup["action_after_followup"] = df_followup["action_after_followup"].astype(str).str.lower().str.strip()
            df_followup["staff_id"] = df_followup["staff_id"].astype(str).str.strip()
        
            # Appointment condition:
            appointment_customers = df_followup[
                (
                    (df_followup["next_action"] == "appointment") |
                    (df_followup["action_after_followup"] == "appointment")
                ) &
                (df_followup["staff_id"] == formatted_rm)
            ].copy()
            
            # ✅ Convert last_updated to datetime
            if "last_updated" in appointment_customers.columns:
                appointment_customers["last_updated"] = pd.to_datetime(
                    appointment_customers["last_updated"], errors="coerce"
                )
            
                # ✅ Sort: most recent update first
                appointment_customers = appointment_customers.sort_values(
                    by="last_updated", ascending=False
                )
            
            if appointment_customers.empty:
                st.success("✅ You have no appointments scheduled.")
                #st.stop()
        
            st.info(f"📋 You have **{len(appointment_customers)} appointments**")
        
            # Loop through each appointment
            for idx, row in appointment_customers.iterrows():
        
                row_key = f"{row.get('customer_id')}_{idx}"
                customer_name = row.get("customer_name", "N/A")
                appt_date = row.get("appointment_date", "N/A")
        
                with st.expander(f"📞 {customer_name} — Appointment: {appt_date}", expanded=False):
        
                    colA, colB = st.columns(2)
        
                    with colA:
                        st.write(f"**📞 Phone:** {row.get('customer_phone', 'N/A')}")
                        st.write(f"**🏢 Business:** {row.get('customer_business', 'N/A')}")
                        st.write(f"**💰 Product:** {row.get('product_interest', 'N/A')}")
        
                    with colB:
                        st.write(f"**🏦 Bank:** {row.get('bank_name', 'N/A')}")
                        st.write(f"**💵 Amount:** ${row.get('amount_usd', 'N/A')}")
                        st.write(f"**📝 Status:** Appointment")

                    # Notes Section
                    notes = row.get("notes", "")
                    st.markdown("---")
                    st.markdown("### 📝 Notes")
                    if notes:
                        st.success(notes)
                    else:
                        st.caption("No notes available.")
        
                    st.markdown("---")
                    st.markdown("### ✨ Actions")
        
                    # Action form
                    with st.form(key=f"form_actions_{row_key}"):
        
                        col1, col2, col3, col4 = st.columns(4)
        
                        with col1:
                            act_completed = st.form_submit_button("✅ Completed")
        
                        with col2:
                            act_reschedule = st.form_submit_button("🔄 Reschedule")
        
                        with col3:
                            act_back_to_follow = st.form_submit_button("📞 Back to Follow-up")
        
                        with col4:
                            act_note = st.form_submit_button("📝 Add Note")
        
                        # ---- Handle Actions ----
                        if act_completed:
                            if update_followup_status(row_key, "Completed", "", "", formatted_rm):
                                        st.success(f"✅ Follow-up completed for {customer_name}")
                                        st.rerun()
                            #if update_followup_status(row_key, "Completed", "", formatted_rm):
                            #    st.success(f"Completed appointment for {customer_name}")
                            #    st.rerun()
        
                        if act_reschedule:
                            st.session_state[f"show_reschedule_{row_key}"] = True
        
                        if act_back_to_follow:
                            st.session_state[f"show_back_follow_{row_key}"] = True
        
                        if act_note:
                            st.session_state[f"show_note_{row_key}"] = True
        
                    # ---- Reschedule UI ----
                    if st.session_state.get(f"show_reschedule_{row_key}", False):
                        st.markdown("### 🔄 Reschedule Appointment")
        
                        new_appt = st.date_input("New Appointment Date", key=f"new_appt_{row_key}")
                        notes = st.text_area("Notes", key=f"new_appt_notes_{row_key}")
        
                        save, cancel = st.columns(2)
        
                        with save:
                            if st.button("💾 Save New Appointment", key=f"save_appt_{row_key}"):
                                if update_followup_reschedule(row_key, new_appt, notes, formatted_rm):
                                    st.success("Rescheduled successfully")
                                    st.session_state[f"show_reschedule_{row_key}"] = False
                                    st.rerun()
        
                        with cancel:
                            if st.button("❌ Cancel", key=f"cancel_appt_{row_key}"):
                                st.session_state[f"show_reschedule_{row_key}"] = False
                                st.rerun()
        
                    # ---- Convert back to follow-up ----
                    if st.session_state.get(f"show_back_follow_{row_key}", False):
                        st.markdown("### 📞 Convert to Follow-Up")
        
                        new_date = st.date_input("Follow-up date", key=f"back_follow_date_{row_key}")
                        notes = st.text_area("Notes", key=f"back_follow_notes_{row_key}")
        
                        save, cancel = st.columns(2)
        
                        with save:
                            if st.button("💾 Convert to Follow-Up", key=f"btn_back_follow_{row_key}"):
                                if update_followup_reschedule(row_key, new_date, notes, formatted_rm):
                                    st.success("Converted back to follow-up")
                                    st.session_state[f"show_back_follow_{row_key}"] = False
                                    st.rerun()
        
                        with cancel:
                            if st.button("❌ Cancel", key=f"cancel_back_follow_{row_key}"):
                                st.session_state[f"show_back_follow_{row_key}"] = False
                                st.rerun()
        
                    # ---- Add Note ----
                    if st.session_state.get(f"show_note_{row_key}", False):
                        st.markdown("### 📝 Add Note")
        
                        note = st.text_area("Write your note", key=f"note_add_{row_key}")
        
                        save, cancel = st.columns(2)
        
                        with save:
                            if st.button("💾 Save Note", key=f"btn_note_{row_key}"):
                                if add_followup_note(row_key, note, formatted_rm):
                                    st.success("Note added")
                                    st.session_state[f"show_note_{row_key}"] = False
                                    st.rerun()
        
                        with cancel:
                            if st.button("❌ Cancel", key=f"cancel_note_{row_key}"):
                                st.session_state[f"show_note_{row_key}"] = False
                                st.rerun()
        

        with tab4_inner:
            st.markdown("📜 Your Historical Called")

            # Refresh button
            if st.button("🔃 Refresh Historical List"):
                st.cache_data.clear()
                st.rerun()

            # Load all follow-up or call data
            df_followup = get_followup_data_cached()

            if not df_followup.empty:
                current_rm = st.session_state.get("staff_id", "")
                if current_rm:
                    formatted_rm = str(current_rm).strip()

                    # ✅ Show ALL historical records for this RM
                    historical_calls = df_followup[
                        df_followup["staff_id"].apply(lambda x: str(x).strip())
                        == formatted_rm
                    ].copy()

                    # Optional: sort by most recent date if column exists
                    #if "appointment_date" in historical_calls.columns:
                    #    historical_calls["appointment_date"] = pd.to_datetime(
                    #        historical_calls["appointment_date"], errors="coerce"
                    #    )
                    #    historical_calls = historical_calls.sort_values(
                    #        "appointment_date", ascending=False
                    #    )
                    if "last_updated" in historical_calls.columns:
                        historical_calls["last_updated"] = pd.to_datetime(
                            historical_calls["last_updated"], errors="coerce"
                        )
                        historical_calls = historical_calls.sort_values(
                            "last_updated", ascending=False
                        )

                    # Display records
                    if not historical_calls.empty:
                        st.success(f"Showing {len(historical_calls)} historical calls for RM {formatted_rm}")

                        for idx, row in historical_calls.iterrows():
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("appointment_date", "N/A")
                            last_update = row.get("last_updated", "N/A")

                            with st.expander(f"📞 {customer_name} - Date: {last_update}", expanded=False):
                                col_info1, col_info2 = st.columns(2)

                                with col_info1:
                                    st.write(f"**📞 Phone:** {row.get('customer_phone', 'N/A')}")
                                    st.write(f"**🏢 Business:** {row.get('customer_business', 'N/A')}")
                                    st.write(f"**💰 Product:** {row.get('product_interest', 'N/A')}")

                                with col_info2:
                                    st.write(f"**🏦 Bank:** {row.get('bank_name', 'N/A')}")
                                    st.write(f"**💵 Amount:** ${row.get('amount_usd', 'N/A')}")
                                    st.write(f"**📅 Follow-up / Call Date:** {last_update}")

                                st.markdown("---")
                                st.markdown("### 🗒️ Notes")
                                st.write(row.get("notes", "No additional notes."))
                    else:
                        st.info("No historical records found for your RM code.")
                else:
                    st.warning("No RM code found in session state. Please log in again.")
            else:
                st.warning("No data available to display.")


        ###
        with tab5_inner:
            st.markdown("### 📞 Add Customer")
            st.info("Check if the customer exists before adding a new record")
        
            # ----------------------------
            # Initialize Session States
            # ----------------------------
            for key in ["picked_up_state", "not_picked_state", "current_phone_checked"]:
                if key not in st.session_state:
                    st.session_state[key] = None
        
            # ----------------------------
            # Load Follow-up Data
            # ----------------------------
            df = pd.DataFrame(get_followup_data_cached())
        
            # ----------------------------
            # Phone Input
            # ----------------------------
            col1, col2 = st.columns([2, 1])
            with col1:
                new_phone = st.text_input(
                    "📱 Enter Customer Phone Number",
                    placeholder="e.g., 012345678",
                    key="new_customer_phone",
                )
        
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                continue_btn = st.button("➡️ Continue", use_container_width=True)
        
            # ----------------------------
            # Handle Continue
            # ----------------------------
            if continue_btn:
                if not new_phone.strip():
                    st.warning("⚠️ Please enter a phone number.")
                else:
                    st.session_state.current_phone_checked = new_phone.strip()
                    st.session_state.picked_up_state = None
                    st.session_state.not_picked_state = None
        
            # ----------------------------
            # MAIN FLOW
            # ----------------------------
            current_phone = st.session_state.current_phone_checked
        
            if current_phone:
                clean_phone = clean_phone_number(current_phone)
        
                if not df.empty and "customer_phone" in df.columns:
                    df["clean_phone"] = df["customer_phone"].apply(clean_phone_number)
                    existing_customer = df[df["clean_phone"] == clean_phone].head(1)
                else:
                    existing_customer = pd.DataFrame()
        
                # ----------------------------
                # EXISTING CUSTOMER
                # ----------------------------
                if not existing_customer.empty:
                    cust = existing_customer.iloc[0]
                    st.warning("⚠️ Customer already exists")
        
                    colA, colB = st.columns(2)
                    with colA:
                        st.write(f"**👤 Name:** {cust.get('customer_name','N/A')}")
                        st.write(f"**📞 Phone:** {cust.get('customer_phone','N/A')}")
                    with colB:
                        st.write(f"**🏢 Business:** {cust.get('customer_business','N/A')}")
                        st.write(f"**📊 Call Status:** {cust.get('call_status','N/A')}")
        
                    st.info("ℹ️ This customer is already in Follow-Up records.")
        
                # ----------------------------
                # NEW CUSTOMER
                # ----------------------------
                else:
                    st.success("✅ Phone number not found")
        
                    # ----------------------------
                    # PICK UP QUESTION
                    # ----------------------------
                    if st.session_state.picked_up_state is None:
                        st.info("📞 Did the customer pick up the call?")
                        col_yes, col_no = st.columns(2)
        
                        with col_yes:
                            if st.button("✅ Yes - Picked Up", use_container_width=True):
                                st.session_state.picked_up_state = True
        
                        with col_no:
                            if st.button("❌ No - Not Picked Up", use_container_width=True):
                                followup_data = {
                                    "customer_name": "Unknown",
                                    "customer_phone": clean_phone,
                                    "staff_id": st.session_state.get("staff_id", "N/A"),
                                    "call_status": "Not Pick Up",
                                    "next_action": "Call Back",
                                    "followup_date": datetime.now().strftime("%Y-%m-%d"),
                                    "call_notes": "Customer did not pick up",
                                }
        
                                if save_followup_to_google_sheets(followup_data):
                                    st.success("✅ 'Not Picked Up' saved")
                                    st.session_state.current_phone_checked = None
                                    st.session_state.picked_up_state = None
        
                    # ----------------------------
                    # CUSTOMER FORM (PICKED UP)
                    # ----------------------------
                    elif st.session_state.picked_up_state:
                        st.markdown("---")
                        st.markdown("### 📝 New Customer Information")
        
                        with st.form("new_customer_form"):
                            colA, colB = st.columns(2)
        
                            with colA:
                                name = st.text_input("👤 Full Name *")
                                business = st.text_input("🏢 Business *")
                                source = st.text_input("📌 Source")
        
                            with colB:
                                st.text_input("📞 Phone", value=clean_phone, disabled=True)
                                bank = st.text_input("🏦 Current Bank")
                                amount = st.number_input("💰 Loan Amount (USD)", min_value=0)
        
                            product = st.selectbox("📂 Product Type", ["Loan", "TD", "Card", "Other"])
                            interest = st.text_input("📉 Interest Rate (%)")
        
                            next_action = st.radio(
                                "🎯 Next Action",
                                ["Follow Up", "Appointment", "No Action Needed", "Drop"],
                                horizontal=True,
                            )
        
                            next_date = None
                            if next_action in ["Follow Up", "Appointment"]:
                                next_date = st.date_input("📅 Next Action Date")
        
                            notes = st.text_area("📝 Notes")
        
                            submitted = st.form_submit_button("💾 Save Customer")
        
                            if submitted:
                                if not name or not business:
                                    st.error("❌ Name and Business are required")
                                else:
                                    followup_data = {
                                        "customer_name": name,
                                        "customer_phone": clean_phone,
                                        "customer_business": business,
                                        "staff_id": st.session_state.get("staff_id", "N/A"),
                                        "call_status": "Pick Up",
                                        "source": source,
                                        "product_interest": product,
                                        "bank_name": bank,
                                        "amount_usd": amount,
                                        "interest": interest,
                                        "next_action": next_action,
                                        "followup_date": next_date.strftime("%Y-%m-%d") if next_date else "",
                                        "call_notes": notes,
                                        "appointment_date": next_date.strftime("%Y-%m-%d") if next_action == "Appointment" else "",
                                    }
        
                                    if save_followup_to_google_sheets(followup_data):
                                        st.success(f"✅ Customer '{name}' saved")
                                        st.balloons()
                                        st.session_state.current_phone_checked = None
                                        st.session_state.picked_up_state = None
        
            # ----------------------------
            # RESET BUTTON
            # ----------------------------
            if st.session_state.current_phone_checked:
                if st.button("🔄 Start Over", use_container_width=True):
                    st.session_state.current_phone_checked = None
                    st.session_state.picked_up_state = None
                    st.session_state.not_picked_state = None

    with tab2:
        st.markdown(
            """
            <h1 style="
                font-family: 'Segoe UI', sans-serif;
                font-size: 32px;
                font-weight: 700;
                color: #14532D;
                margin-bottom: 10px;
            ">
                📊 Performance Dashboard
            </h1>
            """,
            unsafe_allow_html=True
        )
        # Add refresh button and functionality
        col1, col2 = st.columns([10, 1])
        
        with col2:
            if st.button("🔄 Refresh Data", type="secondary"):
                # Clear the cache for dashboard data
                st.cache_data.clear()
                st.rerun()

        #st.title("📊 Performance Dashboard")
        df = get_followup_data_cached()
        staff_master = load_staff_master_df()
        
        if not df.empty:
            current_id = str(st.session_state.get("staff_id", "")).strip()
            
            # FIX: Handle the case where user_role might be a Series or might not exist
            user_role_from_state = st.session_state.get("user_role")
            if isinstance(user_role_from_state, pd.Series):
                # If it's a Series, get the first value or empty string
                current_role = str(user_role_from_state.iloc[0] if len(user_role_from_state) > 0 else "")
            elif isinstance(user_role_from_state, str):
                current_role = user_role_from_state.strip().lower()
            else:
                # Default to empty string if None or other type
                current_role = ""
            
            df["staff_id"] = df["staff_id"].astype(str).str.strip()
            
            # Normalize staff_id in df
            df["staff_id"] = df["staff_id"].astype(str).str.strip()
            
            # Check if staff_master has the required columns
            if "staff_id" in staff_master.columns:
                staff_master["staff_id"] = staff_master["staff_id"].astype(str).str.strip()
            
            if "branch_manager" in staff_master.columns:
                staff_master["branch_manager"] = (
                    staff_master["branch_manager"].astype(str).str.strip()
                )
            
            if "role" in staff_master.columns:
                staff_master["role"] = staff_master["role"].astype(str).str.strip()
            
            # --- ADMIN: see everything ---
            # FIX: Handle the string conversion properly
            current_role_str = str(current_role).lower() if current_role else ""
            is_admin = (current_id == "90020759") or ("admin" in current_role_str)
            
            if is_admin:
                st.info("🔓 Admin Mode Enabled: Showing ALL customer follow-up data")
                # df = df (no filter)
            
            # --- BRANCH MANAGER: see only staff under them (and themself) ---
            elif current_role_str in ["branch manager", "bm", "branch head"]:
                # Check if required columns exist
                if "staff_id" not in staff_master.columns or "branch_manager" not in staff_master.columns:
                    st.error("❌ Missing required columns in staff master data")
                    df = df[df["staff_id"] == current_id]  # Show only own data
                else:
                    # staff_master: each row has staff_id + branch_manager = manager staff id
                    managed_staff = (
                        staff_master[
                            (staff_master["branch_manager"] == current_id)
                            | (staff_master["staff_id"] == current_id)  # include self
                        ]["staff_id"]
                        .unique()
                        .tolist()
                    )
                    
                    df = df[df["staff_id"].isin(managed_staff)]
                    st.info(
                        f"🏦 Branch Manager view — you are seeing calls from "
                        f"{len(managed_staff)} staff (including yourself)."
                    )
            
            # --- NORMAL RM: see only own data ---
            else:
                df = df[df["staff_id"] == current_id]
    
                # optional: st.info("👤 RM view — showing only your own calls")
        
        if df.empty:
            st.warning("⚠️ No data found in FollowUp sheet.")
        else:
            # Clean column names
            df.columns = df.columns.str.strip().str.lower()

            # --- Aggregate Metrics ---
            total_calls = len(df)
            picked_up = df[
                df["call_status"].str.contains("pick", case=False, na=False)
            ].shape[0]
            follow_ups = df[
                df["next_action"].str.contains("follow", case=False, na=False)
            ].shape[0]
            appointments = df[
                df["next_action"].str.contains("appointment", case=False, na=False)
            ].shape[0]
            closed_deals = df[
                df["call_status"].str.contains("close", case=False, na=False)
            ].shape[0]
            
            # --- CARD DISPLAY ---
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                metric_card("Total Calls", f"{total_calls:,}", "📊")
            with col2:
                metric_card("Picked Up", f"{picked_up:,}", "📞")
            with col3:
                metric_card("Follow Up", f"{follow_ups:,}", "🔄")
            with col4:
                metric_card("Appointment", f"{appointments:,}", "📅")
            with col5:
                metric_card("Closed Deal", f"{closed_deals:,}", "✅")
        
            st.markdown("---")
            
            # --- Prepare Charts ---
            action_counts = (
                df["next_action"].fillna("None").value_counts().reset_index()
            )
            action_counts.columns = ["Next Action", "Count"]
            fig_action = px.bar(
                action_counts,
                x="Next Action",
                y="Count",
                text="Count",
                color="Next Action",
                color_discrete_sequence=px.colors.sequential.Emrld,
            )
        
            fig_action.update_traces(
                marker=dict(
                    line=dict(color="black", width=2),
                    opacity=0.95
                ),
                textposition="outside",
            )
        
            fig_action.update_layout(
                title="📞 Next Action Trend",
                xaxis_title="",
                yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                bargap=0.2,
                title_font=dict(size=23, family="Segoe UI", color="#14532D"),
            )
        
            status_counts = df["call_status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_status = px.pie(
                status_counts,
                names="Status",
                values="Count",
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Emrld,
            )
        
            fig_status.update_traces(
                textinfo="percent",
                textposition="inside",
                textfont=dict(size=14, color="black"),
                marker=dict(line=dict(color="black", width=2)),
                pull=[0.06] * len(status_counts),
            )
            fig_status.update_layout(
                title="📞 Status Breakdown",
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title_font=dict(size=23, family="Segoe UI Semibold", color="#14532D"),
            )
            
            # --- Follow-up Status Bar Chart ---
            # Check if column exists before processing
            if "status_followup" in df.columns:
                follow_up_counts = (
                    df["status_followup"].fillna("None").value_counts().reset_index()
                )
                follow_up_counts.columns = ["Follow Up Status", "Count"]
                
                fig_followup = px.bar(
                    follow_up_counts,
                    x="Follow Up Status",
                    y="Count",
                    text="Count",
                    color="Follow Up Status",
                    color_discrete_sequence=px.colors.sequential.Emrld,
                    title="📊 Follow-up Status Distribution",
                )
        
                fig_followup.update_traces(
                    textposition="inside",
                    textfont=dict(size=14, color="black"),
                    marker=dict(
                        line=dict(color="black", width=2),
                        opacity=0.95,
                    )
                )
        
                fig_followup.update_layout(
                    bargap=0.25,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_title=None,
                    yaxis_title=None,
                    title_font=dict(size=23, family="Segoe UI Semibold", color="#14532D"),
                    xaxis=dict(showgrid=False, tickfont=dict(size=13, color="#1F2937")),
                    yaxis=dict(showgrid=False, tickfont=dict(size=13, color="#1F2937")),
                    showlegend=False,
                )
            else:
                fig_followup = None
            
            # Product Distribution Chart
            product_counts = df["product_interest"].value_counts().reset_index()
            product_counts.columns = ["Product", "Count"]
            fig_product = px.pie(
                product_counts,
                names="Product",
                values="Count",
                hole=0.45,
                title="📊 Product Distribution",
                color_discrete_sequence=px.colors.sequential.Emrld,
            )
        
            fig_product.update_traces(
                textinfo="percent+label",
                textfont=dict(size=14, color="black"),
                pull=[0.06] * len(product_counts),
                marker=dict(line=dict(color="black", width=2))
            )
        
            fig_product.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title_font=dict(size=23, family="Segoe UI Semibold", color="#14532D"),
                showlegend=False,
            )
            
            # --- Display Charts ---
            st.markdown("""
                <h2 style="
                    font-family: 'Segoe UI Semibold', sans-serif;
                    font-size: 30px;
                    color: #14532D;
                    margin-bottom: 10px;
                ">
                    📞 Call Insights
                </h2>
            """, unsafe_allow_html=True)
            
            # First row of charts
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.plotly_chart(fig_action, use_container_width=True)
            with col_chart2:
                st.plotly_chart(fig_status, use_container_width=True)
            
            # Second row of charts
            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                if fig_followup is not None:
                    st.plotly_chart(fig_followup, use_container_width=True)
            with col_chart4:
                st.plotly_chart(fig_product, use_container_width=True)
            
            # -----------------------------
            # 📋 CALL REPORT TABLE (FULL WIDTH)
            # -----------------------------
            # --- Date range selector ---
            st.subheader("📅 Filter by Last Updated Date")
            
            col1, col2 = st.columns(2)
            
            with col1:
                start_date = st.date_input(
                    "Start date",
                    value=pd.Timestamp.now().date() - pd.Timedelta(days=7)
                )
            
            with col2:
                end_date = st.date_input(
                    "End date",
                    value=pd.Timestamp.now().date()
                )
            st.markdown("""
                <h2 style="
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 24px;
                    font-weight: 600;
                    color: #14532D;
                    margin-top: 25px;
                ">
                    📋 Detailed Call Report
                </h2>
            """, unsafe_allow_html=True)
            
            # Select only relevant columns
            report_columns = [
                "customer_name", "customer_business", "customer_phone", "source",
                "call_status", "product_interest", "bank_name", "amount_usd",
                "interest", "next_action", "notes", "staff_id"
            ]
            
            # Define new column names
            new_column_names = {
                "customer_name": "Customer Name", "customer_business": "Business",
                "customer_phone": "Phone", "source": "Source", "call_status": "Status",
                "product_interest": "Product Interest", "bank_name": "Bank Name",
                "amount_usd": "Amount (USD)", "interest": "Interest Level",
                "next_action": "Next Action", "notes": "Notes", "staff_id": "ID"
            }
        
            
            # Today's date filter
            today_date = pd.Timestamp.now().date()
            
            df_report = df.copy()
            
            # Apply date filter
            if "last_updated" in df_report.columns:
                # 1️⃣ Try ISO format first
                df_report["last_updated_dt"] = pd.to_datetime(
                    df_report["last_updated"],
                    format="%Y-%m-%d %H:%M:%S",
                    errors="coerce"
                )
                # 2️⃣ Fix remaining NaT using US format
                mask = df_report["last_updated_dt"].isna()
                if mask.any():
                    df_report.loc[mask, "last_updated_dt"] = pd.to_datetime(
                        df_report.loc[mask, "last_updated"],
                        format="%m/%d/%Y %H:%M:%S",
                        errors="coerce"
                    )
                df_report = df_report[
                    (df_report["last_updated_dt"].dt.date >= start_date) &
                    (df_report["last_updated_dt"].dt.date <= end_date)
                ]
                #df_report = df_report[
                #    df_report["last_updated_dt"].dt.date == today_date
                #]
                # OPTIONAL — drop helper column
                df_report = df_report.drop(columns=["last_updated_dt"], errors="ignore")
            
            # Filter to existing columns only
            existing_cols = [col for col in report_columns if col in df_report.columns]
            df_report = df_report[existing_cols]
            
            # Only rename columns that exist
            rename_dict = {
                col: new_column_names[col] 
                for col in existing_cols 
                if col in new_column_names
            }
            df_report = df_report.rename(columns=rename_dict)
            
            # -----------------------------
            # 🎨 Custom Table Styling
            # -----------------------------
            st.markdown(
                """
                <style>
                    .full-width-table table {
                        width: 100% !important;
                        border-collapse: collapse;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 14px;
                    }
        
                    .full-width-table thead th {
                        background-color: #14532D !important;
                        color: white !important;
                        font-weight: 600;
                        padding: 10px;
                        border-bottom: 2px solid #0f3f21;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 6px;
                    }
        
                    .full-width-table tbody td {
                        padding: 10px;
                        border-bottom: 1px solid #E0E0E0;
                    }
        
                    .full-width-table tbody tr:nth-child(even) {
                        background-color: #F7F9F8;
                    }
        
                    .full-width-table tbody tr:hover {
                        background-color: #E7F3EC !important;
                        transition: background-color 0.2s ease;
                    }
                </style>
            """,
                unsafe_allow_html=True,
            )
            
            # Render table with index=False
            st.markdown('<div class="full-width-table">', unsafe_allow_html=True)
            
            if not df_report.empty:
                st.dataframe(
                    df_report, 
                    use_container_width=True, 
                    height=600, 
                    hide_index=True
                )
            else:
                st.info("No call records found for today.")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
# Main app logic
if not st.session_state.logged_in:
    login_form()
else:
    main_app()
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
