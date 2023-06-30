import pandas as pd
import numpy as np
import streamlit as st
from streamlit_searchbox import st_searchbox
from barfi import st_barfi, barfi_schemas, save_schema
import datetime as dt
from time import sleep
import plotly.express as px

from chronomodeler.dbutils import (
    get_simulation_suggestion, get_experiment_count,
    get_experiment_data, insert_data_to_simulation, delete_experiment_data,
    insert_experiment_config, get_experiment_config
)
from chronomodeler.blocks import (
    transformation_block, prediction_block, get_indep_block, get_dep_block,
    add_block, subtract_block, mult_block, div_block, merge_block
)
from chronomodeler.experiment import Experiment
from chronomodeler.expconfig import ExperimentConfig
from chronomodeler.authentication import requires_auth, UserAuthLevel

def view_experiment_results(selected_sim, exp_count):
    exp_choice = st.selectbox(
        label='Choose Experiment Number',
        options=[] if exp_count == 0 else list(range(1, exp_count + 1)),
        disabled=(exp_count == 0),
        key="exp-choice-view"
    )
    if exp_choice is not None:
        config, results = get_experiment_config(selected_sim['name'], exp_choice)

        # show the metrics
        st.markdown('**Experiment Metrics**')
        st.write(results)

        # get the data and show plot of the dependent variable
        df = get_experiment_data(selected_sim['name'], exp_choice)
        df['Human Time'] = df['Time'].dt.strftime('%d %b, %Y')
        fig = px.line(df, x = 'Time', y = ExperimentConfig.get_dependent_variable_from_config(config))
        st.plotly_chart(fig, use_container_width=True)

        # show the data also
        st.markdown('<hr/><b>Experiment Predictions</b>', unsafe_allow_html=True)
        st.dataframe(df)

        # finally have a checkbox to show the config
        show_config = st.checkbox('Show Experiment Config', value=False)
        if show_config:
            st.markdown('**Experiment Config**')
            st.write(config)


def delete_experiment_results(selected_sim, exp_count):
    exp_choice = st.selectbox(
        label='Choose Experiment Number',
        options=[] if exp_count == 0 else list(range(1, exp_count + 1)),
        disabled=(exp_count == 0),
        key="exp-choice-delete"
    )
    if exp_choice is not None:
        df = get_experiment_data(selected_sim['name'], exp_choice)
        st.dataframe(df)

        # delete button
        del_exp_btn = st.button('Delete Experiment')
        if del_exp_btn:
            delete_experiment_data(selected_sim['name'], exp_choice)
            st.success(f"Deleted Experiment {exp_choice} from Simulation {selected_sim['name']}. This page will auto-refresh in 5 seconds.")

            sleep(5)  # auto refresh
            st.experimental_rerun()



def create_experiment(selected_sim, exp_count: int):
    current_exp = exp_count + 1
    st.subheader(f"Enter Details for Experiment {current_exp}")

    # training, testing and prediction time choices
    train_dates = st.date_input('Training Data Range', value=[dt.datetime(2019,1,1), dt.datetime(2021,12,31)])
    test_dates = st.date_input('Testing Data Range', value=[dt.datetime(2022,1,1), dt.datetime(2022,12,31)])
    pred_dates = st.date_input('Prediction Data Range', value=[dt.datetime(2023,1,1), dt.datetime(2024,12,31)])

    # Now different types of blocks
    df = get_experiment_data(selected_sim['name'], exp_num=0)   # get the initial data
    collist = df.columns.values.tolist()
    dep_block = get_dep_block(collist)
    indep_block = get_indep_block(collist)

    # saved_schemas = barfi_schemas()
    # select_schema = st.selectbox('Select a saved computation flow:', saved_schemas)
    barfi_result = st_barfi(
        base_blocks= {
            'Transformation': [transformation_block, add_block, subtract_block, mult_block, div_block],
            'Modelling': [prediction_block, dep_block, indep_block, merge_block]
        }
    )

    if barfi_result is not None and len(barfi_result) > 0:
        exp = Experiment(barfi_schema= barfi_result, data = df, sim_name=selected_sim['name'])
        result, shap = exp.do_experiment(train_dates, test_dates, pred_dates)

        st.markdown(f"Model trained on {shap[0]} observations and {shap[1]} features")
        st.write(exp.results)
        st.dataframe(result)

        # show the experiement related plot also
        show_plot = st.checkbox('Show Visualization Plot', value=False)
        if show_plot:
            # TODO: Add option to whether to show only target or all non-time columns
            fig = px.line(df, x = 'Time', y = exp.target_colname)
            st.plotly_chart(fig, use_container_width=True)


        # if you are okay with the results, try to save it
        save_exp_btn = st.button('Save Experiment')
        if save_exp_btn:
            db_result = result
            db_result['experiment_num'] = current_exp
            db_result = db_result.drop(labels=['Human Time'], axis = 1)
            insert_data_to_simulation(db_result, selected_sim['name'], current_exp)
            insert_experiment_config(exp.get_experiment_config(), exp.results, selected_sim['name'], current_exp)
            st.success('Experiment Saved Successfully! This page will reload in 5 seconds')

            sleep(5)
            st.experimental_rerun()


@requires_auth(auth_level=UserAuthLevel["PRIVATE"])
def experimentPage():
    st.header('Experiment Actions')

    # select action
    exp_action_choice = st.radio(
        label='Select Experiment Action',
        options=['Create', 'View', 'Delete']
    )

    selected_sim = st_searchbox(
        search_function=lambda x: [(row['name'], row) for row in get_simulation_suggestion(x)],
        label="Select Simulation"
    )

    if selected_sim is not None:
        exp_count = get_experiment_count(selected_sim['tablename'])
        st.markdown(f":blue[This simulation have {exp_count} experiments!]")

        if exp_action_choice == 'Create':
            create_experiment(selected_sim, exp_count)
        elif exp_action_choice == 'View':
            view_experiment_results(selected_sim, exp_count)
        elif exp_action_choice == 'Delete':
            delete_experiment_results(selected_sim, exp_count)
        else:
            raise ValueError("Invalid experiment action")


experimentPage()