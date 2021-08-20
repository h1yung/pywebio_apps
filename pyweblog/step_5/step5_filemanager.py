from pywebio import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import hold

# Import other Python libraries
import os

# Import util file with pyweblog classes
import step5_pyweblog_util as pwl

# Change here
blogwriter_url = "https://pyweb.io/shared/step5_writer"

def generate_datatable():
    '''
    Custom function to generate data to place in the CRUD table
    Index 0 should be the headers.
    datatable = [['header1', 'header2']] + data
    "data" should be format [[row1col1,row1col2], [row2col1,row2col2]]
    size of sublist = # of header labels
    '''
    datatable = [['files']] + [[filepath] for filepath in pwl.find_blogfiles()]
    
    return datatable
    
def edit_table(i):
    '''Load an old blog post through CRUD table and edit it'''
    
    i = i - 1 # shift index since header is not included in 'filepaths'
    filepaths = pwl.find_blogfiles()
    run_js('window.location.href = a;', a= blogwriter_url + "?page=" + filepaths[i][:-5])
    
def delete_table(i):
    '''Delete blog post through CRUD table and remove it from a directory'''
    
    i = i - 1 # shift index since header is not included in 'filepaths'
    filepaths = pwl.find_blogfiles()
    os.remove(filepaths[i])

def main():
    '''Filemanager for Step 5'''
    global blogwriter_url
    
    crud_table = pwl.CRUDTable(gen_data_func=generate_datatable, edit_func=edit_table, del_func=delete_table)
    crud_table.put_crud_table()
    put_link("create new blog", url=blogwriter_url)
    hold()