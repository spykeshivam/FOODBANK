"""
Login page — mirrors the Flask /login, /check_user, /log_login, /update_postcode flow.

Flow:
  1. User enters their Username and clicks "Check".
  2. If found: show details + "Login" button (or "Update Postcode" if postcode invalid).
  3. Clicking "Login" calls append_login and shows success/error.
  4. Clicking "Update Postcode" navigates to page 4.
"""
import streamlit as st
from services import data_service

st.set_page_config(page_title="Login", page_icon="🔑", layout="centered")
st.title("Check User Details")

if st.button("← Home"):
    st.switch_page("streamlit_app.py")

# ── session state initialisation ──────────────────────────────────────────────
for key in ("checked_user", "user_data", "login_done"):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Step 1: username input ────────────────────────────────────────────────────
with st.form("check_form"):
    user_id = st.text_input("Enter Username")
    submitted = st.form_submit_button("Check")

if submitted:
    uid = user_id.strip()
    if not uid:
        st.error("No ID provided.")
    else:
        try:
            result = data_service.get_user_details(uid)
            st.session_state.checked_user = uid
            st.session_state.user_data = result
            st.session_state.login_done = False
        except Exception as exc:
            st.error(f"Server Error: {exc}")

# ── Step 2: show result ───────────────────────────────────────────────────────
data = st.session_state.user_data

if data is not None:
    if not data["exists"]:
        st.error(data["message"])
    else:
        st.success(data["message"])
        details = data.get("details", {})
        st.markdown(f"**First Name:** {details.get('First Name', '')}")
        st.markdown(f"**Last Name:** {details.get('Last Name', '')}")
        st.markdown(f"**Date of Birth:** {details.get('Date of Birth', '')}")
        st.markdown(f"**Number of Adults in Household:** {details.get('Number of Adults in Household', '')}")
        st.markdown(f"**Number of Children in Household:** {details.get('Number of Children in Household', '')}")
        st.markdown(f"**Last Login Date:** {details.get('Last Login Date', '')}")

        if st.session_state.login_done:
            st.info("Login recorded. You may check another user.")
        else:
            if not data.get("postcode_valid", True):
                st.warning(
                    "The postcode on your account is missing or invalid. "
                    "Please update it before logging in."
                )
                if st.button("Update Postcode"):
                    st.session_state.update_postcode_user = st.session_state.checked_user
                    st.switch_page("pages/4_Update_Postcode.py")
            else:
                if st.button("Login"):
                    uid = st.session_state.checked_user
                    success, message = data_service.append_login(uid)
                    if success:
                        st.success(message)
                        st.session_state.login_done = True
                        st.session_state.user_data = None
                        st.session_state.checked_user = None
                        st.rerun()
                    else:
                        st.error(message)
