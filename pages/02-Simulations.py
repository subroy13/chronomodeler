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
    get_simulation_data_initial
)



def simulationCreateSection(userid):
    sim_name = st.text_input('Simulation Name')
    # TODO: add validation of simulation name unique check

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

    # Step 2: Optional Renaming of the variables
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
        label="Select Simulation to Delete",
        key="select-sim-delete"
    )
    pass


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
        options=['Create', 'List', 'Delete'],
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
    elif sim_action_choice == 'Edit':
        simulationEditSection(userid)
    else:
        st.error('Invalid Simulation Action')


simulationPage()