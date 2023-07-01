import datetime as dt
import streamlit as st
from streamlit_searchbox import st_searchbox
from barfi import st_barfi, barfi_schemas, save_schema, load_schemas, load_schema_name
import plotly.express as px

from chronomodeler.authentication import requires_auth, get_auth_userid
from chronomodeler.models import User, UserAuthLevel, Simulation, Experiment
from chronomodeler.apimethods import get_simulation_data_initial
from chronomodeler.blocks import (
    transformation_block, prediction_block, get_indep_block, get_dep_block,
    add_block, subtract_block, mult_block, div_block, merge_block
)
from chronomodeler.expconfig import ExperimentConfig

def createExperimentSection(userid, selected_sim: Simulation):
    exp_name = st.text_input('Experiment Name')
    st.subheader(f"Enter Details for Experiment {exp_name}")

    # training, testing and prediction time choices
    train_dates = st.date_input('Training Data Range', value=[dt.datetime(2019,1,1), dt.datetime(2021,12,31)])
    test_dates = st.date_input('Testing Data Range', value=[dt.datetime(2022,1,1), dt.datetime(2022,12,31)])
    pred_dates = st.date_input('Prediction Data Range', value=[dt.datetime(2023,1,1), dt.datetime(2024,12,31)])

    df = get_simulation_data_initial(selected_sim, userid)
    collist = df.columns.values.tolist()
    dep_block = get_dep_block(collist)
    indep_block = get_indep_block(collist)

    # start with blank slate
    barfi_result = st_barfi(
        base_blocks= {
            'Transformation': [transformation_block, add_block, subtract_block, mult_block, div_block],
            'Modelling': [prediction_block, dep_block, indep_block, merge_block]
        }
    )

    if barfi_result is not None and len(barfi_result) > 0:
        # TODO: here we need to perform the experiment things
        expconf = ExperimentConfig.from_barfi_blocks(barfi_result)
        
        pass




def editExperimentSection(userid, selected_sim):
    pass





@requires_auth(auth_level=UserAuthLevel.PRIVATE)
def experimentPage():
    st.header('Experiment Actions')
    userid = get_auth_userid()

    selected_sim: Simulation = st_searchbox(
        search_function=lambda x: [(sim.sim_name, sim) for sim in Simulation.search(x, userid) ],
        label="Select Simulation",
        key="select-sim-delete"
    )


    # select action
    exp_action_choice = st.radio(
        label='Select Experiment Action',
        options=['Create New Experiment', 'Load Existing Experiment'],
        horizontal=True
    )


    if selected_sim is not None:
        exp_count = selected_sim.get_experiment_count()
        st.markdown(f"""
            This simulation has {exp_count.get('draft', 0)} drafts and,
            This simulation has {exp_count.get('final', 0)} final experiments!          
        """)
        if exp_action_choice == "Create New Experiment":
            createExperimentSection(userid, selected_sim)
        elif exp_action_choice == 'Load Existing Experiment':
            editExperimentSection(userid, selected_sim)
        else:
            raise ValueError("Invalid experiment action")


experimentPage()