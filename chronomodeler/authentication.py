import streamlit as st
from functools import wraps
from typing import Union
import bcrypt

from .models import UserAuthLevel, User


# ============================================================
#       Some dependency functions for handling authorization
# ============================================================
def auth_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    return st.session_state


def get_auth_user() -> Union[None, User]:
    user = auth_state().user
    return user

def get_auth_userid() -> Union[None, str]:
    user = auth_state().user
    return user.get('userid') if user is not None else None


def get_auth_userlevel() -> Union[None, int]:
    user = auth_state().user
    return user.get('level') if user is not None else None

def get_auth_username() -> Union[None, str]:
    user = auth_state().user
    return user.get('username') if user is not None else None


# Easy inteceptor for auth
def requires_auth(auth_level = UserAuthLevel.PUBLIC):

    def requires_auth_level(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if auth_state().user is not None:
                # verify auth level
                logg_user = auth_state().user

                if logg_user['level'] >= auth_level.value:
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
                # show login page
                with st.sidebar:
                    st.warning('Not Authenticated')
                    st.markdown(':orange[Please login to continue]')

                    # show login form
                    username = st.text_input('Username')
                    password = st.text_input('Password', type="password")
                    login_btn = st.button('Login', type="primary")

                    # add to the session state
                    if login_btn and username != "" and password != "":

                        # now fetch the user from database
                        cred_match = False
                        user = User.get_user_by_username(username)
                        if user is not None and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                            cred_match = True
                            auth_state().user = {
                                'userid': user.userid,
                                'username': user.username,
                                'level': user.authlevel.value if isinstance(user.authlevel, UserAuthLevel) else user.authlevel
                            }
                            st.experimental_rerun()
                        if not cred_match:
                            st.markdown(':red[Invalid username or password]')
            
        return wrapper

    return requires_auth_level