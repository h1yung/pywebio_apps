# PyWebIO library
from pywebio import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *

# Other libraries
from urllib import parse
from notetubeUtils import *

def main():
    # Display the admin page for a specific user that exists in the database.
    # If it doesn't exist, return to the signup menu page.
    
    global root_link
    
    authenticate_firebase()

    search = eval_js("window.location.search")
    query = {'page':None}
    
    try:
        query = dict(parse.parse_qsl(search.lstrip('?')))
    except:
        pass

    if query['page'] in list(find_firebase_keys().keys()):
        admin_session = AdminSession(encrypt_key=query['page'])
        admin_session.display_adminpage()
    else:
        run_js('window.location.href = a;', a=root_link + "signup/")