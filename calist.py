import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import time
import csv
import os

# Page config
st.set_page_config(page_title="Sales Call System", layout="wide", page_icon="📞")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
        text-align: center;
    }
    .call-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
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
        margin: 5px;
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
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'customers' not in st.session_state:
    st.session_state.customers = []
if 'call_log' not in st.session_state:
    st.session_state.call_log = []
if 'selected_customer' not in st.session_state:
    st.session_state.selected_customer = None
if 'view_customer_history' not in st.session_state:
    st.session_state.view_customer_history = None

# File paths

# Get the folder where your main.py is
BASE_DIR = os.path.dirname(__file__)

# Relative path to the logo
LOGO_PATH = os.path.join(BASE_DIR, "Logo-CMCB.png") 
CUSTOMERS_FILE = os.path.join(BASE_DIR, "sample_customers.csv")
CALL_LOG_FILE = os.path.join(BASE_DIR, "call_log.csv")

# Load data from CSV files
def load_data():
    """Load customer data and call log"""
    try:
        # Load customers
        st.session_state.customers = pd.read_csv(CUSTOMERS_FILE).to_dict('records')
        
        # Ensure required fields exist
        for customer in st.session_state.customers:
            if 'rm_code' not in customer:
                customer['rm_code'] = "001"
            if 'call_count' not in customer:
                customer['call_count'] = 0
            if 'last_contact' not in customer:
                customer['last_contact'] = datetime.now().strftime("%Y-%m-%d")
    except Exception as e:
        st.error(f"Error loading customer data: {e}")
        # Fallback sample data
        st.session_state.customers = [
            {"id": 1, "name": "Sok Dara", "business": "Sok Dara Grocery", "phone": "010 123 456", 
             "email": "sokdara@email.com", "potential": "H", "status": "New Lead", 
             "last_contact": "2023-01-15", "call_count": 0, "rm_code": "001"},
            {"id": 2, "name": "Lim Srey", "business": "Srey Fashion", "phone": "011 234 567", 
             "email": "limsrey@email.com", "potential": "M", "status": "Pending", 
             "last_contact": "2023-02-20", "call_count": 2, "rm_code": "001"},
            {"id": 3, "name": "Chen Lao", "business": "Lao Construction", "phone": "012 345 678", 
             "email": "chenlao@email.com", "potential": "L", "status": "Completed", 
             "last_contact": "2023-03-10", "call_count": 1, "rm_code": "001"},
        ]
    if os.path.exists(CALL_LOG_FILE) and os.path.getsize(CALL_LOG_FILE) > 0:
        try:
        # Specify column names if CSV has no header
            columns = ["rm_code", "customer_name", "call_date", "call_count", "notes"]  # adjust to your actual columns
            st.session_state.call_log = pd.read_csv(CALL_LOG_FILE, names=columns).to_dict('records')
        except Exception as e:
            st.error(f"Error reading call log: {e}")
            st.session_state.call_log = []
    else:
        st.session_state.call_log = []
        save_call_log()
# Save data to CSV files
def save_call_log():
    df = pd.DataFrame(st.session_state.call_log)
    df.to_csv(CALL_LOG_FILE, index=False)

# User authentication
def authenticate_user(username, rm_code):
    # In a real application, you'd check against a database
    # For demo purposes, we'll accept any username with RMCODE:001
    return rm_code == "001"

# Login form
def login_form():
    st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #2E8B57 0%, #3CB371 100%);
        }
        .login-card h2 {
            margin-top: 10px;
            color: #2E8B57;
        }
        .stTextInput>div>div>input {
            padding-left: 35px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Login box
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    # ---- Bank Logo ----
    st.image(
        LOGO_PATH,
        width=160,
        output_format="PNG"
    )

    st.markdown("<h2>Sales Call System</h2>", unsafe_allow_html=True)
    st.write("Welcome! Please log in with your **RM Code** to continue.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("👤 Username")
        rm_code = st.text_input("🔑 RM Code", type="password")
        submitted = st.form_submit_button("Login 🚀")
        if submitted:
            if authenticate_user(username, rm_code):
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.session_state.rm_code = rm_code
                load_data()
                st.rerun()
            else:
                st.error("❌ Invalid credentials, please try again.")
    st.markdown("</div>", unsafe_allow_html=True)
# Main app
def main_app():
    # Header with logo
    col1, col2 = st.columns([1, 3])
    with col1:
        try:
            st.image(LOGO_PATH, width=150)
        except:
            st.markdown("""
            <div style="text-align: center; padding: 20px; background: #f0f0f0; border-radius: 10px;">
                <h2>🏦 CMCB</h2>
                <p>Chip Mong Commercial Bank</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>RM Code: <strong>{st.session_state.rm_code}</strong></p>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="main-header">
            <h1>📞 Sales Call Management System</h1>
            <p>Efficient customer outreach and follow-up platform</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Filter customers by RM code
    user_customers = [c for c in st.session_state.customers if c.get('rm_code') == st.session_state.rm_code]
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📋 Customer List", "📞 Make Calls", "📊 Performance"])

    with tab1:
        st.markdown("""
        <div class="call-card">
            <h2>👥 Customer Relationship Management</h2>
            <p>Manage customer contacts, track call history, and add new customers</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create tabs for different functionalities
        cust_tab1, cust_tab2, cust_tab3 = st.tabs(["📋 Customer Directory", "📞 Call History Lookup", "➕ Add New Customer"])
        
        with cust_tab1:
            st.markdown("### 🔍 Search & Filter Customers")
            
            # Search and filter
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                search_term = st.text_input("Search by name or business", key="search_main")
            with col2:
                status_filter = st.selectbox("Filter by status", ["All", "Pending", "Completed", "Missed", "New Lead"], key="status_filter")
            with col3:
                potential_filter = st.selectbox("Filter by potential", ["All", "H (High)", "M (Medium)", "L (Low)"], key="potential_filter")
            with col4:
                sort_by = st.selectbox("Sort by", ["Name", "Last Contact", "Potential", "Status"], key="sort_by")
            
            # Filter customers
            filtered_customers = user_customers.copy()
            if search_term:
                filtered_customers = [c for c in filtered_customers if search_term.lower() in str(c.get('name', '')).lower() or search_term.lower() in str(c.get('business', '')).lower()]
            if status_filter != "All":
                filtered_customers = [c for c in filtered_customers if c.get('status') == status_filter]
            if potential_filter != "All":
                potential_value = potential_filter[0]  # Get H, M, or L
                filtered_customers = [c for c in filtered_customers if c.get('potential') == potential_value]
            
            # Sort customers
            if sort_by == "Name":
                filtered_customers.sort(key=lambda x: x.get('name', ''))
            elif sort_by == "Last Contact":
                filtered_customers.sort(key=lambda x: x.get('last_contact', ''), reverse=True)
            elif sort_by == "Potential":
                potential_order = {"H": 1, "M": 2, "L": 3}
                filtered_customers.sort(key=lambda x: potential_order.get(x.get('potential', ''), 4))
            elif sort_by == "Status":
                status_order = {"New Lead": 1, "Pending": 2, "Completed": 3, "Missed": 4}
                filtered_customers.sort(key=lambda x: status_order.get(x.get('status', ''), 5))
            
            # Display customers
            st.subheader(f"📋 Customers ({len(filtered_customers)})")
            
            if not filtered_customers:
                st.info("No customers match your search criteria.")
            
            for customer in filtered_customers:
                with st.container():
                    st.markdown("---")
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{customer.get('name', 'N/A')}**")
                        st.markdown(f"*{customer.get('business', 'N/A')}*")
                        st.markdown(f"📞 {customer.get('phone', 'N/A')}")
                        if 'email' in customer:
                            st.markdown(f"📧 {customer.get('email', 'N/A')}")
                    
                    with col2:
                        # Potential badge
                        potential = customer.get('potential', '')
                        potential_color = {"H": "red", "M": "orange", "L": "green"}.get(potential, "black")
                        st.markdown(f"<span style='color: {potential_color}; font-weight: bold;'>Potential: {potential}</span>", 
                                   unsafe_allow_html=True)
                        st.markdown(f"Last contact: {customer.get('last_contact', 'N/A')}")
                        
                        # Call count if available
                        if 'call_count' in customer:
                            st.markdown(f"Calls: {customer.get('call_count', 0)}")
                    
                    with col3:
                        # Status badge
                        status = customer.get('status', '')
                        status_class = f"status-{status.lower().replace(' ', '-')}" if status else "status-pending"
                        st.markdown(f"<span class='{status_class}'>{status}</span>", 
                                   unsafe_allow_html=True)
                    
                    with col4:
                        if st.button("📞 Call", key=f"call_{customer.get('id', '')}"):
                            st.session_state.selected_customer = customer
                            st.rerun()
                    
                    with col5:
                        if st.button("📋 History", key=f"history_{customer.get('id', '')}"):
                            st.session_state.view_customer_history = customer
                            st.rerun()

        with cust_tab2:
            st.markdown("### 📞 Call History Lookup")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                phone_search = st.text_input("Enter customer phone number", placeholder="e.g., 010 123 456")
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                search_btn = st.button("🔍 Search History", use_container_width=True)
            
            if phone_search or (st.session_state.get('view_customer_history') and cust_tab2):
                # Determine which customer to show
                if st.session_state.get('view_customer_history'):
                    customer = st.session_state.view_customer_history
                    phone_search = customer.get('phone', '')
                else:
                    # Find customer by phone
                    customer = next((c for c in user_customers if c.get('phone') == phone_search), None)
                
                if customer:
                    st.success(f"Found customer: {customer.get('name', 'N/A')}")
                    
                    # Display customer info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Name:** {customer.get('name', 'N/A')}")
                        st.markdown(f"**Business:** {customer.get('business', 'N/A')}")
                        st.markdown(f"**Phone:** {customer.get('phone', 'N/A')}")
                    
                    with col2:
                        potential = customer.get('potential', '')
                        potential_color = {"H": "red", "M": "orange", "L": "green"}.get(potential, "black")
                        st.markdown(f"**Potential:** <span style='color: {potential_color};'>{potential}</span>", 
                                   unsafe_allow_html=True)
                        st.markdown(f"**Status:** {customer.get('status', 'N/A')}")
                        st.markdown(f"**Last Contact:** {customer.get('last_contact', 'N/A')}")

                    # Display call history
                    st.subheader("📋 Call History")
                    
                    # Filter call log for this customer
                    customer_name = customer.get('name', '')
                    customer_calls = [call for call in st.session_state.call_log if call.get('customer') == customer_name]
                    
                    if customer_calls:
                        for call in reversed(customer_calls):  # Show most recent first
                            st.markdown(f"""
                            <div class="customer-card">
                                <strong>{call.get('date', '')}</strong> - 
                                <span class="status-{call.get('outcome', '').lower()}">{call.get('outcome', '')}</span><br>
                                <em>{call.get('notes', 'No notes')}</em>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No call history found for this customer.")
                    
                    # Add new call entry
                    st.subheader("📝 Log New Call")
                    with st.form(key=f"log_call_form_{customer.get('id', '')}"):
                        call_notes = st.text_area("Call Notes", placeholder="Enter details about the conversation...")
                        call_outcome = st.radio("Call Outcome", ["Completed", "Missed", "Callback", "Not Interested"])
                        
                        if st.form_submit_button("💾 Save Call Log"):
                            # Log the call
                            call_entry = {
                                "customer": customer.get('name', ''),
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "outcome": call_outcome,
                                "notes": call_notes
                            }
                            st.session_state.call_log.append(call_entry)
                            save_call_log()
                            
                            # Update customer status and last contact
                            for i, c in enumerate(st.session_state.customers):
                                if c.get('id') == customer.get('id'):
                                    st.session_state.customers[i]['status'] = call_outcome
                                    st.session_state.customers[i]['last_contact'] = datetime.now().strftime("%Y-%m-%d")
                                    if 'call_count' in st.session_state.customers[i]:
                                        st.session_state.customers[i]['call_count'] += 1
                                    else:
                                        st.session_state.customers[i]['call_count'] = 1
                                    break
                            
                            st.success("Call logged successfully!")
                            time.sleep(1)
                            st.rerun()
                    
                else:
                    st.warning("No customer found with that phone number.")
            else:
                st.info("Enter a phone number to search for call history")
        
        with cust_tab3:
            st.markdown("### ➕ Add New Customer")
            
            with st.form(key="add_customer_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Basic Information")
                    new_name = st.text_input("Full Name*", placeholder="e.g., Sok Dara")
                    new_business = st.text_input("Business Name*", placeholder="e.g., Sok Dara Grocery")
                    new_phone = st.text_input("Phone Number*", placeholder="e.g., 010 123 456")
                    new_email = st.text_input("Email", placeholder="e.g., sokdara@email.com")
                
                with col2:
                    st.subheader("Additional Details")
                    new_potential = st.selectbox("Potential Level*", ["H", "M", "L"])
                    new_status = st.selectbox("Status*", ["New Lead", "Pending", "Completed", "Missed"])
                    new_address = st.text_area("Address", placeholder="Full address")
                    new_notes = st.text_area("Notes", placeholder="Any additional notes")
                
                submitted = st.form_submit_button("Save Customer")

            if submitted:
                if not all([new_name, new_business, new_phone, new_potential, new_status]):
                    st.error("Please fill all required fields.")
                else:
                    # Create new customer
                    new_id = max([c.get('id', 0) for c in st.session_state.customers], default=0) + 1
                    new_customer = {
                        "id": new_id,
                        "name": new_name,
                        "business": new_business,
                        "phone": new_phone,
                        "email": new_email,
                        "potential": new_potential,
                        "status": new_status,
                        "last_contact": datetime.now().strftime("%Y-%m-%d"),
                        "call_count": 0,
                        "rm_code": st.session_state.rm_code
                    }
                    
                    st.session_state.customers.append(new_customer)
                    st.success("✅ Customer added successfully!")

    with tab2:
        st.markdown("""
        <div class="call-card">
            <h2>📞 Make Calls</h2>
            <p>Connect with customers and log your interactions</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.selected_customer:
            customer = st.session_state.selected_customer
            st.markdown(f"### Calling: {customer.get('name', 'N/A')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Business:** {customer.get('business', 'N/A')}")
                st.markdown(f"**Phone:** 📞 {customer.get('phone', 'N/A')}")
                potential = customer.get('potential', '')
                potential_color = "red" if potential == 'H' else "orange" if potential == 'M' else "green"
                st.markdown(f"**Potential:** <span style='color: {potential_color};'>{potential}</span>", 
                           unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**Last Contact:** {customer.get('last_contact', 'N/A')}")
                status = customer.get('status', '')
                st.markdown(f"**Status:** <span class='status-{status.lower()}'>{status}</span>", 
                           unsafe_allow_html=True)
            
            # Call notes
            call_notes = st.text_area("Call Notes", placeholder="Enter details about the conversation...")
            
            # Call outcome
            outcome = st.radio("Call Outcome", ["Completed", "Missed", "Callback"])
            
            # Call actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📞 Start Call", use_container_width=True):
                    with st.spinner("Calling..."):
                        time.sleep(2)  # Simulate call
                        st.success(f"Connected to {customer.get('name', 'N/A')}")
            
            with col2:
                if st.button("✅ Log Call", use_container_width=True):
                    # Log the call
                    call_entry = {
                        "customer": customer.get('name', ''),
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "outcome": outcome,
                        "notes": call_notes
                    }
                    st.session_state.call_log.append(call_entry)
                    save_call_log()
                    
                    # Update customer status
                    for i, c in enumerate(st.session_state.customers):
                        if c.get('id') == customer.get('id'):
                            st.session_state.customers[i]['status'] = outcome
                            st.session_state.customers[i]['last_contact'] = datetime.now().strftime("%Y-%m-%d")
                            if 'call_count' in st.session_state.customers[i]:
                                st.session_state.customers[i]['call_count'] += 1
                            else:
                                st.session_state.customers[i]['call_count'] = 1
                            break
                    
                    st.success("Call logged successfully!")
                    time.sleep(1)
                    st.session_state.selected_customer = None
                    st.rerun()
            
            with col3:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.selected_customer = None
                    st.rerun()
        
        else:
            st.info("Select a customer from the Customer List tab to make a call")

    with tab3:
        st.markdown("""
        <div class="call-card">
            <h2>📊 Performance Dashboard</h2>
            <p>Track your calling performance and metrics</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate metrics
        total_customers = len(user_customers)
        completed_calls = len([c for c in user_customers if c.get('status') == 'Completed'])
        pending_calls = len([c for c in user_customers if c.get('status') == 'Pending'])
        missed_calls = len([c for c in user_customers if c.get('status') == 'Missed'])
        
        high_potential = len([c for c in user_customers if c.get('potential') == 'H'])
        medium_potential = len([c for c in user_customers if c.get('potential') == 'M'])
        low_potential = len([c for c in user_customers if c.get('potential') == 'L'])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{total_customers}</h3>
                <p>Total Customers</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{completed_calls}</h3>
                <p>Completed Calls</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{pending_calls}</h3>
                <p>Pending Calls</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{missed_calls}</h3>
                <p>Missed Calls</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Potential metrics
        st.subheader("Potential Distribution")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: red;">{high_potential}</h3>
                <p>High Potential</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: orange;">{medium_potential}</h3>
                <p>Medium Potential</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: green;">{low_potential}</h3>
                <p>Low Potential</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Call log
        st.subheader("Recent Call Log")
        user_call_log = [call for call in st.session_state.call_log 
                         if any(c.get('name') == call.get('customer') and c.get('rm_code') == st.session_state.rm_code 
                                for c in st.session_state.customers)]
        
        if user_call_log:
            for log in reversed(user_call_log[-5:]):  # Show last 5 calls
                st.markdown(f"""
                <div class="customer-card">
                    <strong>{log.get('customer', '')}</strong> - {log.get('date', '')} 
                    <span class="status-{log.get('outcome', '').lower()}">({log.get('outcome', '')})</span><br>
                    <em>{log.get('notes', 'No notes')}</em>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No calls logged yet. Start making calls to see your activity here.")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #6c757d; margin-top: 30px;'>"
        "Sales Call System • CMCB Bank • "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        "</div>",
        unsafe_allow_html=True
    )

# Main app logic
if not st.session_state.logged_in:
    login_form()
else:
    main_app()
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
