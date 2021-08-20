# spam/glitch: at 1 video, spamming watch button and stuff causes to go to -1 videos left
# delete auth key after expiration in database 
# production server: duplicate report email?


# PyWebIO library
from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *
from pywebio.session import *

# Other libraries
import ssl
import numpy as np
from functools import partial
from urllib import parse
from cuid import *
import requests
import json
from youtubesearchpython import *
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTP_SSL_PORT
import firebase_admin
from firebase_admin import db
from firebase_admin import auth

# web link root
version = "test" ## CHANGE HERE ##
if version == "test":
    root_link = "https://notetube-test.pyweb.io/test_"
if version == "production":
    root_link = "https://notetube.pyweb.io/"

# for firebase login authentication
rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_WEB_API_KEY = "AIzaSyBMB6UEWY3o6io9uekgUqcX1GTVTJK4s0M"
# for youtube search query
ssl._create_default_https_context = ssl._create_unverified_context
# how many results to display (19 is max for this library)
NUM_RESULTS = 15

class UserSession:
    '''
    Methods and variables for the viewer end of the app.
    1. Search YouTube videos through keyword
    2. Display results in a table, where you can:
    2.1. Watch video (a limited number of times set by admin)
    2.2. Take notes, view, and delete
    3. Sync with the firebase database from and to.
    '''

    def __init__(self, email):
        self.email = email
        self.uid = auth.get_user_by_email(email).uid
        self.videos_left = 0
        self.current_session_notes = {}
        self.all_notes = {}

    def watch(self, dummy, search, title, duration, channel, link):
        '''
        Display selected YouTube video as an embedded object.
        Also can take notes and save it as part of the current session.
        '''
        
        embed_key = link.split("?v=")[1]
        link = "https://www.youtube.com/embed/" + embed_key + "?loop=1" + "&playlist=" + embed_key
        
        popup(title, closable=False, content=
            [
                put_html(
                    '<iframe width="100%" height="400px" src="' + link + '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
                ),
                put_textarea(
                    label="Note",
                    name="note", value=self.load_note(embed_key)
                ),
                put_buttons(
                    ['Save Note', 'Exit'],
                    lambda x: self.save_notes(markdown=pin.note, embed_key=embed_key, search=search) if x == 'Save Note'
                    else self.exit_video(search=search))
            ]
        )

    def handle_no_videos_left(self):
        '''
        With no more videos allowed to watch, open a popup to block user from
        clicking on any videos. If there are any notes during the current session
        that has not been sent to the admin email, do so and empty it, moving it
        to list of all notes.
        '''
        
        if self.videos_left <= 0:
            # if current_session_notes is filled, empty it
            # we also send an email.
            if len(self.current_session_notes) != 0:
                send_email(self.email, "NoteTube Report", self.package_notes())
                self.current_session_notes = {}
                self.update_firebase()
            popup("no more videos left! wait a bit", closable=False)
            return

    def display_table(self, search, titles, views, durations, channels, links):
        '''
        Render page header and table of search results: 
        1. ability to view and delete notes if they exist for a specific video
        2. information about videos and the button to watch and take notes on them
        '''

        # if no more videos left, then quit
        self.handle_no_videos_left()

        # play buttons column
        play = [
            put_buttons(["▶"], onclick=partial(self.watch, 
                search=search, link=links[i], title=titles[i], 
                duration=durations[i], channel=channels[i])) for i in range(int(len(links)))
        ]
        
        # view & delete notes column
        notes = []
        delete_notes = []
        for i in range(int(len(links))):
            embed_key = links[i].split("?v=")[1]
            if self.is_existing_note(youtubekey=embed_key):
                notes.append(put_buttons("📝", onclick=partial(self.load_note_popup, youtubekey=embed_key)))
                delete_notes.append(
                    put_buttons("🗑", onclick=partial(self.delete_note, youtubekey=embed_key, search=search)))
            else:
                notes.append(put_text(""))
                delete_notes.append(put_text(""))

        # transposing matrix for put_table format
        matrix_t = list(np.transpose([play, titles, views, durations, channels, notes, delete_notes]))

        # rendering all the content inside clearable scope
        with use_scope('scope', clear=True):
            put_grid([
                [style(put_image(
                    "https://i.imgur.com/lcYHHd5.jpg"),
                    "width:100px;"
                )],
                [style(put_text("\nTop " + str(len(links))
                                + " results for: "
                                + search
                                + "\nSearch provided by YouTube\n"
                                + "Videos Left: "
                                + str(self.videos_left)
                                ),
                       "font-size:80%;")],
            ], direction="column")
            put_html("<hr>")
            style(
                put_table(
                    matrix_t,
                    header=[
                        'Watch & Take Notes',
                        'Title',
                        'Views',
                        'Duration',
                        'Channel',
                        'Note',
                        'Delete Note'
                    ]
                ),
                "color: black; word-break: keep-all"
            )

    def exit_video(self, search):
        '''exit popup window, refresh table without saving notes'''

        self.videos_left = self.videos_left - 1
        self.update_firebase()

        close_popup()

        searched_vids = search_videos(search)
        self.display_table(
            search,
            searched_vids[0],
            searched_vids[1],
            searched_vids[2],
            searched_vids[3],
            searched_vids[4]
        )

    def save_notes(self, markdown, embed_key, search):
        '''close popup window, save note, refresh table'''

        self.videos_left = self.videos_left - 1
        self.current_session_notes[embed_key] = markdown
        self.all_notes[embed_key] = markdown

        self.update_firebase()

        close_popup()

        searched_vids = search_videos(search)
        self.display_table(
            search,
            searched_vids[0],
            searched_vids[1],
            searched_vids[2],
            searched_vids[3],
            searched_vids[4]
        )

    def load_note(self, youtubekey):
        '''
        return note content of youtube key.
        if it doesn't exist, then return an empty string.
        '''

        if self.is_existing_note(youtubekey):
            return self.all_notes[youtubekey]
        else:
            return ""

    def load_note_popup(self, dummy, youtubekey):
        '''display note content inside popup window'''

        popup('View Note', closable=False, content=
        [
            put_markdown(self.load_note(youtubekey)),
            put_buttons(
                ['Close'],
                onclick=lambda x: close_popup()
            )
        ]
              )

    def delete_note(self, dummy, search, youtubekey):
        '''delete note from database, refresh table'''

        self.all_notes.pop(youtubekey)
        
        try:
            self.current_session_notes.pop(youtubekey)
        except:  # if note doesnt exist in current session, just forget it
            pass

        self.update_firebase()

        searched_vids = search_videos(search)
        self.display_table(
            search,
            searched_vids[0],
            searched_vids[1],
            searched_vids[2],
            searched_vids[3],
            searched_vids[4])

    def is_existing_note(self, youtubekey):
        '''return True if youtube key exists in all notes'''

        if youtubekey in list(self.all_notes.keys()):
            return True
        else:
            return False

    def search_and_display(self):
        '''search keyword for YouTube video, display results as a table'''
        
        while True:
            data = input_group("NoteTube 📺", [
                input(name="Search", placeholder="search a title"),
                actions(name="cmd", buttons=["Search", {'label': 'Logout', 'type': 'cancel'}])
            ])
            if data is None:
                break
            if data["cmd"] == "Search":
                searched_vids = search_videos(data["Search"])
                self.display_table(
                    data["Search"],
                    searched_vids[0],
                    searched_vids[1],
                    searched_vids[2],
                    searched_vids[3],
                    searched_vids[4]
                )

    def package_notes(self):
        '''
        put all notes together into one string and prepare to
        send it via email
        '''
        
        global root_link

        return_str = ""
        
        for k, v in self.current_session_notes.items():
            return_str = return_str + "Title: " + get_video_title(
                k) + "\n" + v + "\n" + "https://www.youtube.com/watch?v=" + k + "\n\n"
        return_str = return_str + "Admin page: " + root_link + "admin/?page=" + db.reference().get()['users'][self.uid]['encrypt_key']
        
        return return_str

    def update_firebase(self):
        '''
        send information to firebase db of a specific user id,
        syncing it with the object variables.
        '''
        
        db_data = db.reference().child('users').child(self.uid)

        db_data.update({'current_session_notes': self.current_session_notes})
        db_data.update({'all_notes': self.all_notes})
        db_data.update({'videos_left': self.videos_left})

    def sync_with_firebase(self):
        '''
        retrieve information from firebase db of a specific user id
        and sync it with the object variables
        '''
        '''
        retrieve information from firebase db of a specific user id
        and sync it with the object variables
        '''

        db_data = db.reference().get()['users']

        try:  
            self.current_session_notes = db_data[self.uid]['current_session_notes']
        except:
            # if no notes written in the current section, set it to empty dict
            self.current_session_notes = {}
        
        self.videos_left = db_data[self.uid]['videos_left']
        self.all_notes = db_data[self.uid]['all_notes']

class AdminSession:
    '''
    Methods and variables for the admin control panel.
    1. Display control panel and its functionalities.
    2. Sync with the firebase database from and to.
    '''

    def __init__(self, encrypt_key):
        self.uid = find_firebase_keys()[encrypt_key]
        self.email = db.reference().child('users').child(self.uid).get()['email']
        self.encrypt_key = encrypt_key
        self.watch_key = ""
        self.videos_left = 0
        self.current_session_notes = {}
        self.all_notes = {}

    def display_adminpage(self):
        '''
        display admin control panel page based on the user key.
        show: current remaining allotted videos for user, watch key, and session link.
        ask for: new video limit and watch key, defaulting to 5 and "watchkey"; delete account.
        respectively if not specified.
        '''
        
        global root_link
        
        while True:
            
            self.sync_with_firebase()
            
            # e.g. email_user = pywebiouser ; mail_type = @gmail.com
            email_user, mail_type = self.email.split("@")
            
            with use_scope('scope', clear=True):
                put_markdown("# admin page: " + email_user)
                put_link("Session Link",
                        url= root_link + "takenotes/?page=" + email_user + "+" + mail_type)
                put_text("📺 Videos left: " + str(self.videos_left))
                put_text("🔑 Current watch key: " + self.watch_key)
                put_buttons(["delete account"], onclick=partial(self.delete_account, uid=self.uid), link_style=True)
            
            # set watch key and video limit
            params_input = input_group('Configurations',
                                    [
                                        input(label="video limit", type="number", name="video_limit",
                                            validate=is_whole_number, help_text="default: 5"),
                                        input(label="watch key", name="watch_key", 
                                            validate=is_valid_watchkey, type=PASSWORD, help_text="default: watchkey"),
                                        actions(name='cmd', buttons=['Confirm', 'Exit'])
                                    ]
                                )
            if params_input['cmd'] == 'Confirm':
                if params_input["video_limit"] is None: # default is 5
                    self.videos_left = 5
                else:
                    self.videos_left = params_input["video_limit"]
                
                if params_input["watch_key"] is "": # default is "watchkey"
                    self.watch_key = "watchkey"
                else:
                    self.watch_key = params_input['watch_key']
            else:
                run_js('window.location = a;', a=root_link + "signup/")

            self.update_firebase()
            
    def delete_account(self, dummy, uid):
        '''
        delete user info from firebase as well as its database
        '''
        popup('Confirm Account Deletion', [
                put_html('Are you sure you want to permanently delete all your data? Type in your email to confirm.'), 
                put_input(label="Email", name="confirm_email"),
                put_buttons(['Yes', 'No'], onclick=lambda x: self.handle_delete_yes() if x == 'Yes' else self.handle_delete_no())
            ], closable=False
        )
    
    def handle_delete_yes(self):
        '''
        
        '''
        
        if pin.confirm_email == self.email:
            toast("Account has been successfully deleted. Good bye!")
            auth.delete_user(self.uid)
            
            # save uid:email in deleted_users
            user_info = db.reference().child('users').child(self.uid).get()
            db.reference().child('deleted_users').update({self.uid:self.email})
            
            db.reference().child('encrypt_keys').child(self.encrypt_key).delete()
            db.reference().child('users').child(self.uid).delete()
            close_popup()
            run_js('window.location = a;', a= root_link + "signup/")
        else:
            toast("Wrong email. Try again.")
    
    def handle_delete_no(self):
        '''
        
        '''
        close_popup()
        
        
    def update_firebase(self):
        '''
        send information to firebase db of a specific user id,
        syncing it with the object variables.
        encrypt_key for the specific uid will be a new random cuid(),
        so every time a change is submitted via the admin control panel
        we can ensure higher security and protection by changing the control
        panel url that is dependent on encrypt_key.
        '''
        
        db_data = db.reference().child('users').child(self.uid)

        db_data.update({'current_session_notes': self.current_session_notes})
        db_data.update({'all_notes': self.all_notes})
        db_data.update({'videos_left': self.videos_left})
        db_data.update({'watch_key': self.watch_key})
        
        # randomize encrypt key again
        db.reference().child('encrypt_keys').child(self.encrypt_key).delete()
        self.encrypt_key = cuid()
        db_data.update({'encrypt_key':self.encrypt_key})
        db.reference().child('encrypt_keys').update({self.encrypt_key:self.uid})
        
    def sync_with_firebase(self):
        '''
        retrieve information from firebase db of a specific user id
        and sync it with the object variables
        '''

        db_data = db.reference().get()['users']

        try:  
            self.current_session_notes = db_data[self.uid]['current_session_notes']
        except:
            # if no notes written in the current section, set it to empty dict
            self.current_session_notes = {}
        
        self.videos_left = db_data[self.uid]['videos_left']
        self.all_notes = db_data[self.uid]['all_notes']
        self.watch_key = db_data[self.uid]['watch_key']

def send_email(email, subject, content):
    '''send an email'''

    SMTP_HOST = 'smtp.gmail.com'
    SMTP_USER = 'pywebiouser@gmail.com'
    SMTP_PASS = 'hackerchallenge!' # hide this somehow?

    email_message = EmailMessage()
    email_message.add_header('To', email)
    email_message.add_header('From', SMTP_USER)
    email_message.add_header('Subject', subject)
    email_message.set_content(content)
    smtp_server = SMTP_SSL('smtp.gmail.com', port=SMTP_SSL_PORT)
    smtp_server.login(SMTP_USER, SMTP_PASS)
    smtp_server.sendmail(SMTP_USER, [email], email_message.as_bytes())
    smtp_server.quit()


def get_video_title(video_key):
    '''based on youtube video key, return the title'''

    video = Video.get('https://www.youtube.com/watch?v=' + video_key)
    return video["title"]

def authenticate_firebase():
    '''
    authenticate admin permissions to database using service account 
    key JSON file contents from directory, then initialize app with the service
    account to grant admin privileges for this executable.
    '''
    
    try:
        app = firebase_admin.get_app()
    except ValueError as e:
        cred = firebase_admin.credentials.Certificate('./notetube-test-firebase-adminsdk-9fgos-78b9c10383.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://notetube-test-default-rtdb.firebaseio.com/'
        })

def find_firebase_users():
    '''Find all user id's in the firebase db'''
    return list(db.reference().get()['users'].keys())


def find_firebase_keys():
    '''Get all encryption keys in the firebase db'''
    return db.reference().get()['encrypt_keys']


def find_firebase_auth_keys():
    '''Get all authentication keys in the firebase db'''
    
    return db.reference().get()['auth_keys']


def register_firebase_key(encrypt_key, email):
    '''
    For an email user, assign the encrypted key in the database
    after confirming registration through email link.
    '''

    db.reference().child("encrypt_keys").update({encrypt_key: email})


def register_firebase_auth_key(encrypt_key, email):
    '''
    For an email user, assign a temporary authentication key
    in the database during registration.
    '''
    
    db.reference().child("auth_keys").update({encrypt_key: email})


def search_videos(search, num_results=NUM_RESULTS):
    '''
    search for a num_results amount of videos,
    return a list of lists with all the titles, views, durations, channels, and links
    '''

    search = VideosSearch(search, limit=num_results, language='en', region='US')
    search_dict = search.result()

    titles = []
    durations = []
    views = []
    channels = []
    links = []

    for search_result in search_dict['result']:
        titles.append(search_result['title'])
        durations.append(search_result['duration'])
        views.append(search_result['viewCount']['short'])
        channels.append(search_result['channel']['name'])
        links.append(search_result['link'])

    return [titles, views, durations, channels, links]


def login():
    '''try to login with gmail'''
    
    global root_link
    
    while True:
        with use_scope('scope', clear=True):
            put_buttons(["forgot password?"], onclick=forgot_password, link_style=True)
            
        data = input_group("🔒 Login", [
            input(name="email", placeholder="example@gmail.com", required=True),
            input(name="password", type=PASSWORD, placeholder="password", required=True),
            actions(name="cmd", buttons=["Login", {'label': 'Back', 'type': 'cancel'}])
        ])
        if data is None:
            clear('scope')
            break
        elif data["cmd"] == "Login":
            try:
                login = sign_in_with_email_and_password(data["email"], data["password"])
                uid = login['localId']
                encrypt_key = db.reference().child("users").child(uid).get()["encrypt_key"]
                run_js('window.location = a;',
                    a= root_link + "admin/?page=" + encrypt_key)
            except:
                toast("Wrong login/password combination. Try again.")
                pass

def forgot_password(dummy):
    '''
    popup asking for email to reset password link
    '''
    popup("Forgot Password", 
        [
            put_input(label='Email receiving reset password link', name='email'),
            put_buttons(['Send Link'], onclick=send_reset_password)
        ]
    )

def send_reset_password(dummy):
    '''Send email resetting password'''
    
    uid = auth.get_user_by_email(pin.email).uid
    encrypt_key = db.reference().child("users").child(uid).child("encrypt_key").get()
    
    send_email(pin.email,
        subject="NoteTube: Reset Password",
        content=eval_js("window.location")['href'].split("?")[0] + "?page=" + encrypt_key
    )

    popup("Check your email to reset password!", closable=False)
    
def reset_password(encrypt_key):
    '''
    Change password for uid associated with encrypt_key
    '''
    uid = db.reference().child("encrypt_keys").child(encrypt_key).get()
    email = db.reference().child('users').child(uid).child("email").get()
    
    new_password = input("New password for " + email, validate=is_valid_password)
    user = auth.update_user(uid,
        password = new_password
    )
    
    toast("Successfully changed password.")
    run_js('window.location.href = a;', a=eval_js("window.location")['href'].split("?")[0])
        

def sign_in_with_email_and_password(email: str, password: str, return_secure_token: bool = True):
    '''
    setting up: enable signin method in firebase settings
    https://betterprogramming.pub/user-management-with-firebase-and-python-749a7a87b2b6
    '''
    
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": return_secure_token
    })

    r = requests.post(rest_api_url,
                      params={"key": FIREBASE_WEB_API_KEY},
                      data=payload)

    return r.json()
    
def watch():
    '''Start authentication to start watch session by asking email'''
    
    global root_link
    
    while True:
        data = input_group("📧 Email belonging to session", [
            input(name="email", placeholder="example@gmail.com", required=True),
            actions(name="cmd", buttons=["Watch", {'label': 'Back', 'type': 'cancel'}])
        ])
        if data is None:
            break
        elif data["cmd"] == "Watch":
           # check email exists
            email = data["email"]
            email_user, mail_type = (None, None)
            try:
                email_user, mail_type = email.split("@")
                uid = auth.get_user_by_email(email).uid     
            except:
                uid = None
            
            if uid in find_firebase_users():
                run_js('window.location = a;',
                    a= root_link + "takenotes/?page=" + email_user + "+" + mail_type)
            else:
                toast("Invalid account. Try again.")
                
def verify_watch(email):
    '''Finish authentication of watch session by asking for watchkey'''
    
    global root_link
    uid = auth.get_user_by_email(email).uid
    
    while True:
        data = input_group("🔑 Enter watch key for " + email, [
            input(name="watch_key", placeholder="enter code here"),
            actions(name="cmd", buttons=["Watch", "Back"])
        ])
        if data["cmd"] == "Watch":
            if data["watch_key"] == db.reference().child("users").child(uid).get()["watch_key"]:
                break
            else:
                toast("Invalid watch key. Try again.")
        if data["cmd"] == "Back":
            run_js('window.location = a;',
                    a= root_link + "signup/")
                    
def signup():
    '''try to signup with gmail'''
    while True:
        data = input_group("📝 Signup", [
                input(name="email", placeholder="example@gmail.com", required=True, validate=user_exists),
                actions(name="cmd", buttons=["Signup", {'label': 'Back', 'type': 'cancel'}])
            ])
        if data is None:
            return
        elif data["cmd"] == "Signup":

            ### CODE: check if email and password is correct
            try:
                ### generate encrypt key
                encrypt_key = cuid()
                
                ### redirect to admin page
                send_email(data["email"],
                    subject="NoteTube: Finish Setting Up Password",
                    content=eval_js("window.location")['href'].split("?")[0] + "?page=" + encrypt_key
                )
                
                register_firebase_auth_key(encrypt_key, data["email"])
                popup("Check your email to continue signing up!", closable=False)
                return
            except:
                toast("Invalid email. Try again.")
    

def finish_signing_up(auth_key):
    '''finish setting up password'''
    
    global root_link
    
    email = db.reference().child("auth_keys").get()[auth_key]
    password = input(label="Password for: " + email, validate=is_valid_password)
    
    user = auth.create_user(email=email, password=password)
        
    # remove temporary auth key from db, move it to encrypt keys
    db.reference().child("auth_keys").child(auth_key).delete()
    db.reference().child("encrypt_keys").update({auth_key: user.uid})
    # set password, ecrypt_key, videos_left under user in db
    db.reference().child("users").child(user.uid).update({'encrypt_key': str(auth_key)})
    db.reference().child("users").child(user.uid).update({'videos_left': 0})
    db.reference().child("users").child(user.uid).update({'all_notes': {'dummy': ''}})
    db.reference().child("users").child(user.uid).update({'watch_key': str(auth_key)})
    db.reference().child("users").child(user.uid).update({'email': email})
    
    # redirect to front page
    toast("Successfully signed up.")
    
    send_email(
        email,
        subject="NoteTube Admin Page Link",
        content= root_link + "admin/?page=" + auth_key
    )
    
    run_js('window.location.href = a;', a=eval_js("window.location")['href'].split("?")[0])


def user_exists(email):
    '''VALIDATION: if uid associated with email exists in the database or not'''
    try:
        uid = auth.get_user_by_email(email).uid
        
        if uid in find_firebase_users():
            return "The user is already signed up."
    except:
        pass
        
def is_whole_number(num):
    '''VALIDATION: if num is a whole number or not'''
    if num is None:
        return
    elif num < 0:
        return "Enter a whole number!"

def is_valid_watchkey(watchkey):
    '''VALIDATION: if watchkey consists of only alphanumeric characters or not'''
    
    valid_char_set = [character for character in '0123456789ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz']
    
    if watchkey == "":
        return
    else:
        for character in watchkey:
            if character not in valid_char_set:
                return "only alphanumeric characters are acceptable."

def is_valid_password(password):
    '''VALIDATION: if password meets requirements for a firebase auth password or not'''
    
    valid_char_set = [character for character in '0123456789ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz~`!@#$%^&*()-_+=|}]{["\':;?/>.<, ']
    
    if password == "":
        return
    else:
        for character in password:
            if character not in valid_char_set:
                return "only alphanumeric characters are acceptable."
    if len(password) < 6:
        return "password length has to be at least 6."
    
def main():
    pass
