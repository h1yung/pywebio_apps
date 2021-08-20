# PyWebIO library
from pywebio import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *

# Other libraries
import notetubeUtils as nu
from urllib import parse

# from notetubeUtils import *

def main():
    # Display the signup page as well as a page responsible for the step that finishes sign up.
    
    nu.authenticate_firebase()
    
    # finish signing up
    search = eval_js("window.location.search")
    query = {'page':None}

    try:
        query = dict(parse.parse_qsl(search.lstrip('?')))
    except:
        y = None

    if query['page'] in list(nu.find_firebase_auth_keys().keys()):
        nu.finish_signing_up(query['page'])
    
    if query['page'] in list(nu.find_firebase_keys().keys()):
        nu.reset_password(query['page'])
        
    # sign up, login & watch prompt
    while True:
        choice = actions('📺 NoteTube',
                            ['Signup', 'Login', 'Watch'])

        if choice == 'Signup':
            nu.signup()
        if choice == 'Login':
            nu.login()
        if choice == 'Watch':
            nu.watch()