import os, re
import streamlit as st
from streamlit_searchbox import st_searchbox
import pandas as pd
import numpy as np

from chronomodeler.constants import TIME_FORMAT_LIST
from chronomodeler.dbutils import (
    create_simulation, insert_data_to_simulation, get_simulation_suggestion, 
    delete_simulation, get_simulation_data_snippet, list_simulations
)
from chronomodeler.authentication import requires_auth, UserAuthLevel


def simulationCreateSection():
    sim_name = st.text_input('Simulation Name')

    with st.form(key='input-file'):
        st.subheader('Input File Details')
        input_f = st.file_uploader('Input File', accept_multiple_files=False)
        parse_file = st.form_submit_button('Parse File')
        if parse_file and input_f is not None:
            xl = pd.ExcelFile(input_f)
            st.session_state['xl'] = xl
    
    if st.session_state.get('xl') is not None:
        with st.form('intput-sheet'):
            xl = st.session_state.get('xl')
            input_sheet_name = st.selectbox('Input Excel Sheet Name', options=xl.sheet_names)
            parse_file = st.form_submit_button('Parse Excel Sheet')
            if parse_file and input_f is not None:
                df = xl.parse(sheet_name=input_sheet_name)
                st.success(f"Found {df.shape[0]} rows and {df.shape[1]} columns in the dataset")
                st.session_state['data'] = df

    if st.session_state.get('data') is not None:
        with st.form('preprocess-data'):
            df = st.session_state.get('data')
            st.markdown('Rename the columns as needed, otherwise leave blank')

            # for each column, create an input
            col_grids = st.columns(3)

            collist = list(df.columns.values.tolist())
            col_names = { col: re.sub(r'\n+', ' ', col) for col in collist}

            old_cols = list(df.columns.values.tolist())
            new_cols = [col_grids[i % 3].text_input(label = col_names[col] ) for i, col in enumerate(col_names)]

            # time column selection
            col1, col2 = st.columns(2)
            with col1:
                time_col = st.selectbox(label='Time Column', options=collist)
            with col2:
                time_format = st.selectbox(label='Time Format', options=TIME_FORMAT_LIST)

            pre_submitted = st.form_submit_button(label="Preprocess")
            if pre_submitted:
                if df is not None and sim_name is not None and sim_name != "":
                    select_collist = []
                    for i in range(len(old_cols)):
                        if old_cols[i] != time_col:
                            new_colname = new_cols[i] if new_cols[i] != "" and new_cols[i] is not None else old_cols[i]
                            select_collist.append(new_colname)
                            df[new_colname] = pd.to_numeric(df[old_cols[i]].astype(str).str.replace(',', ''))
                
                    df['Time'] = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
                    subdf = df.loc[(~df['Time'].isna()), select_collist + ['Time']].reset_index(drop = True).copy(deep = True)
                    subdf['TimeIndex'] = np.arange(subdf.shape[0])

                    st.success(f"Preprocessing completed: Final row count {subdf.shape[0]}!")
                    st.session_state['processed_data'] = subdf
                else:
                    st.error("Invalid input")

    if st.session_state.get('processed_data') is not None:
        subdf: pd.DataFrame = st.session_state.get('processed_data')
        st.dataframe(subdf)
        confirm_save = st.button('Confirm Data')
        if confirm_save:
            create_simulation(sim_name)   # create simulation master tables
            st.session_state['data'] = None 
            st.session_state['xl'] = None
            insert_data_to_simulation(subdf, sim_name, exp_num=0)
            st.success("You're good to go for the experiments!")

def simulationListSection():
    sim_list = list_simulations()
    st.markdown(f"You have {len(sim_list)} many simulations")
    selected_sim = st_searchbox(
        search_function=lambda x: [(row['name'], row) for row in get_simulation_suggestion(x)],
        label="Select Simulation to View",
        key="select-sim-view"
    )
    if selected_sim is not None:
        dt_top, dt_bottom = get_simulation_data_snippet(selected_sim['name'])
        st.dataframe(dt_top)
        if dt_bottom is not None:
            st.markdown('...')
            st.dataframe(dt_bottom)


def simulationDeleteSection():
    selected_sim = st_searchbox(
        search_function=lambda x: [(row['name'], row) for row in get_simulation_suggestion(x)],
        label="Select Simulation",
        key="select-sim-delete"
    )
    if selected_sim is not None:
        dt_top, dt_bottom = get_simulation_data_snippet(selected_sim['name'])
        st.dataframe(dt_top)
        if dt_bottom is not None:
            st.markdown('...')
            st.dataframe(dt_bottom)
    
    delete_submit = st.button('Delete Simulation')
    if delete_submit and selected_sim is not None:
        delete_simulation(sim_name=selected_sim['name'])
        st.success(f"Simulation {selected_sim['name']} is deleted successfully!")


@requires_auth(auth_level=UserAuthLevel["PRIVATE"])
def simulationPage():
    st.header('Chrono Modeler Simulation Page')

    st.subheader('Simulation Actions')
    sim_action_choice = st.radio('Choose Action', options=['Create', 'List', 'Delete'])

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.subheader(f"Perform {sim_action_choice} Simulation")

    if sim_action_choice == 'Create':
        simulationCreateSection()
    elif sim_action_choice == 'List':
        simulationListSection()
    elif sim_action_choice == 'Delete':
        simulationDeleteSection()
    else:
        st.error('Invalid Simulation Action')


simulationPage()
