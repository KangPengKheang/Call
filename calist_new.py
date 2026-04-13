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

@st.cache_data(ttl=3000)
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
        
@st.cache_data(ttl=3000)  # Cache for 5 minutes
def get_followup_data_cached():
    try:
        client = setup_gsheets()
        if client:
            sheet = client.open_by_key(SHEET_ID)
            followup_sheet = sheet.worksheet("FollowUp")
            data = followup_sheet.get_all_records()
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading follow-up data: {e}")
    return pd.DataFrame()


@st.cache_data(ttl=1000)
def load_customers_from_sheet_cached():
    """Cached version of customer loading"""
    return load_customers_from_sheet()


# Page config
st.set_page_config(page_title="SALE CALL MANAGEMENT", layout="wide", page_icon="📞")
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
            customer_data["rm_code"],
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
                "rm_code",
                "source",
                "call_status",
                "product_interest",
                "bank_name",
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
            followup_data.get("rm_code", ""),
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

            st.sidebar.error(f"Detailed error: {traceback.format_exc()}")

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

@st.cache_resource(ttl=3600)
def setup_gsheets():
    """Initialize Google Sheets connection with proper scopes"""
    try:
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
            st.info("💡 Make sure your secrets.toml has all required fields")
            return None

        # Use Credentials from secrets
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        st.sidebar.success("✅ Google Sheets connection established")
        return client  
    except Exception as e:
        st.error(f"❌ Error setting up Google Sheets: {e}")
        return None
        

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


# Change the authentication to accept both formats
def authenticate_user(staff_id):
    """Authenticate user based on staff ID only"""
    try:
        # Simple check - you can make this more sophisticated
        if staff_id and staff_id.strip():
            # You can add more validation here
            # Example: Check if staff ID exists in your database
            valid_staff_ids = [
                "90020644",
                "90021792",
                "90016593",
                "90019686",
                "90020759",
                "002",
                "003",
                "90019425",
                "90019509",
            ]
            return staff_id.upper() in valid_staff_ids
        return False

    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False


def get_rm_code_from_staff_id(staff_id):
    """Map staff ID to RM code"""
    staff_to_rm_mapping = {
        "90021792": "001",
        "001": "001",
        "90019509": "002",
        "002": "002",
        "90020644": "003",
        "90019686": "004",
        "90020758": "004",
        "90020759": "006",
        "90019425": "010",
        # Add more mappings as needed
    }

    return staff_to_rm_mapping.get(staff_id.upper(), staff_id)


# Login form
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

    with st.form("login_form", clear_on_submit=False):
        staff_id = st.text_input(
            "🆔 Staff ID",
            max_chars=10,
            placeholder="Enter your staff ID",
            help="Enter your employee/staff identification number",
        )
        submitted = st.form_submit_button("Login →", use_container_width=True)

        if submitted:
            if authenticate_user(staff_id):
                st.session_state.logged_in = True
                st.session_state.staff_id = staff_id

                # Get RM code from staff ID
                rm_code = get_rm_code_from_staff_id(staff_id)
                st.session_state.rm_code = rm_code

                # with st.spinner("Loading customer data..."):
                st.session_state.customers = load_customers_from_sheet_cached()
                st.rerun()
            else:
                st.error("❌ Invalid Staff ID")

    st.markdown("</div></div>", unsafe_allow_html=True)


# Add helper functions for Google Sheets operations
def update_followup_status(row_key, new_status, new_date, notes, rm_code):
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
            sheet_rm_code = str(sheet_row[headers.index("rm_code")]).strip().zfill(3)
            sheet_customer_id = sheet_row[headers.index("customer_id")]

            if sheet_rm_code == rm_code and str(sheet_customer_id) == customer_id:
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


def update_followup_reschedule(row_key, new_date, new_notes, rm_code):
    """Reschedule a follow-up"""
    # notes = (
    #    f"Rescheduled to {new_date}. {new_notes}"
    #    if new_notes
    #    else f"Rescheduled to {new_date}"
    # )
    return update_followup_status(row_key, "Reschedule", new_date, new_notes, rm_code)


def convert_to_appointment(row_key, appointment_date, appointment_notes, rm_code):
    """Convert follow-up to appointment"""
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
            sheet_rm_code = str(sheet_row[headers.index("rm_code")]).strip().zfill(3)
            sheet_customer_id = sheet_row[headers.index("customer_id")]

            if sheet_rm_code == rm_code and str(sheet_customer_id) == customer_id:
                # Update to appointment
                followup_sheet.update_cell(
                    idx, headers.index("action_after_followup") + 1, "Appointment"
                )
                followup_sheet.update_cell(
                    idx, headers.index("appointment_date") + 1, str(appointment_date)
                )
                # followup_sheet.update_cell(
                #    idx, headers.index("appointment_date") + 1, str(appointment_date)
                # )

                # Update notes
                # current_notes = (
                #    sheet_row[headers.index("notes")]
                #    if len(sheet_row) > headers.index("notes")
                #    else ""
                # )
                # updated_notes = f"{current_notes}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}: Converted to appointment - {appointment_notes}"
                # followup_sheet.update_cell(
                #    idx, headers.index("notes") + 1, updated_notes.strip()
                # )

                # Update last_updated
                followup_sheet.update_cell(
                    idx,
                    headers.index("last_updated") + 1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                return True
        return False
    except Exception as e:
        st.error(f"❌ Error converting to appointment: {e}")
        return False


def add_followup_note(row_key, new_note, rm_code):
    """Add note to follow-up"""
    return update_followup_status(row_key, "Follow Up", new_note, rm_code)


def add_sample_customer_data(existing_df):
    """Add sample customer data for demonstration"""
    if not existing_df.empty:
        return existing_df
    sample_data = {
        "id": range(1, 51),
        "name": [f"Customer {i}" for i in range(1, 51)],
        "business": np.random.choice(
            ["Family Business", "SME", "Enterprise", "Startup"], 50
        ),
        "phone": [
            f"010 {np.random.randint(100, 999)} {np.random.randint(100, 999)}"
            for _ in range(50)
        ],
        "source": np.random.choice(
            ["Construction", "Services", "Manufacturing", "Food & Beverage"], 50
        ),
        "rm_code": np.random.choice(["001", "002", "003", "004"], 50),
        "status": np.random.choice(
            ["Called", "Not Reached", "Busy", "Wrong Number"], 50
        ),
        "create_date": pd.date_range("2024-01-01", periods=50, freq="D"),
        "notes": [""] * 50,
    }
    return pd.DataFrame(sample_data)


def add_sample_followup_data(existing_df):
    """Add sample followup data for demonstration"""
    if not existing_df.empty:
        return existing_df

    sample_data = {
        "customer_name": [f"Customer {i}" for i in range(1, 31)],
        "customer_id": range(1, 31),
        "customer_business": np.random.choice(
            ["Family Business", "SME", "Enterprise"], 30
        ),
        "customer_phone": [
            f"010 {np.random.randint(100, 999)} {np.random.randint(100, 999)}"
            for _ in range(30)
        ],
        "rm_code": np.random.choice(["001", "002", "003", "004"], 30),
        "product_interest": np.random.choice(
            ["Loan", "TD", "KHQR", "VISA", "Other", "No"], 30
        ),
        "bank_name": np.random.choice(["ABA", "ACLEDA", "Chip Mong", "Prince", ""], 30),
        "amount_usd": np.random.choice([0, 5000, 10000, 25000, 50000, 100000], 30),
        "next_action": np.random.choice(
            ["Follow Up", "Appointment", "Completed", "Drop"], 30
        ),
        "followup_date": pd.date_range("2024-01-01", periods=30, freq="D"),
        "status": np.random.choice(["Completed", "Pending", "In Progress"], 30),
        "followup_count": np.random.randint(1, 5, 30),
        "last_updated": pd.date_range("2024-01-01", periods=30, freq="D"),
        "appointment_date": pd.date_range("2024-01-05", periods=30, freq="D"),
    }
    return pd.DataFrame(sample_data)


# --- Metric Card Function ---
def display_metric_card(title, value, subtitle):
    st.markdown(
        f"""
        <style>
        .metric-card {{
            background: linear-gradient(135deg, #e6f4ea 0%, #f4fff8 100%);
            padding: 18px 12px;
            border-radius: 16px;
            border: 1.5px solid rgba(3,140,62,0.3);
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            text-align: center;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .metric-card:hover {{
            transform: scale(1.03);
            box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        }}
        .metric-title {{
            font-size: 1.1rem;
            color:#047857;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 800;
            color:#065f46;
            margin: 6px 0;
        }}
        .metric-subtitle {{
            font-size: 0.9rem;
            color:#065f46;
            opacity: 0.8;
        }}
        </style>

        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_rm_performance(customers_df, followups_df):
    """Show RM-wise performance metrics"""

    if customers_df.empty:
        st.info("No customer data available")
        return

    col1, col2 = st.columns(2)

    with col1:
        # RM Performance Summary
        rm_stats = (
            customers_df.groupby("rm_code")
            .agg({"id": "count"})
            .rename(columns={"id": "total_calls"})
        )

        # Add completed calls if status column exists
        if "status" in customers_df.columns:
            rm_stats["completed_calls"] = customers_df.groupby("rm_code")[
                "status"
            ].apply(lambda x: (x == "Called").sum() if "Called" in x.values else 0)
        else:
            rm_stats["completed_calls"] = 0

        # Merge with followup data
        if not followups_df.empty and "rm_code" in followups_df.columns:
            rm_followups = (
                followups_df.groupby("rm_code")
                .agg({"customer_id": "count"})
                .rename(columns={"customer_id": "successful_followups"})
            )

            if "product_interest" in followups_df.columns:
                rm_followups["loan_interests"] = followups_df.groupby("rm_code")[
                    "product_interest"
                ].apply(lambda x: (x == "Loan").sum())

            if "next_action" in followups_df.columns:
                rm_followups["appointments"] = followups_df.groupby("rm_code")[
                    "next_action"
                ].apply(lambda x: (x == "Appointment").sum())

            rm_performance = rm_stats.merge(
                rm_followups, on="rm_code", how="left"
            ).fillna(0)
        else:
            rm_performance = rm_stats
            rm_performance["successful_followups"] = 0
            rm_performance["loan_interests"] = 0
            rm_performance["appointments"] = 0

        rm_performance["conversion_rate"] = (
            rm_performance["successful_followups"] / rm_performance["total_calls"] * 100
        ).round(1)

        st.subheader("🏆 RM Performance Ranking")
        st.dataframe(
            rm_performance.style.format(
                {"conversion_rate": "{:.1f}%"}
            ).background_gradient(cmap="Blues"),
            use_container_width=True,
        )

    with col2:
        if not rm_performance.empty:
            # Conversion Rate by RM
            fig = px.bar(
                rm_performance.reset_index(),
                x="rm_code",
                y="conversion_rate",
                title="Conversion Rate by RM",
                color="conversion_rate",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(xaxis_title="RM Code", yaxis_title="Conversion Rate (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No RM performance data available")

    # Detailed RM Performance
    st.subheader("📊 Detailed RM Metrics")

    for rm_code in customers_df["rm_code"].unique():
        rm_customers = customers_df[customers_df["rm_code"] == rm_code]
        rm_followups = (
            followups_df[followups_df["rm_code"] == rm_code]
            if not followups_df.empty
            else pd.DataFrame()
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(f"RM {rm_code} - Total Calls", len(rm_customers))
        with col2:
            successful = len(rm_followups) if not rm_followups.empty else 0
            st.metric(f"RM {rm_code} - Successful", successful)
        with col3:
            conv_rate = (
                (successful / len(rm_customers) * 100) if len(rm_customers) > 0 else 0
            )
            st.metric(f"RM {rm_code} - Conversion", f"{conv_rate:.1f}%")
        with col4:
            loans = (
                len(rm_followups[rm_followups["product_interest"] == "Loan"])
                if not rm_followups.empty and "product_interest" in rm_followups.columns
                else 0
            )
            st.metric(f"RM {rm_code} - Loans", loans)


def show_call_analytics(customers_df, followups_df):
    """Show call analytics and trends"""

    if customers_df.empty:
        st.info("No customer data available for analytics")
        return

    col1, col2 = st.columns(2)

    with col1:
        if "status" in customers_df.columns:
            # Call Status Distribution
            status_counts = customers_df["status"].value_counts()
            fig1 = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Call Status Distribution",
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No status data available")

    with col2:
        if "business" in customers_df.columns:
            # Business Type Analysis
            business_counts = customers_df["business"].value_counts().head(10)
            fig2 = px.bar(
                x=business_counts.values,
                y=business_counts.index,
                orientation="h",
                title="Top 10 Business Types",
                color=business_counts.values,
                color_continuous_scale="thermal",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No business type data available")

    # Daily Call Trends
    if "create_date" in customers_df.columns:
        st.subheader("📅 Daily Call Trends")
        daily_calls = customers_df.set_index("create_date").resample("D").size()
        fig3 = px.line(
            x=daily_calls.index,
            y=daily_calls.values,
            title="Daily Call Volume",
            labels={"x": "Date", "y": "Number of Calls"},
        )
        st.plotly_chart(fig3, use_container_width=True)


def show_product_analysis(followups_df):
    """Show product interest analysis"""

    if followups_df.empty:
        st.info("No follow-up data available for product analysis")
        return

    col1, col2 = st.columns(2)

    with col1:
        if "product_interest" in followups_df.columns:
            # Product Interest Distribution
            product_counts = followups_df["product_interest"].value_counts()
            fig1 = px.pie(
                values=product_counts.values,
                names=product_counts.index,
                title="Product Interest Distribution",
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No product interest data available")

    with col2:
        if "next_action" in followups_df.columns:
            # Next Action Analysis
            action_counts = followups_df["next_action"].value_counts()
            fig2 = px.bar(
                x=action_counts.values,
                y=action_counts.index,
                orientation="h",
                title="Next Action Distribution",
                color=action_counts.values,
                color_continuous_scale="sunset",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No next action data available")

    # Bank Information Analysis
    if "amount_usd" in followups_df.columns:
        st.subheader("💰 Potential Deal Size")

        # Convert amount to numeric, handling empty strings
        followups_df["amount_numeric"] = pd.to_numeric(
            followups_df["amount_usd"], errors="coerce"
        )
        valid_amounts = followups_df["amount_numeric"].dropna()

        if not valid_amounts.empty:
            total_potential = valid_amounts.sum()
            avg_deal = valid_amounts.mean()
            max_deal = valid_amounts.max()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Potential ($)", f"${total_potential:,.0f}")
            with col2:
                st.metric("Average Deal Size", f"${avg_deal:,.0f}")
            with col3:
                st.metric("Largest Deal", f"${max_deal:,.0f}")
        else:
            st.info("No valid amount data available")


def show_activity_timeline(customers_df, followups_df):
    """Show activity timeline and recent updates"""

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🕒 Recent Activities")

        if not followups_df.empty and "last_updated" in followups_df.columns:
            # Recent followups
            recent_followups = followups_df.nlargest(10, "last_updated")
            display_cols = [
                "customer_name",
                "product_interest",
                "next_action",
                "last_updated",
            ]
            available_cols = [
                col for col in display_cols if col in recent_followups.columns
            ]

            recent_followups = recent_followups[available_cols]

            for _, row in recent_followups.iterrows():
                customer_name = row.get("customer_name", "Unknown")
                product = row.get("product_interest", "N/A")
                action = row.get("next_action", "N/A")
                updated = row.get("last_updated", "Unknown")

                if hasattr(updated, "strftime"):
                    updated_str = updated.strftime("%Y-%m-%d %H:%M")
                else:
                    updated_str = str(updated)

                st.write(f"**{customer_name}** - {product} ({action})")
                st.caption(f"Updated: {updated_str}")
                st.markdown("---")
        else:
            st.info("No recent activities data available")

    with col2:
        st.subheader("📈 Performance Trends")

        if not customers_df.empty and "create_date" in customers_df.columns:
            # Weekly performance trend
            weekly_trend = customers_df.set_index("create_date").resample("W").size()
            fig = px.area(
                x=weekly_trend.index,
                y=weekly_trend.values,
                title="Weekly Call Volume Trend",
                labels={"x": "Week", "y": "Calls"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data available")


# --- Initialize selected filter in session state
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = None


# --- Helper function for clickable metrics
def metric_button(label, value, key, help_text=None):
    button_clicked = st.button(
        f"{label}\n### {value}", key=key, help=help_text, use_container_width=True
    )
    if button_clicked:
        st.session_state.selected_filter = label


# Main app
import base64

with open(
    "Logo-CMCB.png", "rb"
) as f:  # put the PNG file in the same folder as this script
    logo_data = base64.b64encode(f.read()).decode()

import re


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
                        RM {st.session_state.rm_code}
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

    def optimize_customer_data(customers):
        """Pre-process customer data for faster filtering"""
        optimized_customers = []

        for customer in customers:
            # Pre-process RM code and status once
            optimized_customer = customer.copy()
            optimized_customer["_rm_normalized"] = (
                str(customer.get("rm_code", "")).strip().zfill(3)
            )
            optimized_customer["_status"] = customer.get("status", "")
            optimized_customers.append(optimized_customer)
        return optimized_customers

    def get_user_customers_ultra_fast(optimized_customers, rm_code):
        """Ultra-fast filtering with pre-processed data"""
        target_rm = str(rm_code).strip().zfill(3)
        return [
            customer
            for customer in optimized_customers
            if customer["_status"] != "Called"
            and customer["_rm_normalized"] == target_rm
        ]

    def get_called_customers(optimized_customers, rm_code):
        """Get customers with status = 'Called' for specific RM"""
        target_rm = str(rm_code).strip().zfill(3)

        return [
            customer
            for customer in optimized_customers
            if customer["status"] == "Called"
            and customer["_rm_normalized"] == target_rm
        ]

    def get_uncalled_customers(optimized_customers, rm_code):
        """Get customers with status != 'Called' for specific RM"""
        target_rm = str(rm_code).strip().zfill(3)

        return [
            customer
            for customer in optimized_customers
            if customer["status"] != "Called"
            and customer["_rm_normalized"] == target_rm
        ]

    # Add these helper functions if missing
    def get_called_customers_ultra_fast(optimized_customers, rm_code):
        """Get customers that have been called"""
        if not optimized_customers:
            return []

        target_rm = str(rm_code).strip().zfill(3)
        return [
            customer
            for customer in optimized_customers
            if customer.get("_status") == "Called"
            and customer.get("_rm_normalized") == target_rm
        ]

    current_rm = str(st.session_state.rm_code).strip()

    # Usage - call this once when loading data
    if "optimized_customers" not in st.session_state:
        st.session_state.optimized_customers = optimize_customer_data(
            st.session_state.customers
        )
    # Get uncalled customers for display
    user_customers = get_uncalled_customers(
        st.session_state.optimized_customers, current_rm
    )

    # Get called customers for metrics
    called_customers = get_called_customers(
        st.session_state.optimized_customers, current_rm
    )
    current_rm = str(st.session_state.rm_code).strip()
    user_customers = get_user_customers_ultra_fast(
        st.session_state.optimized_customers, current_rm
    )

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
                st.session_state.optimized_customers, current_rm
            )
            called_customers = get_called_customers_ultra_fast(
                st.session_state.optimized_customers, current_rm
            )
        else:
            user_customers = []
            called_customers = []
            # st.sidebar.error("❌ Cannot create user_customers - no optimized data")
        # Precompute all metrics
        total_customers = len(user_customers) + len(called_customers)
        contacted = len(called_customers)
        contact_rate = (contacted / total_customers * 100) if total_customers else 0
        # Compute follow-ups and appointments once
        follow_up_count = 0
        appointment_count = 0
        if not df_followup.empty and "next_action" in df_followup.columns:
            formatted_rm = current_rm.zfill(3)
            follow_up_count = len(
                df_followup[
                    (df_followup["next_action"].str.lower() == "follow up")
                    & (
                        df_followup["rm_code"].apply(lambda x: str(x).strip().zfill(3))
                        == formatted_rm
                    )
                ]
            )
            appointment_count = len(
                df_followup[
                    (df_followup["next_action"].str.lower() == "appointment")
                    & (
                        df_followup["rm_code"].apply(lambda x: str(x).strip().zfill(3))
                        == formatted_rm
                    )
                ]
            )

        with col1:
            display_metric_card("📋 TOTAL", total_customers, "YOUR CUSTOMER LIST")

        with col2:
            display_metric_card("📞 CONTACTED", contacted, f"{contact_rate:.1f}% Rate")

        with col3:
            display_metric_card("📞 PICK UP", contacted, f"{contact_rate:.1f}% Rate")

        with col4:
            display_metric_card("🔄 FOLLOW UP", follow_up_count, "Pending")

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

        with tab1_inner:
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
                                            st.write(
                                                f"🔍 DEBUG: Saving call_status = '{current_call_status}'"
                                            )
                                            followup_data = {
                                                "customer_name": str(row["name"]),
                                                "customer_id": str(row["id"]),
                                                "customer_business": str(
                                                    row["business"]
                                                ),
                                                "customer_phone": str(
                                                    row.get("phone", "")
                                                ),
                                                "rm_code": str(
                                                    st.session_state.rm_code
                                                ),
                                                "call_status": str(current_call_status),
                                                # "call_status": str(
                                                #    st.session_state.status_dict.get(
                                                #        customer_id, ""
                                                #    )
                                                # ),
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
            st.markdown("### 🔄 Follow Up")
            st.info("List of customers with pending follow-ups")
            # Add caching for follow-up data
            # Load data with caching
            df_followup = get_followup_data_cached()
            if not df_followup.empty:
                current_rm = st.session_state.get("rm_code", "")
                if current_rm:
                    formatted_rm = str(current_rm).strip().zfill(3)
                    # Filter for pending follow-ups for this RM
                    follow_up_customers = df_followup[
                        (df_followup["next_action"].str.lower() == "follow up")
                        & (
                            df_followup["rm_code"].apply(
                                lambda x: str(x).strip().zfill(3)
                            )
                            == formatted_rm
                        )
                    ]
                    # Display the data
                    if not follow_up_customers.empty:
                        # st.success(
                        #    f"📊 Found {len(follow_up_customers)} follow-up(s) for your account"
                        # )
                        # Initialize session state for UI toggles
                        for idx, row in follow_up_customers.iterrows():
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            if f"show_new_followup_{row_key}" not in st.session_state:
                                st.session_state[f"show_new_followup_{row_key}"] = False
                            if f"show_appointment_{row_key}" not in st.session_state:
                                st.session_state[f"show_appointment_{row_key}"] = False
                            if f"show_note_{row_key}" not in st.session_state:
                                st.session_state[f"show_note_{row_key}"] = False

                        for idx, row in follow_up_customers.iterrows():
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("followup_date", "N/A")
                            # Add the index to make each row_key unique
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"

                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("followup_date", "N/A")

                            with st.expander(
                                f"📞 {customer_name} - Follow Up: {followup_date}",
                                expanded=False,
                            ):
                                # Compact customer info in columns
                                col_info1, col_info2 = st.columns(2)

                                with col_info1:
                                    st.write(
                                        f"**📞 Phone:** {row.get('customer_phone', 'N/A')}"
                                    )
                                    st.write(
                                        f"**🏢 Business:** {row.get('customer_business', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💰 Product:** {row.get('product_interest', 'N/A')}"
                                    )
                                    # 📝 Add Notes
                                    notes = row.get("notes", "")
                                    if notes:
                                        st.markdown(
                                            f"""
                                            <div style='background-color:#f9f9f9;padding:10px;
                                            border-left:4px solid #2E8B57;border-radius:6px;
                                            margin-top:5px;'>
                                            <strong>📝 Notes:</strong> {notes}
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                    else:
                                        st.markdown(
                                            """
                                            <div style='color:gray;font-style:italic;margin-top:5px;'>
                                            📝 No notes recorded.
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with col_info2:
                                    st.write(
                                        f"**🏦 Bank:** {row.get('bank_name', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💵 Amount:** ${row.get('amount_usd', 'N/A')}"
                                    )
                                    st.write(f"**📅 Follow-up:** {followup_date}")

                                # st.markdown("**📝 Notes:**")
                                # st.markdown(
                                #    f"<div style='background-color:#f9f9f9;padding:10px;border-radius:10px;'>"
                                #    f"{row.get('notes', 'No notes recorded.')}</div>",
                                #    unsafe_allow_html=True,
                                # )

                                # Notes section
                                # In your customer expander, replace the nested expander with:

                                # Action buttons
                                st.markdown("#### Actions")

                                # Use forms for better performance
                                with st.form(key=f"actions_form_{row_key}"):
                                    (
                                        action_col1,
                                        action_col2,
                                        action_col3,
                                    ) = st.columns(3)

                                    with action_col1:
                                        mark_completed = st.form_submit_button(
                                            "✅ Completed",
                                            use_container_width=True,
                                            help="Mark this follow-up as completed",
                                        )

                                    with action_col2:
                                        new_followup = st.form_submit_button(
                                            "🔄 Reschedule",
                                            use_container_width=True,
                                            help="Schedule a new follow-up date",
                                        )

                                    with action_col3:
                                        convert_appointment = st.form_submit_button(
                                            "📅 To Appointment",
                                            use_container_width=True,
                                            help="Convert to appointment",
                                        )

                                    # Handle form submissions
                                    if mark_completed:
                                        if update_followup_status(
                                            row_key, "Completed", "", "", formatted_rm
                                        ):
                                            st.success(
                                                f"✅ Follow-up completed for {customer_name}"
                                            )
                                            st.rerun()

                                    if new_followup:
                                        st.session_state[
                                            f"show_new_followup_{row_key}"
                                        ] = True

                                    if convert_appointment:
                                        st.session_state[
                                            f"show_appointment_{row_key}"
                                        ] = True

                                # Reschedule Follow-up Section
                                if st.session_state[f"show_new_followup_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 🔄 Reschedule Follow-up")

                                    col_date, col_notes = st.columns([1, 2])
                                    with col_date:
                                        new_date = st.date_input(
                                            "New follow-up date:",
                                            key=f"new_date_{row_key}",
                                        )
                                    with col_notes:
                                        new_notes = st.text_area(
                                            "Additional notes:",
                                            key=f"new_notes_{row_key}",
                                        )

                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.button(
                                            "💾 Schedule", key=f"save_new_{row_key}"
                                        ):
                                            if update_followup_reschedule(
                                                row_key,
                                                new_date,
                                                new_notes,
                                                formatted_rm,
                                            ):
                                                st.session_state[
                                                    f"show_new_followup_{row_key}"
                                                ] = False
                                                st.success(
                                                    f"✅ Follow-up rescheduled for {customer_name}"
                                                )
                                                st.rerun()
                                    with col_cancel:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_new_{row_key}"
                                        ):
                                            st.session_state[
                                                f"show_new_followup_{row_key}"
                                            ] = False
                                            st.rerun()

                                # Convert to Appointment Section
                                if st.session_state[f"show_appointment_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 📅 Convert to Appointment")

                                    col_appt_date, col_appt_notes = st.columns([1, 2])
                                    with col_appt_date:
                                        appointment_date = st.date_input(
                                            "Appointment date:",
                                            key=f"appt_date_{row_key}",
                                        )
                                    with col_appt_notes:
                                        appointment_notes = st.text_area(
                                            "Appointment details:",
                                            key=f"appt_notes_{row_key}",
                                        )

                                    col_confirm, col_cancel_appt = st.columns(2)
                                    with col_confirm:
                                        if st.button(
                                            "🎯 Confirm", key=f"confirm_appt_{row_key}"
                                        ):
                                            if convert_to_appointment(
                                                row_key,
                                                appointment_date,
                                                appointment_notes,
                                                formatted_rm,
                                            ):
                                                st.session_state[
                                                    f"show_appointment_{row_key}"
                                                ] = False
                                                st.success(
                                                    f"✅ Converted to appointment for {customer_name}"
                                                )
                                                st.rerun()
                                    with col_cancel_appt:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_appt_{row_key}"
                                        ):
                                            st.session_state[
                                                f"show_appointment_{row_key}"
                                            ] = False
                                            st.rerun()

                                # Add Note Section
                                if st.session_state[f"show_note_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 📝 Add Note")

                                    new_note = st.text_area(
                                        "Add your note:", key=f"note_{row_key}"
                                    )

                                    col_save_note, col_cancel_note = st.columns(2)
                                    with col_save_note:
                                        if st.button(
                                            "💾 Save Note", key=f"save_note_{row_key}"
                                        ):
                                            if new_note.strip():
                                                if add_followup_note(
                                                    row_key, new_note, formatted_rm
                                                ):
                                                    st.session_state[
                                                        f"show_note_{row_key}"
                                                    ] = False
                                                    st.success(
                                                        f"✅ Note added for {customer_name}"
                                                    )
                                                    st.rerun()
                                            else:
                                                st.warning("⚠️ Please enter a note")
                                    with col_cancel_note:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_note_{row_key}"
                                        ):
                                            st.session_state[f"show_note_{row_key}"] = (
                                                False
                                            )
                                            st.rerun()
                    else:
                        st.success("✅ No pending follow-ups found for your account.")
            else:
                st.info("📭 No follow-up data available")

        with tab3_inner:
            st.markdown("### 📅 Appointment")
            st.info("List of customers with appointment")
            # Add caching for follow-up data
            # Load data with caching
            df_followup = get_followup_data_cached()
            if not df_followup.empty and "next_action" in df_followup.columns:
                current_rm = st.session_state.get("rm_code", "")
                if current_rm:
                    formatted_rm = str(current_rm).strip().zfill(3)
                    # Filter for pending follow-ups for this RM
                    follow_up_customers = df_followup[
                        (df_followup["next_action"].str.lower() == "appointment")
                        & (
                            df_followup["rm_code"].apply(
                                lambda x: str(x).strip().zfill(3)
                            )
                            == formatted_rm
                        )
                    ]

                    # Display the data
                    if not follow_up_customers.empty:
                        # Initialize session state for UI toggles
                        for idx, row in follow_up_customers.iterrows():
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            if f"show_new_followup_{row_key}" not in st.session_state:
                                st.session_state[f"show_new_followup_{row_key}"] = False
                            if f"show_appointment_{row_key}" not in st.session_state:
                                st.session_state[f"show_appointment_{row_key}"] = False
                            if f"show_note_{row_key}" not in st.session_state:
                                st.session_state[f"show_note_{row_key}"] = False

                        for idx, row in follow_up_customers.iterrows():
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("appointment_date", "N/A")
                            # Add the index to make each row_key unique
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("appointment_date", "N/A")
                            with st.expander(
                                f"📞 {customer_name} - Appointment: {followup_date}",
                                expanded=False,
                            ):
                                # Compact customer info in columns
                                col_info1, col_info2 = st.columns(2)

                                with col_info1:
                                    st.write(
                                        f"**📞 Phone:** {row.get('customer_phone', 'N/A')}"
                                    )
                                    st.write(
                                        f"**🏢 Business:** {row.get('customer_business', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💰 Product:** {row.get('product_interest', 'N/A')}"
                                    )

                                with col_info2:
                                    st.write(
                                        f"**🏦 Bank:** {row.get('bank_name', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💵 Amount:** ${row.get('amount_usd', 'N/A')}"
                                    )
                                    st.write(f"**📅 Follow-up:** {followup_date}")

                                # Notes section
                                # In your customer expander, replace the nested expander with:

                                # Action buttons
                                st.markdown("---")
                                st.markdown("#### Actions")

                                # Use forms for better performance
                                with st.form(key=f"actions_form_{row_key}"):
                                    (
                                        action_col1,
                                        action_col2,
                                        action_col3,
                                        action_col4,
                                    ) = st.columns(4)

                                    with action_col1:
                                        mark_completed = st.form_submit_button(
                                            "✅ Completed",
                                            use_container_width=True,
                                            help="Mark this follow-up as completed",
                                        )

                                    with action_col2:
                                        new_followup = st.form_submit_button(
                                            "🔄 Reschedule",
                                            use_container_width=True,
                                            help="Schedule a new follow-up date",
                                        )

                                    with action_col3:
                                        convert_appointment = st.form_submit_button(
                                            "📅 To Appointment",
                                            use_container_width=True,
                                            help="Convert to appointment",
                                        )

                                    with action_col4:
                                        add_note = st.form_submit_button(
                                            "📝 Add Note",
                                            use_container_width=True,
                                            help="Add additional notes",
                                        )

                                    # Handle form submissions
                                    if mark_completed:
                                        if update_followup_status(
                                            row_key, "Completed", "", formatted_rm
                                        ):
                                            st.success(
                                                f"✅ Follow-up completed for {customer_name}"
                                            )
                                            st.rerun()

                                    if new_followup:
                                        st.session_state[
                                            f"show_new_followup_{row_key}"
                                        ] = True

                                    if convert_appointment:
                                        st.session_state[
                                            f"show_appointment_{row_key}"
                                        ] = True

                                    if add_note:
                                        st.session_state[f"show_note_{row_key}"] = True

                                # Reschedule Follow-up Section
                                if st.session_state[f"show_new_followup_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 🔄 Reschedule Follow-up")

                                    col_date, col_notes = st.columns([1, 2])
                                    with col_date:
                                        new_date = st.date_input(
                                            "New follow-up date:",
                                            key=f"new_date_{row_key}",
                                        )
                                    with col_notes:
                                        new_notes = st.text_area(
                                            "Additional notes:",
                                            key=f"new_notes_{row_key}",
                                        )

                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.button(
                                            "💾 Schedule", key=f"save_new_{row_key}"
                                        ):
                                            if update_followup_reschedule(
                                                row_key,
                                                new_date,
                                                new_notes,
                                                formatted_rm,
                                            ):
                                                st.session_state[
                                                    f"show_new_followup_{row_key}"
                                                ] = False
                                                st.success(
                                                    f"✅ Follow-up rescheduled for {customer_name}"
                                                )
                                                st.rerun()
                                    with col_cancel:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_new_{row_key}"
                                        ):
                                            st.session_state[
                                                f"show_new_followup_{row_key}"
                                            ] = False
                                            st.rerun()

                                # Convert to Appointment Section
                                if st.session_state[f"show_appointment_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 📅 Convert to Appointment")

                                    col_appt_date, col_appt_notes = st.columns([1, 2])
                                    with col_appt_date:
                                        appointment_date = st.date_input(
                                            "Appointment date:",
                                            key=f"appt_date_{row_key}",
                                        )
                                    with col_appt_notes:
                                        appointment_notes = st.text_area(
                                            "Appointment details:",
                                            key=f"appt_notes_{row_key}",
                                        )

                                    col_confirm, col_cancel_appt = st.columns(2)
                                    with col_confirm:
                                        if st.button(
                                            "🎯 Confirm", key=f"confirm_appt_{row_key}"
                                        ):
                                            if convert_to_appointment(
                                                row_key,
                                                appointment_date,
                                                appointment_notes,
                                                formatted_rm,
                                            ):
                                                st.session_state[
                                                    f"show_appointment_{row_key}"
                                                ] = False
                                                st.success(
                                                    f"✅ Converted to appointment for {customer_name}"
                                                )
                                                st.rerun()
                                    with col_cancel_appt:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_appt_{row_key}"
                                        ):
                                            st.session_state[
                                                f"show_appointment_{row_key}"
                                            ] = False
                                            st.rerun()

                                # Add Note Section
                                if st.session_state[f"show_note_{row_key}"]:
                                    st.markdown("---")
                                    st.markdown("#### 📝 Add Note")

                                    new_note = st.text_area(
                                        "Add your note:", key=f"note_{row_key}"
                                    )

                                    col_save_note, col_cancel_note = st.columns(2)
                                    with col_save_note:
                                        if st.button(
                                            "💾 Save Note", key=f"save_note_{row_key}"
                                        ):
                                            if new_note.strip():
                                                if add_followup_note(
                                                    row_key, new_note, formatted_rm
                                                ):
                                                    st.session_state[
                                                        f"show_note_{row_key}"
                                                    ] = False
                                                    st.success(
                                                        f"✅ Note added for {customer_name}"
                                                    )
                                                    st.rerun()
                                            else:
                                                st.warning("⚠️ Please enter a note")
                                    with col_cancel_note:
                                        if st.button(
                                            "❌ Cancel", key=f"cancel_note_{row_key}"
                                        ):
                                            st.session_state[f"show_note_{row_key}"] = (
                                                False
                                            )
                                            st.rerun()
                    else:
                        st.success("✅ No pending follow-ups found for your account.")
            else:
                st.info("📭 No follow-up data available")

        with tab4_inner:
            st.markdown("📜 Your Historical Called")
            df_followup = get_followup_data_cached()
            if not df_followup.empty and "next_action" in df_followup.columns:
                current_rm = st.session_state.get("rm_code", "")
                if current_rm:
                    formatted_rm = str(current_rm).strip().zfill(3)
                    # Filter for pending follow-ups for this RM
                    follow_up_customers = df_followup[
                        (df_followup["next_action"].str.lower() == "appointment")
                        & (
                            df_followup["rm_code"].apply(
                                lambda x: str(x).strip().zfill(3)
                            )
                            == formatted_rm
                        )
                    ]

                    # Display the data
                    if not follow_up_customers.empty:
                        # Initialize session state for UI toggles
                        for idx, row in follow_up_customers.iterrows():
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            if f"show_new_followup_{row_key}" not in st.session_state:
                                st.session_state[f"show_new_followup_{row_key}"] = False
                            if f"show_appointment_{row_key}" not in st.session_state:
                                st.session_state[f"show_appointment_{row_key}"] = False
                            if f"show_note_{row_key}" not in st.session_state:
                                st.session_state[f"show_note_{row_key}"] = False

                        for idx, row in follow_up_customers.iterrows():
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("appointment_date", "N/A")
                            # Add the index to make each row_key unique
                            row_key = f"{row.get('customer_id')}_{row.get('customer_name')}_{idx}"
                            customer_name = row.get("customer_name", "N/A")
                            followup_date = row.get("appointment_date", "N/A")
                            with st.expander(
                                f"📞 {customer_name} - Appointment: {followup_date}",
                                expanded=False,
                            ):
                                # Compact customer info in columns
                                col_info1, col_info2 = st.columns(2)

                                with col_info1:
                                    st.write(
                                        f"**📞 Phone:** {row.get('customer_phone', 'N/A')}"
                                    )
                                    st.write(
                                        f"**🏢 Business:** {row.get('customer_business', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💰 Product:** {row.get('product_interest', 'N/A')}"
                                    )

                                with col_info2:
                                    st.write(
                                        f"**🏦 Bank:** {row.get('bank_name', 'N/A')}"
                                    )
                                    st.write(
                                        f"**💵 Amount:** ${row.get('amount_usd', 'N/A')}"
                                    )
                                    st.write(f"**📅 Follow-up:** {followup_date}")

                                # Notes section
                                # In your customer expander, replace the nested expander with:

                                # Action buttons
                                st.markdown("---")
                                st.markdown("### Action")

        with tab5_inner:
            st.markdown("### 📞 Add New Customer")
            st.info("Check if the customer exists before adding a new record")

            # Initialize session states
            if "picked_up_state" not in st.session_state:
                st.session_state.picked_up_state = None
            if "not_picked_state" not in st.session_state:
                st.session_state.not_picked_state = None
            if "current_phone_checked" not in st.session_state:
                st.session_state.current_phone_checked = None

            # df = pd.DataFrame(user_customers)
            df = get_followup_data_cached()
            df = pd.DataFrame(df)

            col1, col2 = st.columns([2, 1])
            with col1:
                new_phone = st.text_input(
                    "📱 Enter Customer Phone Number",
                    placeholder="e.g., 012345678",
                    key="new_customer_phone",
                    value="",
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                check_btn = st.button("🔍 Check Customer", use_container_width=True)

            # Handle phone check and display logic separately
            if check_btn and new_phone:
                clean_phone = str(new_phone).strip()
                # Reset states for new phone check
                if clean_phone != st.session_state.get("current_phone_checked"):
                    st.session_state.picked_up_state = None
                    st.session_state.not_picked_state = None
                st.session_state.current_phone_checked = clean_phone
                st.rerun()

            # Always show the appropriate section based on current state
            current_phone = st.session_state.get("current_phone_checked")
            # st.write("🧾 DataFrame Columns:", list(df.columns))

            if current_phone:
                clean_phone = clean_phone_number(current_phone)
                # clean_phone = clean_phone_number(current_phone)

                # st.write("🔍 **Debug — Raw Input Phone:**", current_phone)
                # st.write("🧹 **Debug — Cleaned Input Phone:**", clean_phone)

                # Clean phone column in df before comparing
                df["clean_phone"] = df["customer_phone"].apply(clean_phone_number)

                # Debug few rows from df
                # st.write("📄 **Debug — Sample of Cleaned DF Phones:**")
                # st.dataframe(df[["customer_phone", "clean_phone"]].tail(10))

                # Check if this number exists (exact match)
                # existing_customer = df[df["clean_phone"] == clean_phone].head(1)
                # We have a phone number to check (either from button click or session state)
                clean_phone = str(current_phone).strip()
                df["clean_phone"] = df["customer_phone"].apply(clean_phone_number)
                existing_customer = df[df["clean_phone"] == clean_phone].head(1)

                #
                if not existing_customer.empty:
                    # --- Customer exists ---
                    st.warning("⚠️ Customer already exists in the system.")
                    cust_data = existing_customer.iloc[0]

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(
                            f"**👤 Name:** {cust_data.get('customer_name', 'N/A')}"
                        )
                        st.write(
                            f"**📞 Phone:** {cust_data.get('customer_phone', 'N/A')}"
                        )
                    with col2:
                        st.write(
                            f"**🏢 Business:** {cust_data.get('customer_business', 'N/A')}"
                        )
                        st.write(
                            f"**📊 Call Status:** {cust_data.get('call_status', 'N/A')}"
                        )

                    # Optional: show when last contacted
                    last_followup = cust_data.get("followup_date", "N/A")
                    st.info(f"🗓️ Last follow-up recorded on **{last_followup}**")

                    # Optional — show notes if available
                    notes = cust_data.get("notes", "")
                    if notes:
                        st.markdown(
                            f"<div style='background-color:#f9f9f9;padding:10px;border-left:4px solid #2E8B57;border-radius:6px;margin-top:5px;'>"
                            f"<strong>📝 Notes:</strong> {notes}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='color:gray;font-style:italic;'>No notes recorded yet.</div>",
                            unsafe_allow_html=True,
                        )

                    # 🧭 Instead of call, guide them
                    st.info(
                        "ℹ️ This customer is already registered in the Follow-Up sheet."
                    )

                ##
                else:
                    # --- Customer does not exist ---
                    st.success("✅ Phone number not found in system.")

                    # Show pick up buttons if no state chosen yet
                    if st.session_state.get("picked_up_state") is None:
                        st.info("📞 Was the customer pick up the call?")
                        col_yes, col_no = st.columns(2)

                        # --- Picked Up ---
                        with col_yes:
                            if st.button(
                                "✅ Yes - Picked Up",
                                key="picked_yes",
                                use_container_width=True,
                            ):
                                st.session_state.picked_up_state = True
                                st.rerun()

                        # --- Not Picked Up ---
                        with col_no:
                            if st.button(
                                "❌ No - Not Picked Up",
                                key="picked_no",
                                use_container_width=True,
                            ):
                                st.session_state.not_picked_state = True

                                # Save "Not Picked Up" immediately
                                followup_data = {
                                    "customer_name": "Unknown - Not Picked Up",
                                    "customer_phone": clean_phone,
                                    "rm_code": st.session_state.get("rm_code", "N/A"),
                                    "call_status": "Not Picked Up",
                                    "product_interest": "",
                                    "bank_name": "",
                                    "amount_usd": "",
                                    "next_action": "Call Back",
                                    "followup_date": datetime.now().strftime(
                                        "%Y-%m-%d"
                                    ),
                                    "call_notes": "Customer did not pick up the call",
                                    "status": "Not Picked Up",
                                    "appointment_date": "",
                                }

                                success = save_followup_to_google_sheets(followup_data)
                                if success:
                                    st.success(
                                        "✅ 'Not Picked Up' logged to FollowUp sheet!"
                                    )
                                    st.session_state.not_picked_state = False
                                    st.session_state.current_phone_checked = None
                                    st.rerun()

                    # --- Show new customer form if picked up ---
                    elif st.session_state.get("picked_up_state"):
                        st.markdown("---")
                        st.markdown("#### 📝 Please enter new customer details:")

                        with st.form("new_customer_form"):
                            col1, col2 = st.columns(2)

                            with col1:
                                new_name = st.text_input(
                                    "Full Name *",
                                    placeholder="Enter customer full name",
                                )
                                new_business = st.text_input(
                                    "Business Type *",
                                    placeholder="e.g., Drink Shop, Retail",
                                )
                                new_industry = st.text_input(
                                    "Source *",
                                    placeholder="e.g., Social Media, RBM, Referral...",
                                )

                            with col2:
                                st.text_input(
                                    "Phone Number *", value=clean_phone, disabled=True
                                )
                                new_bank = st.text_input(
                                    "Current Bank",
                                    placeholder="Bank they currently use",
                                )
                                new_amount = st.number_input(
                                    "Loan Amount (USD)", min_value=0, value=0
                                )

                            col3, col4 = st.columns(2)
                            with col3:
                                new_loan_type = st.selectbox(
                                    "Product Type",
                                    ["Loan", "TD", "Card", "Other"],
                                )
                            with col4:
                                new_interest = st.radio(
                                    "Interest Level",
                                    ["L", "M", "H"],
                                    index=1,
                                    horizontal=True,
                                )

                            new_notes = st.text_area(
                                "Notes",
                                placeholder="Additional notes about the call...",
                            )

                            submitted = st.form_submit_button(
                                "💾 Save to FollowUp Sheet", use_container_width=True
                            )

                            if submitted:
                                if not new_name or not new_business:
                                    st.error(
                                        "❌ Please fill in all required fields (Name and Business)"
                                    )
                                else:
                                    followup_data = {
                                        "customer_name": new_name,
                                        "customer_phone": clean_phone,
                                        "customer_business": new_business,
                                        "rm_code": st.session_state.get(
                                            "rm_code", "N/A"
                                        ),
                                        "call_status": "Picked Up",  # ✅ Added
                                        "source": new_industry,
                                        "product_interest": new_loan_type,
                                        "bank_name": new_bank,
                                        "amount_usd": new_amount,
                                        "interest": new_interest,
                                        "next_action": "Follow Up",
                                        "followup_date": datetime.now().strftime(
                                            "%Y-%m-%d"
                                        ),
                                        "call_notes": new_notes,
                                        "appointment_date": "",
                                    }

                                    success = save_followup_to_google_sheets(
                                        followup_data
                                    )
                                    if success:
                                        st.success(
                                            f"✅ New customer '{new_name}' saved to FollowUp sheet!"
                                        )
                                        st.balloons()
                                        st.session_state.picked_up_state = None
                                        st.session_state.current_phone_checked = None
                                        st.rerun()
            elif check_btn and not new_phone:
                st.warning("⚠️ Please enter a phone number to check.")

            # Add a reset button
            if st.session_state.get("current_phone_checked") or st.session_state.get(
                "picked_up_state"
            ):
                if st.button("🔄 Start Over", use_container_width=True):
                    st.session_state.picked_up_state = None
                    st.session_state.not_picked_state = None
                    st.session_state.current_phone_checked = None
                    st.rerun()

    with tab2:
        st.title("📊 Performance Dashboard")
        df = get_followup_data_cached()
        customer_df = load_customers_from_sheet_cached()
        customer_df = pd.DataFrame(customer_df)
        #df["rm_code"] = df["rm_code"].astype(str).str.strip().str.lstrip("'")
        #customer_df["rm_code"] = customer_df["rm_code"].astype(str).str.strip()

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
                st.metric("📊 Total Calls", f"{total_calls:,}")
            with col2:
                st.metric("📞 Picked Up", f"{picked_up:,}")
            with col3:
                st.metric("🔄 Follow Up", f"{follow_ups:,}")
            with col4:
                st.metric("📅 Appointment", f"{appointments:,}")
            with col5:
                st.metric("✅ Closed Deal", f"{closed_deals:,}")

            st.markdown("---")
            # --- Funnel Chart ---
            # --- Next Action Bar Chart ---
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
                color_discrete_sequence=px.colors.sequential.Greens[::-2],
                title="📞 Next Action Distribution",
            )

            status_counts = df["call_status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_status = px.pie(
                status_counts,
                names="Status",
                values="Count",
                title="📊 Call Status Distribution",
                color_discrete_sequence=px.colors.sequential.Greens[::-2],
            )
            fig_status.update_traces(
                textinfo="percent+label", pull=[0.05] * len(status_counts)
            )

            # follow_up_counts = (
            #    df["status_followup"].fillna("None").value_counts().reset_index()
            # )
            # --- Follow-up Status Bar Chart ---
            follow_up_counts = (
                df["status_followup"].fillna("None").value_counts().reset_index()
            )
            follow_up_counts.columns = ["Follow Up Status", "Count"]  # rename correctly

            fig_followup = px.bar(
                follow_up_counts,
                x="Follow Up Status",
                y="Count",
                text="Count",
                color="Follow Up Status",
                color_discrete_sequence=px.colors.sequential.Greens[
                    ::-1
                ],  # reversed dark green
                title="📊 Follow-up Status Distribution",
            )
            # st.write(customer_df.columns)
            df['rm_code'] = df['rm_code'].astype(str).str.strip().str.lstrip("'")
            rm_summary = (
                df.groupby("rm_code")
                .agg(
                    total_calls=("customer_id", "count"),
                    appointments=(
                        "next_action",
                        lambda x: (
                            x.str.contains("appointment", case=False, na=False)
                        ).sum(),
                    ),
                )
                .reset_index()
            )
            rm_summary['rm_code'] = rm_summary['rm_code'].astype(str).str.strip().str.lstrip("'")

            customer_df["rm_code"] = (
                customer_df["rm_code"].astype(str).str.strip().str.lstrip("'")
            )
            

            # Now merge - both columns are strings
            rm_summary = rm_summary.merge(
                customer_df[["rm_code", "sale_name"]].drop_duplicates(),
                on="rm_code",
                how="left",
            )

            # --- Display RM table (optional) ---
            # st.dataframe(rm_summary)

            # --- Smart grouped bar chart ---
            fig_rm = px.bar(
                rm_summary,
                x="sale_name",  # RM name
                y=["total_calls", "appointments"],
                barmode="group",
                text_auto=True,
                color_discrete_sequence=["#145214", "#71c671"],  # dark & light green
                title="📊 Total Calls and Appointments by RM",
            )
            # --- Display side by side ---
            st.markdown("## Call Insights")
            col_chart1, col_chart2 = st.columns(2)
            col_chart3, col_chart4 = st.columns(2)

            with col_chart1:
                st.plotly_chart(fig_action, use_container_width=True)

            with col_chart2:
                st.plotly_chart(fig_status, use_container_width=True)

            with col_chart3:
                st.plotly_chart(fig_followup, use_container_width=True)

            with col_chart4:
                st.plotly_chart(fig_rm, use_container_width=True)
            # --- Optional: Top 5 Follow-ups or Appointments ---
            #top_customers = df[
            #    df["next_action"].str.contains(
            #        "follow|appointment", case=False, na=False
            #    )
            #]
            #top_customers_count = (
            #    top_customers["customer_name"].value_counts().head(5).reset_index()
            #)
            #top_customers_count.columns = ["Customer", "Count"]

            #st.markdown("## 🏆 Top 5 Customers for Follow-ups / Appointments")
            #st.table(top_customers_count)


# Main app logic
if not st.session_state.logged_in:
    login_form()
else:
    main_app()
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
