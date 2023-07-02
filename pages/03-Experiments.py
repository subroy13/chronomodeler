import datetime as dt
import streamlit as st
from streamlit_searchbox import st_searchbox
from barfi import st_barfi, barfi_schemas, save_schema, load_schemas, load_schema_name
import plotly.express as px
import pandas as pd
from time import time, sleep

from chronomodeler.authentication import requires_auth, get_auth_userid
from chronomodeler.models import User, UserAuthLevel, Simulation, Experiment
from chronomodeler.apimethods import get_simulation_data_initial, insert_data_to_experiment, delete_data_from_experiment
from chronomodeler.blocks import (
    transformation_block, prediction_block, get_indep_block, get_dep_block,
    add_block, subtract_block, mult_block, div_block, merge_block
)
from chronomodeler.expconfig import ExperimentConfig, run_experiment


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
        options=['Create New Experiment', 'Load Existing Experiment', 'Delete Experiment'],
        horizontal=True
    )

    if selected_sim is not None:
        exp_count = selected_sim.get_experiment_count()
        st.markdown(f"""This simulation has {exp_count} experiments!""")

        st.subheader(f"Enter Details for Experiment")

        if exp_action_choice == 'Delete Experiment':
            # load experiment
            selected_expp_delete: Experiment = st_searchbox(
                search_function=lambda x: [(expp.exp_name, expp) for expp in Experiment.search(x, userid) ],
                label="Select Experiment to Delete",
                key="select-expp-delete"
            )
            if selected_expp_delete is not None:
                # show model config and metrics
                col111, col112 = st.columns(2)
                with col111:
                    st.markdown('**Experiment Config**')
                    st.write(selected_expp_delete.config)
                with col112:
                    st.markdown('**Experiment Results**')
                    st.write(selected_expp_delete.results)

                # show the delete button
                delete_exp_btn = st.button('Delete Experiment')
                if delete_exp_btn:
                    delete_data_from_experiment(selected_expp_delete, selected_sim, userid)
                    Experiment.delete(selected_expp_delete.expid)
                    st.success(f"Deleted Experiment {selected_expp_delete.exp_name}. This page will reload in 5 seconds!")
                    sleep(5)
                    st.experimental_rerun()
                    
        else:

            # training, testing and prediction time choices
            train_dates = st.date_input('Training Data Range', value=[dt.datetime(2019,1,1), dt.datetime(2021,12,31)])
            test_dates = st.date_input('Testing Data Range', value=[dt.datetime(2022,1,1), dt.datetime(2022,12,31)])
            pred_dates = st.date_input('Prediction Data Range', value=[dt.datetime(2023,1,1), dt.datetime(2024,12,31)])

            df = get_simulation_data_initial(selected_sim, userid)
            collist = df.columns.values.tolist()
            dep_block = get_dep_block(collist)
            indep_block = get_indep_block(collist)


            if exp_action_choice == "Create New Experiment":
                exp_name = st.text_input('Experiment Name')
        
                # start with blank slate
                barfi_result = st_barfi(
                    base_blocks= {
                        'Transformation': [transformation_block, add_block, subtract_block, mult_block, div_block],
                        'Modelling': [prediction_block, dep_block, indep_block, merge_block]
                    },
                    key="barfi-create-exp"
                )

            elif exp_action_choice == "Load Existing Experiment":
                # load experiment
                selected_expp: Experiment = st_searchbox(
                    search_function=lambda x: [(expp.exp_name, expp) for expp in Experiment.search(x, userid) ],
                    label="Select Experiment to Load",
                    key="select-expp-load"
                )
                if selected_expp is not None:
                    # save the barfi schemas
                    exp_name = selected_expp.exp_name
                    expconf = ExperimentConfig(config = selected_expp.config)
                    gen_schema = expconf.save_schema_temporarily(selected_expp.exp_name)

                    # start with blank slate
                    barfi_result = st_barfi(
                        base_blocks= {
                            'Transformation': [transformation_block, add_block, subtract_block, mult_block, div_block],
                            'Modelling': [prediction_block, dep_block, indep_block, merge_block]
                        },
                        key="barfi-update-exp",
                        load_schema=exp_name
                    )
                else:
                    barfi_result = None
                    exp_name = None
            
            if barfi_result is not None and len(barfi_result) > 0:
                expconf = ExperimentConfig.from_barfi_blocks(barfi_result)
                result, shap, metrics = run_experiment(
                    expconf, df, 
                    train_dates, test_dates, pred_dates,
                    selected_sim
                )
                st.markdown(f"Model trained on {shap[0]} observations and {shap[1]} features")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('Model Metrics')
                    st.write(metrics)
                with col2:
                    st.markdown('Model Prediction')
                    st.dataframe(result)

                # show the experiement related plot also
                show_plot = st.checkbox('Show Visualization Plot', value=False)
                if show_plot:
                    target_col = (expconf.get_target_variable())[1]
                    train_data = df.copy(deep = True)
                    train_data['regime'] = 'Train'
                    test_data = result.copy(deep = True)
                    test_data['regime'] = 'Test'
                    plotdf = pd.concat([train_data, test_data])
                    fig = px.line(plotdf, x = 'Time', y = target_col, color='regime', symbol = 'regime')
                    st.plotly_chart(fig, use_container_width=True)

                # if you are okay with the results, try to save it
                save_exp_btn = st.button('Save Experiment')
                if save_exp_btn:
                    newexp = Experiment(
                        simid = selected_sim.simid,
                        exp_name=exp_name,
                        config=expconf.config,
                        results=metrics,
                        initial=False,
                        expid=selected_expp.expid if exp_action_choice == "Load Existing Experiment" else None
                    )
                    if exp_action_choice == "Load Existing Experiment":
                        newexp.update()   # update the newexp id
                    else:
                        newexp.insert()
                    insert_data_to_experiment(
                        df = result.drop(labels=['Human Time'], axis = 1),
                        expp=newexp,
                        sim=selected_sim,
                        userid=selected_sim.userid
                    )
                    st.success('Experiment Saved Successfully! This page will reload in 5 seconds')

                    sleep(5)
                    st.experimental_rerun()


experimentPage()