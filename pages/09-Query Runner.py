import streamlit as st
import pandas as pd

from chronomodeler.models import UserAuthLevel
from chronomodeler.dbutils import db_query_fetch, db_query_execute
from chronomodeler.authentication import requires_auth

@requires_auth(auth_level=UserAuthLevel.DEVELOPER)
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