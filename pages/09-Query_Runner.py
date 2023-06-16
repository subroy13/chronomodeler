import streamlit as st
import pandas as pd
from functools import wraps


from chronomodeler.dbutils import db_query_execute, db_query_fetch


# ============================================================
#       Some dependency functions for handling authorization
# ============================================================


def auth_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    return st.session_state


# Easy inteceptor for auth
def requires_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if auth_state().user is not None:
            with st.sidebar:
                logg_user = auth_state().user
                st.success(f"Welcome {logg_user}!")
                logout_btn = st.button('Logout', type = "primary")

                # remove from session state
                if logout_btn:
                    auth_state().user = None
                    st.experimental_rerun()

            return fn(*args, **kwargs)
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
                    admin_user = st.secrets['admin'].get("username")
                    admin_pass = st.secrets['admin'].get("password")
                    if admin_user != username or admin_pass != password:
                        st.markdown(':red[Invalid username or password]')
                    else:
                        auth_state().user = "admin"
                        st.experimental_rerun()
        
    return wrapper



@requires_auth
def queryRunnerPage():
    query = st.text_area("SQL Query")
    require_fetch = st.checkbox(label="Require Fetching", value=True)
    execute_btn = st.button('Execute')
    if execute_btn and query is not None and query != "":
        if require_fetch:
            df = pd.DataFrame(db_query_fetch(query, ()))
            st.dataframe(df)
        else:
            res = db_query_execute(query, ())
            st.success('Query executed successfully!')



queryRunnerPage()