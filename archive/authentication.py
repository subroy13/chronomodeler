import streamlit as st
from functools import wraps
from typing import Enum


# ============================================================
#       Some dependency functions for handling authorization
# ============================================================
UserAuthLevel = {
    "PUBLIC": 0,
    "PRIVATE": 1,
    "DEVELOPER": 2,
    "ADMIN": 3,
    "SUPERADMIN": 4
}


def auth_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    return st.session_state


# Easy inteceptor for auth
def requires_auth(auth_level = UserAuthLevel["PUBLIC"]):

    def requires_auth_level(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if auth_state().user is not None:
                # verify auth level
                logg_user = auth_state().user

                if logg_user['level'] >= auth_level:
                    with st.sidebar:
                        st.success(f"Welcome {logg_user['username']}!")
                        logout_btn = st.button('Logout', type = "primary")

                        # remove from session state
                        if logout_btn:
                            auth_state().user = None
                            st.experimental_rerun()

                    return fn(*args, **kwargs)
                else:
                    with st.sidebar:
                        st.error(f"You do not have privilege to view this page")
                        st.success(f"Welcome {logg_user['username']}!")
                        logout_btn = st.button('Logout', type = "primary")

                        # remove from session state
                        if logout_btn:
                            auth_state().user = None
                            st.experimental_rerun()
            else:
                # show not login page
                with st.sidebar:
                    st.warning('Not Authenticated')
                    st.markdown(':orange[Please login to continue]')

                    # show login form
                    username = st.text_input('Username')
                    password = st.text_input('Password', type="password")
                    login_btn = st.button('Login', type="primary")

                    # add to the session state
                    if login_btn and username != "" and password != "":

                        # based on the auth_level, collect all username password combinations
                        creds = []
                        for key in UserAuthLevel:
                            if ('USER_' + key) in st.secrets and UserAuthLevel[key] <= auth_level:
                                creds.append((
                                    st.secrets['USER_' + key].get("username"), 
                                    st.secrets['USER_' + key].get("password"),
                                    key
                                ))

                        cred_match = False                        
                        for uname, pwd, key in creds:
                            if uname == username and password == pwd:
                                cred_match = True
                                auth_state().user = {
                                    'username': username,
                                    'level': UserAuthLevel[key]
                                }
                                st.experimental_rerun()
                        if not cred_match:
                            st.markdown(':red[Invalid username or password]')
            
        return wrapper

    return requires_auth_level