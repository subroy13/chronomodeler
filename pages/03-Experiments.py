import streamlit as st
from streamlit_searchbox import st_searchbox

from chronomodeler.authentication import requires_auth, get_auth_userid
from chronomodeler.models import User, UserAuthLevel, Simulation, Experiment


def createExperimentSection(userid, selected_sim):
    pass 

def deleteExperimentSection(userid, selected_sim):
    pass

def viewExperimentSection(userid, selected_sim):
    pass

def editExperimentSection(userid, selected_sim):
    pass





@requires_auth(auth_level=UserAuthLevel.PRIVATE)
def experimentPage():
    st.header('Experiment Actions')
    userid = get_auth_userid()

    # select action
    exp_action_choice = st.radio(
        label='Select Experiment Action',
        options=['Create', 'Edit', 'View', 'Delete'],
        horizontal=True
    )

    selected_sim: Simulation = st_searchbox(
        search_function=lambda x: [(sim.sim_name, sim) for sim in Simulation.search(x, userid) ],
        label="Select Simulation",
        key="select-sim-delete"
    )

    if selected_sim is not None:
        exp_count = selected_sim.get_experiment_count()
        st.markdown(f"""
            This simulation has {exp_count.get('draft', 0)} drafts and,
            This simulation has {exp_count.get('final', 0)} final experiments!          
        """)
        if exp_action_choice == "Create":
            createExperimentSection(userid, selected_sim)
        elif exp_action_choice == "View":
            viewExperimentSection(userid, selected_sim)
        elif exp_action_choice == "Delete":
            deleteExperimentSection(userid, selected_sim)
        elif exp_action_choice == "Edit":
            editExperimentSection(userid, selected_sim)
        else:
            raise ValueError("Invalid experiment action")


experimentPage()