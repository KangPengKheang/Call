b1, b2 = st.columns(2)

with b1:
    st.markdown('<div id="save-btn-anchor"></div>', unsafe_allow_html=True)
    if st.button("Save", use_container_width=True, disabled=save_disabled):
        if duplicate_found:
            st.error("This phone number already exists. Saving is blocked.")
        elif not form_ready:
            st.error("Please complete Phone Number, Full Name, and Call Purpose")
        else:
            with st.spinner("Saving call log..."):
                if save_new_call_to_sheet(df_all):
                    st.toast("Call saved successfully")
                    st.rerun()

with b2:
    st.markdown('<div id="save-new-btn-anchor"></div>', unsafe_allow_html=True)
    if st.button("Save & New", use_container_width=True, disabled=save_disabled):
        if duplicate_found:
            st.error("This phone number already exists. Saving is blocked.")
        elif not form_ready:
            st.error("Please complete Phone Number, Full Name, and Call Purpose")
        else:
            with st.spinner("Saving and preparing a new form..."):
                if save_new_call_to_sheet(df_all):
                    queue_form_reset()
                    st.toast("Call saved successfully")
                    st.rerun()
