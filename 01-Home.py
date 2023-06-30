import sys, os, re
import bcrypt
import streamlit as st

from chronomodeler.models import User, UserAuthLevel, Simulation, Experiment

st.set_page_config(
    layout="wide"
)


@st.cache_data
def runInitialSetup():
    print('Initializing database schema if not created already')
    User.create_table()
    Simulation.create_table()
    Experiment.create_table()
    return True


def signupSection():
    st.header("Sign Up")
    with st.form('user-sign-up', clear_on_submit=False):
        useremail = st.text_input('Email', max_chars=256, help="Enter your work email address")
        password = st.text_input('Password', type="password", help="Enter your preferred password. \nShould contain alphabets and numbers and \nspecial symbols for added protection.")
        confirm_password = st.text_input('Confirm Password', type="password", help="Retype your password")
        submit_btn = st.form_submit_button("Sign Up")

        if submit_btn:
            if re.search(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', useremail, re.I) is None:
                st.error('Invalid email address')
            elif password != confirm_password or password == "":
                st.error('Password does not match confirm password')
            else:
                # everything is fine, create user
                salt = bcrypt.gensalt()
                user = User(
                    username=useremail,
                    password_hash=bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8'),
                    authlevel=UserAuthLevel.PRIVATE
                )
                user.insert()  # modified the user
                st.success('You are registered sucessfully, Proceed to any other page to login.')



def instructionSection():
    st.header('Instructions for use')
    st.markdown("""
### Simulations

In the **Simulations** section, you can create, view, and delete datasets. Follow these steps to create a simulation:

1. Click on the **Create Simulation** button.
2. Specify the dataset details, such as renaming columns and selecting the time index column.
3. Preprocess your data as needed.
4. Save the simulation for future reference.

You can view and manage your simulations from the simulation dashboard. Feel free to explore the simulation features and options available.

### Experiments

The **Experiments** section lets you perform in-depth analysis and prediction on your time series data using a control flow diagram. Here's how to conduct an experiment:

1. Select a simulation from the dropdown menu or create a new one if needed.
2. Define the train and test splits for your data.
3. Design a flowchart to preprocess and transform your data using the visual control flow editor.
    a. You can load and save the flowchart draft as necessary using the in menu options.
4. Choose a prediction model for your experiment.
5. Click on **Execute** to process and fit the model.
    a. Below the control flow editor, it should display the metrics of the fitted model.
6. Analyze the metrics on the train and test data, as well as future predictions.
7. For reference, you can save the experiment results along with the config and the metrics.
8. You can add as many experiments as you want. Current experiment can use predictions from previous experiments as well.

You can save and load your experiment configurations for reuse and comparison.

### Flow Diagram Blocks

There are primarily two types of blocks in the control flow editor.

1. Transformation
    - Add 
    - Subtract
    - Multiply
    - Division
    - Transformation (Generic Transformation like Sine, Cosine, Exponentiation). All transformations have an optional parameter which controls its behaviour. Example: The period length for sine and cosine, The window length in Lag operator.

2. Modelling
    - Dependent Variable
    - Indepdent Variable
    - Merge (A merge mixing block that is used to indicate a collection of variables). This is useful just before the modelling block.
    - Modelling / Prediction Method (This block defines the type of the model used to predict the variables). These also take parameter, sometimes multiple parameters, separated by comma.
        * CAGR - Parameter is stride, window. The stride is the last value on which CAGR is applied. The window is the number of timeperiods aggregated over for calculating CAGR.
        * Growth - Parameter is stride, annual growth percentage.

    
Feel free to explore the features and functionalities of Chronomodeller. If you have any questions or need assistance, refer to the **Help** section or reach out to our support team.

Happy exploring and analyzing your time series data with Chronomodeller!
    """)
    




def ChronoModelerHomePage():
    runInitialSetup()
    st.title('Welcome to Chronomodeller!')
    st.markdown("Chronomodeller is a powerful tool for analyzing time series data. This user-friendly app allows you to create simulations and conduct experiments to gain insights and make predictions.")
    signupSection()
    st.markdown('<hr/>', unsafe_allow_html=True)
    instructionSection()
    


ChronoModelerHomePage()
