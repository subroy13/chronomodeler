############################
# Different Types of Blocks in Barfi
############################

import streamlit as st
from barfi import Block
from .models import ChronoModel

#####################################
# Transformation Block
transformation_block = Block(name='Transformation')

# Add the input and output interfaces
transformation_block.add_input()
transformation_block.add_output()

# Add an optional display text to the block, and functionality inputs
transformation_block.add_option(name='display-option', type='display', value='Apply Transformation')
transformation_block.add_option(name='method-option', type='select', 
                                items=['Identity', 'Sine', 'Cosine', 'Exponent', 'Log', 'Power', 'Lag'], 
                                value='Identity')

transformation_block.add_option(name='method-param', type='number')


#####################################
# Prediction Method Block
prediction_block = Block(name='Modelling')

# Add the input and output interfaces
prediction_block.add_output()

# Add an optional display text to the block, and functionality inputs
prediction_block.add_option(name='display-option', type='display', value='Modelling Method')
prediction_block.add_option(name='method-option', type='select', 
                                items=['Identity', 'CAGR', 'Growth', 'Experiment Output'] + ChronoModel.MODEL_LISTS, 
                                value='Identity')

prediction_block.add_option(name='method-param', type='input')



#####################################
# Feature Input Block

def get_indep_block(collist: list[str]):
    indep_block = Block(name='Independent Variable')
    indep_block.add_input(name="Modelling Method")
    indep_block.add_output(name='Output')
    indep_block.add_option(name='display-option', type='display', value='Independent Variable')
    indep_block.add_option(name='column-option', type='select', items=collist, value = collist[0])
    return indep_block

# Target Output Block
def get_dep_block(collist: list[str]):
    dep_block = Block(name = 'Dependent Variable')
    dep_block.add_input(name = 'Modelling Method')
    dep_block.add_input(name = 'Merge Input')
    dep_block.add_option(name='display-option', type='display', value='Dependent Variable')
    dep_block.add_option(name='column-option', type='select', items=collist, value = collist[0])
    return dep_block

const_block = Block(name = 'Constant')
const_block.add_output(name = 'Output')
const_block.add_option(name = 'display-option', type="display", value = 'Constant')
const_block.add_option(name='value-option', type="number", value=0)



###################################
# Mixer Block (Takes 5 inputs to 1 output)

add_block = Block(name = 'Add')
add_block.add_input()
add_block.add_input()
add_block.add_input()
add_block.add_input()
add_block.add_input()
add_block.add_output()


subtract_block = Block(name='Subtract')
subtract_block.add_input()
subtract_block.add_input()
subtract_block.add_output()


mult_block = Block(name='Multiply')
mult_block.add_input()
mult_block.add_input()
mult_block.add_output()


div_block = Block(name='Division')
div_block.add_input()
div_block.add_input()
div_block.add_output()

###################################
# Merged Block (Takes 5 inputs to 1 output)

merge_block = Block(name = 'Merge')
merge_block.add_input()
merge_block.add_input()
merge_block.add_input()
merge_block.add_input()
merge_block.add_input()
merge_block.add_output()
