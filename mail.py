from pywebio.input import *
from pywebio.output import *
from pywebio.session import *

import imaplib
import email
from email.message import EmailMessage
from smtplib import SMTP_SSL, SMTP_SSL_PORT
from datetime import datetime, timedelta
from functools import partial

# https://gist.github.com/martinrusev/6121028

def main():
    ########################################################
    # LOG IN                                               #
    ########################################################
    logged_in = False
    time_day = 1
    msg_numbers = None # global var: uids of emails in current selected folder
    imap_server = imaplib.IMAP4_SSL(host='imap.gmail.com')
    current_mode = "Unread"
    msg_requested = None # global var: msg_requested item tracked to use reply function
    put_markdown("## Gmail on BuildMyOwn.App 📧")
    
    
    while not logged_in:
        idpw = input_group("log in", [
            input("username", 
                required=True, 
                name='login',
                help_text='Turn on "https://www.google.com/settings/security/lesssecureapps" and "https://accounts.google.com/b/4/DisplayUnlockCaptcha"'
            ),
            input("password", 
                type=PASSWORD, 
                required=True, 
                name='password', 
                help_text='Go to your Gmail settings -> "Forwarding and POP/IMAP" -> "Enable IMAP"'
            )
        ])  
        
        try:
            imap_server.login(idpw['login'], idpw['password'])
        except:
            pass
        logged_in = True
    
    set_scope("scope")
    display = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=300, keep_bottom=True)

    # Ask for timezone
    # timezone = await select(label="Choose Timezone",
    #     options={
    #         "Pacific Time":"PT",
    #         "Mountain Time":"MT",
    #         "Central Time":"CT",
    #         "Eastern Time":"ET",
    #     }   
    # )

    def refresh_display(mode="Inbox"):
        '''set server based on type of folder requested'''
       
        global msg_numbers
        keyword = "coupon"
        
        # not adjusted for timezones
        day_before = datetime.today() - timedelta(days=1)
        day_before = day_before.strftime('%d-%b-%Y')
        
        if mode == "Sent":
            imap_server.select('"[Gmail]/Sent Mail"')
        elif mode in ["Read", "Unread", "Custom-Filtered"]:
            imap_server.select()
        if mode == "Unread":
            _, msg_numbers = imap_server.search(None, '(UNSEEN SINCE "' + day_before + '")')
        elif mode == "Read":
            _, msg_numbers = imap_server.search(None, '(SEEN SINCE "' + day_before + '")')
        elif mode == "Custom-Filtered":
            _, msg_numbers = imap_server.search(None, '(UNSEEN SINCE "' 
                + day_before 
                + '" TEXT "' 
                + keyword + '")')
        elif mode == "Sent":
            _, msg_numbers = imap_server.search(None, ('(ALL SINCE "' + day_before + '")'))
        
        i = 0
        email_previews = []  
        
        for message_number in reversed(msg_numbers[0].split()):
            # Body Peek prevents the server from marking email as read after fetching its data
            _, msg = imap_server.fetch(message_number, '(BODY.PEEK[HEADER])')
                
            # Parse the raw email message in to a convenient object
            message = email.message_from_bytes(msg[0][1])
                
            # parse out sender name
            sender = message["from"]
            sender = sender[:(sender.find("<"))]
            # shorten long titles
            title = message["subject"]
            if len(message["subject"]) > 50:
                title = title[:50] + "..."
            # parse date
            date = message["Date"]

            # content for each row, aka email element.
            email_row = [
                put_buttons(["✉️"], 
                    onclick=partial(display_email_content, idx=i)
                ),
                style(put_text(sender),
                    "color:gray"
                ),
                style(put_text(title),
                    "color:gray"
                ),
                style(put_text(date),
                    "color:gray"
                ),
                put_buttons(["⚪"], 
                    onclick=partial(mark_as_read, idx=i)
                ),
                put_buttons(["⚪"], 
                    onclick=partial(move_to_trash, idx=i)
                )

            ]
            email_previews.append(email_row)
            i += 1
        
        # Set up table headers.
        labels = ["Open", "Sender", "Title", "Time", "Mark As Read", "Trash"] 
        
        set_scope("scope")
        display = output()
        with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
            put_scrollable(display, height=300, keep_bottom=True)
        display.append(
            put_text("Folder/" + mode + " - displaying results from the past " + str(time_day) + " day(s)."),
        )
        if mode == "Custom-Filtered":
            display.append(
                put_text("The custom filter displays all unread emails with the keyword 'coupon' in the header or body."))
        display.append(
            put_html("<hr>")
        )
        display.append(
            style(
                put_table(
                    email_previews, 
                    header = labels
                ),
                "color: black; overflow:auto; height:400px; word-break: keep-all"
            )
        )
    
    def display_email_content(dummy, idx):
        '''display email content'''
        
        global msg_numbers
        global msg_requested
        
        msg_number = list(reversed(msg_numbers[0].split()))[int(idx)]
        _, msg = imap_server.fetch(msg_number, '(RFC822)')
        msg_requested = email.message_from_bytes(msg[0][1])
        
        # Updating scope
        display = output()
        with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
            put_scrollable(display, height=300, keep_bottom=True)
        
        # HEADER
        display.append(put_text("Subject: " + msg_requested['subject']))
        display.append(put_text("To: " + msg_requested['to']))
        display.append(put_text("From: " + msg_requested['from']))
        #display.append(put_text("Cc: " + msg_requested['cc']))
        #display.append(put_text("Bcc: " + msg_requested['bcc']))
        #display.append(put_text("Urgency (1 highest 5 lowest): " + msg_requested['x-priority']))
        display.append(put_html("<hr>"))
        
        # BODY
        
        # if the email message is multipart
        if msg_requested.is_multipart():
            # iterate over email parts
            for part in msg_requested.walk():
                # extract content type of email
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                try:
                    # get the email body
                    body = part.get_payload(decode=True).decode()
                except:
                    pass
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    # print text/plain emails and skip attachments
                    display.append(put_text(body))
        else:
            # extract content type of email
            content_type = msg_requested.get_content_type()
            # get the email body
            body = msg_requested.get_payload(decode=True).decode()
            if content_type == "text/plain":
                # print only text email parts
                display.append(put_text(body))
            if content_type == "text/html":
                # if it's HTML, create a new HTML file and open it in browser
                display.append(put_html(body))
        
        # TO DO
        display.append(put_buttons(["reply"], onclick=reply))
        
    def mark_as_read(dummy, idx):
        global msg_numbers
        uid = list(reversed(msg_numbers[0].split()))[int(idx)]
        imap_server.store(uid, '+FLAGS', '\\Seen')
        refresh_display(current_mode)
        
    def move_to_trash(dummy, idx):
        global msg_numbers
        uid = list(reversed(msg_numbers[0].split()))[int(idx)]
        imap_server.store(uid, '+X-GM-LABELS', '\\Trash')
        refresh_display(current_mode)

    def reply(x):
        global msg_requested
        
        # ASKING FOR EMAIL
        email_content = input_group("Reply", [
            textarea(name='Email', help_text='write your email here'),
            actions(name='cmd', buttons=['Send', 'Back'])
        ])
        
        # ORIGINAL HEADER

        subject = msg_requested['subject']
        original_sender = msg_requested['from']
                
        if email_content['cmd'] == 'Send':
            SMTP_HOST = 'smtp.gmail.com'
            SMTP_USER = idpw['login']
            SMTP_PASS = idpw['password']
            to_emails = [original_sender]
            email_message = EmailMessage()
            email_message.add_header('To', ', '.join(to_emails))
            email_message.add_header('From', SMTP_USER)
            email_message.add_header('Subject', 'RE: ' + subject)
            email_message.set_content(email_content['Email'])
                  
            smtp_server = SMTP_SSL('smtp.gmail.com', port=SMTP_SSL_PORT)
            smtp_server.login(SMTP_USER, SMTP_PASS)
            smtp_server.sendmail(SMTP_USER, to_emails, email_message.as_bytes())
            smtp_server.quit()
        if email_content['cmd'] == 'Back':
            pass
        refresh_display(current_mode)

        return x
    def check_timestamp(time):
        if time <= 0:
            return "Number should be greater than 0."
    
    ########################################################
    # INPUT BUTTONS (CHANGE BETWEEN MODES: INBOX, SEND...) #
    ########################################################
    
    refresh_display("Unread")
    
    while logged_in:
        
        data = input_group("Welcome, " + idpw['login'], [
            actions(name='folder', buttons=[ 
                'Unread',
                'Read',
                'Custom-Filtered',
                'Sent'
            ]), 
            #style(
            actions(name='cmd', buttons=[ 
                'Compose',
                {'label': 'Logout', 'type': 'cancel'}
            ])
            #,"background-color:red"
            #)
        ])
        if data is None:
            break
        #######################################
        # OUTPUT: INBOX/UNREAD                #
        #######################################
        if data['folder'] == 'Unread':
            refresh_display("Unread")
            current_mode = "Unread"
        #######################################
        # OUTPUT: INBOX/READ                  #
        #######################################
        if data['folder'] == 'Read':
            refresh_display("Read")
            current_mode = "Read"
        #######################################
        # OUTPUT: INBOX/READ                  #
        #######################################
        if data['folder'] == 'Custom-Filtered':
            refresh_display("Custom-Filtered")
            current_mode = "Custom-Filtered"
        #######################################
        # OUTPUT: SENT                        #
        #######################################
        if data['folder'] == 'Sent':
            #x = str(imap_server.list())
            #await input(x)
            refresh_display("Sent")
            current_mode = "Sent"
        #######################################
        # OUTPUT: COMPOSE                     #
        #######################################
        if data['cmd'] == 'Compose':
            email_content = input_group("Compose", [
                input(name='Subject', help_text="^ Title ^"),
                input(name='Recipient', help_text="^ Recipient Email (Use commas to separate multiple)^"),
                textarea(name='Email', help_text='write your email here'),
                actions(name='cmd', buttons=['Send', 'Back'])
            ])
            if email_content['cmd'] == 'Send':
                SMTP_HOST = 'smtp.gmail.com'
                SMTP_USER = idpw['login']
                SMTP_PASS = idpw['password']
                
                # parsing comma-separated recipient string into list
                to_emails = email_content['Recipient'].replace(" ", "").split(",")
                
                email_message = EmailMessage()
                email_message.add_header('To', ', '.join(to_emails))
                email_message.add_header('From', SMTP_USER)
                email_message.add_header('Subject', email_content['Subject'])
                email_message.set_content(email_content['Email'])
                  
                smtp_server = SMTP_SSL('smtp.gmail.com', port=SMTP_SSL_PORT)
                smtp_server.login(SMTP_USER, SMTP_PASS)
                smtp_server.sendmail(SMTP_USER, to_emails, email_message.as_bytes())
                
                smtp_server.quit()
            if email_content['cmd'] == 'Back':
                pass
            refresh_display(current_mode)
            
    # CLOSE SESSION
    toast("You have successfully logged out.")
