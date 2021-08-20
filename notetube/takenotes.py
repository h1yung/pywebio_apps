# PyWebIO library
from pywebio import *
from pywebio.output import *
from pywebio.input import *

# Other libraries
from notetubeUtils import *
from urllib import parse

def main():
    
    global root_link # root url for notetube 
    
    authenticate_firebase()
    
    search = eval_js("window.location.search")
    query = {'page':None}
    email_user, mail_type = (None, None)
    email = None
    uid = None

    try:
        query = dict(parse.parse_qsl(search.lstrip('?')))
        email_user = query['page'].split(" ")[0]
        mail_type = query['page'].split(" ")[1]
        email = email_user + "@" + mail_type
        uid = auth.get_user_by_email(email).uid
    except:
        pass
    
    # (1) ?page={email} -> notetube session
    if uid in find_firebase_users():
        verify_watch(email)
        user_session = UserSession(email=email)
        user_session.sync_with_firebase()
        user_session.search_and_display()
    else:
        run_js('window.location.href = a;', a= root_link + "signup/")