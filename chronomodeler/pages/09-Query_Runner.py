import streamlit as st
import pandas as pd

from chronomodeler.dbutils import db_query_execute, db_query_fetch


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