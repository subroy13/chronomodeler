import streamlit as st
from streamlit_searchbox import st_searchbox
import numpy as np
import os, json, re
import pandas as pd

from chronomodeler.constants import TIME_FORMAT_LIST
from chronomodeler.authentication import requires_auth, get_auth_userid
from chronomodeler.models import User, UserAuthLevel, Simulation, Experiment
from chronomodeler.apimethods import (
    insert_data_to_experiment, 
    delete_simulation_data_table,
    get_simulation_data_initial,
    delete_data_from_experiment
)
from chronomodeler.qboutils import fetch_all_qbo_data


def simulationCreateManualDataSection(sim_name, userid):
    # Step 1: Upload File and Parse Excel Sheet
    with st.form(key='input-file'):
        st.subheader('Input File Details')
        input_f = st.file_uploader('Input File', accept_multiple_files=False)
        if input_f is not None:
            xl = pd.ExcelFile(input_f)
            input_sheet_name = st.selectbox('Input Excel Sheet Name', options=xl.sheet_names)
        
        parse_file = st.form_submit_button('Parse Excel Sheet')
        if parse_file and input_f is not None:
            df = xl.parse(sheet_name=input_sheet_name)
            st.success(f"Found {df.shape[0]} rows and {df.shape[1]} columns in the dataset")
            st.session_state['data'] = df
    
    
def simulationCreateQBODataSection(sim_name, userid):
    realm_id = st.text_input('Quickbooks Account Realmid')
    access_token = st.text_input('API Access Token')
    
    colqbo_1, colqbo_2, colqbo_3 = st.columns(3)
    with colqbo_1:
        start_year = st.number_input('Start Year', min_value=1970, max_value=2100)
    with colqbo_2:
        end_year = st.number_input('End Year', min_value=1970, max_value=2100)
    with colqbo_3:
        data_freq = st.radio('Data Frequency', options=['Yearly', 'Monthly'])
    
    fetch_data = st.button('Fetch QBO Data using API', help='Note that this may incur API cost / charges at your developer account')
    if fetch_data:
        if realm_id is not None and access_token is not None and realm_id != '' and access_token != '':
            df = fetch_all_qbo_data(realm_id, access_token, start_year, end_year, data_freq)  # fetches the raw data
            st.session_state['qborawdata'] = df
        else:
            st.error('Invalid realmid or access token')

    if st.session_state.get('qborawdata') is not None:
        df = st.session_state.get('qborawdata')
        st.write(f"Fetched data of {df.shape[1] - 1} varibles across {df.shape[0]} timepoints")
        selectcollist = st.multiselect(label='Select Columns from Reports', options=[x for x in df.columns.tolist() if x not in ['LineItem', 'Time']])

        subdf = df[selectcollist + ['Time']]
        st.write(f"Please verify the selected data below")
        st.write(subdf)

        proceed_btn = st.button('Looks Okay! Proceed')
        if proceed_btn:
            st.session_state['data'] = subdf


def simulationCreateSection(userid):
    sim_name = st.text_input('Simulation Name')
    # TODO: add validation of simulation name unique check

    sim_create_choice = st.radio(
        'Choose Data Creation Type', 
        options=['Manual Upload', 'Import From Quickbooks'],
        horizontal=True
    )

    # Step 1: Fetch the raw data
    if sim_create_choice == 'Manual Upload':
        simulationCreateManualDataSection(sim_name, userid)
    else:
        simulationCreateQBODataSection(sim_name, userid)

    # Step 2: Optional Renaming of the variables
    if st.session_state.get('data') is not None:
        with st.form('preprocess-data'):
            df = st.session_state.get('data')
            st.markdown('Rename the columns as needed, otherwise leave blank')

            # for each column, create an input
            col_grids = st.columns(3)

            collist = list(df.columns.values.tolist())
            if sim_create_choice == 'Manual Upload':
                col_names = { col: re.sub(r'\n+', ' ', col) for col in collist}
            else:
                col_names = { col: re.sub(r'\n+', ' ', col) for col in collist if col != 'Time'}
            old_cols = list(df.columns.values.tolist())
            new_cols = [col_grids[i % 3].text_input(label = col_names[col] ) for i, col in enumerate(col_names)]

            # time column selection (only for manual upload)
            if sim_create_choice == 'Manual Upload':
                col1, col2 = st.columns(2)
                with col1:
                    time_col = st.selectbox(label='Time Column', options=collist)
                with col2:
                    time_format = st.selectbox(label='Time Format', options=TIME_FORMAT_LIST)
            else:
                time_col = 'Time'
                time_format = "%Y-%m-%d"

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

    # creating the simulation object
    if st.session_state.get('processed_data') is not None:
        subdf: pd.DataFrame = st.session_state.get('processed_data')
        st.dataframe(subdf)
        confirm_save = st.button('Confirm Data')
        if confirm_save:
            # create the simulation object
            sim = Simulation(userid,sim_name)
            sim.insert()   # insert the simulation
            st.session_state['data'] = None 
            st.session_state['xl'] = None

            # create the initial experiment
            expp = Experiment(sim.simid, 'initial', {}, {}, initial=True)
            expp.insert()   # insert the initial experiment (which is same as dummy)

            # insert data to the experiment
            insert_data_to_experiment(subdf, expp, sim, userid)
            st.success("You're good to go for the experiments!")


    
def simulationEditSection(userid):
    # TODO: Update data, and then run all the experiments 1 by 1
    selected_sim = st_searchbox(
        search_function=lambda x: [(sim.sim_name, sim) for sim in Simulation.search(x, userid) ],
        label="Select Simulation to Update",
        key="select-sim-edit"
    )
    if selected_sim is not None:
        initial_df = get_simulation_data_initial(selected_sim, userid)
        st.dataframe(initial_df)

        # upload new data
        st.subheader('Upload New Data Here')
        input_f = st.file_uploader('Input File', accept_multiple_files=False)
        if input_f is not None:
            xl = pd.ExcelFile(input_f)
            input_sheet_name = st.selectbox('Input Excel Sheet Name', options=xl.sheet_names)        
            df = xl.parse(sheet_name=input_sheet_name)
            st.success(f"Found {df.shape[0]} rows and {df.shape[1]} columns in the dataset")
            
            with st.form('preprocess-data-update'):
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
                    if df is not None:
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
            rerun_exp_btn = st.button('Save and Rerun Experiments')
            if rerun_exp_btn:
                old_cols = [col for col in initial_df.columns if col not in ['experiment_id']]
                new_cols = [col for col in subdf.columns]
                if set(old_cols) != set(new_cols):
                    st.error(f"The updated excel does not match the schema of existing simulation data.")
                    st.error(f"The columns present in new data but not in old data are: {', '.join( set(new_cols).difference(set(old_cols)) )}")
                    st.error(f"The columns present in old data but not in new data are: {', '.join( set(old_cols).difference(set(new_cols)) )}")
                else:
                    initial_exp = selected_sim.get_initial_experiment()
                    insert_data_to_experiment(subdf, initial_exp, selected_sim)
                    st.success('Data Updated Successfully')
                        

def simulationListSection(userid):
    sim_count = Simulation.count(userid)
    st.markdown(f"You have {sim_count} many simulations")
    selected_sim = st_searchbox(
        search_function=lambda x: [(sim.sim_name, sim) for sim in Simulation.search(x, userid) ],
        label="Select Simulation to View",
        key="select-sim-view"
    )
    if selected_sim is not None:
        df = get_simulation_data_initial(selected_sim, userid)
        st.dataframe(df)
        


def simulationDeleteSection(userid):
    selected_sim = st_searchbox(
        search_function=lambda x: [(sim.sim_name, sim) for sim in Simulation.search(x, userid) ],
        label="Select Simulation to Delete",
        key="select-sim-delete"
    )
    if selected_sim is not None:
        df = get_simulation_data_initial(selected_sim, userid)
        st.dataframe(df)

    delete_submit = st.button('Delete Simulation')
    if delete_submit and selected_sim is not None:
        Simulation.delete(selected_sim.simid)
        delete_simulation_data_table(selected_sim, userid)
        


@requires_auth(auth_level=UserAuthLevel.PRIVATE)
def simulationPage():
    userid = get_auth_userid()
    st.header('Chrono Modeler Simulation Page')

    st.subheader('Simulation Actions')
    sim_action_choice = st.radio(
        'Choose Action', 
        options=['Create', 'List', 'Update', 'Delete'],
        horizontal=True
    )

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.subheader(f"Perform {sim_action_choice} Simulation")

    if sim_action_choice == 'Create':
        simulationCreateSection(userid)
    elif sim_action_choice == 'List':
        simulationListSection(userid)
    elif sim_action_choice == 'Delete':
        simulationDeleteSection(userid)
    elif sim_action_choice == 'Update':
        simulationEditSection(userid)
    else:
        st.error('Invalid Simulation Action')


simulationPage()