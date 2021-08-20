from pywebio import *
from pywebio.output import *
from pywebio.input import *
import os
from functools import partial

filenames = []

def main():
    
    while(True):
        set_scope("scope")
        
        # table
        create_table()
        
        # wait to create file
        new_file = input_group("PyWebIO File Manager 📁", [
            input(name='newFile', 
                placeholder='newfile.py', 
                help_text="name your new file and press create, or upload from your local device."
            ),
            actions(name='cmd', buttons=['Create/Refresh', 'Upload', 'Exit'])
        ])

        if new_file['cmd'] == 'Create/Refresh':
            try:
                os.mknod(new_file['newFile'])
            except:
                pass
        elif new_file['cmd'] == 'Upload':
            upload()
        else:
            break
        
def create_table():
    '''displays table'''
    global filenames
    
    filenames = os.listdir()
    display = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=300, keep_bottom=True)
        
    table = []
    for i in range(len(filenames)):
        file_row = [
            put_text(filenames[i]),
            put_buttons(["◀️"], onclick=partial(rename, i=i)),
            put_buttons(["✖️"], onclick=partial(delete, i=i)),
            put_buttons(["🔎"], onclick=partial(view, i=i)),
            put_buttons(["⬇️"], onclick=partial(download, i=i)),
        ]              
        table.append(file_row)
    display.append(
        style(
            put_table(table,
                header=["File", "Rename", "Delete", "View", "Download"]
            ),
            "word-break: keep-all"
        )
    )

def delete(dummy, i):
    '''delete specific file'''
    confirm = actions('⚠️ Are you sure you want to delete ' + filenames[i] + '? ⚠️', ['Yes', 'No'],
                      help_text='WARNING: UNRECOVERABLE AFTER DELETION')
    if confirm == "Yes":
        os.remove(filenames[i])
    create_table()

    
def view(dummy, i):
    '''view contents inside file'''
    f = open(filenames[i], "rb")
    decode = filenames[i].split(".")
    display = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=300, keep_bottom=True)

    display.append(style(put_text(filenames[i]), 'font-size:150%'))
    display.append(put_html("<hr>"))
    
    if decode[1] in ["jpeg", "gif", "png", "jpg"]:
        display.append(put_image(f.read()))
    else:
        display.append(put_text(f.read()))
    f.close()
        
def rename(dummy, i):
    ''''''
    new_name = input("Rename " + filenames[i])
    os.rename(filenames[i], new_name)
    create_table()

def upload():
    ''''''
    set_scope("scope2")
    # need to name each input to make input group to be functional
    new_file = input_group("Upload a file", [
            file_upload("upload", name="file_uploader"),
            actions(name='cmd', buttons=['Upload', 'Exit'])
    ])
    if new_file['cmd'] == 'Upload':
        try:
            fn = new_file["file_uploader"]
            f = open(fn["filename"], "wb")
            f.write(fn["content"])
            f.close()
        except:
            with use_scope('scope2', clear=True):  # enter the existing scope and clear the previous content
                put_error("Choose a file!")
            upload()
    else:
        clear("scope2")
        pass

def download(dummy, i):
    global filenames
    filenames = os.listdir()
    display = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=300, keep_bottom=True)

    table = []
    for j in range(len(filenames)):
        file_row = [
            put_text(filenames[j]),
            put_buttons(["◀️"], onclick=partial(rename, i=j)),
            put_buttons(["✖️"], onclick=partial(delete, i=j)),
            put_buttons(["🔎"], onclick=partial(view, i=j)),
            put_buttons(["⬇️"], onclick=partial(download, i=j)),
        ]              
        table.append(file_row)
    display.append(
        style(
            put_table(table,
                header=["File", "Rename", "Delete", "View", "Download"]
            ),
            "word-break: keep-all"
        )
    )
    
    f = open(filenames[i], "rb")
    display.append(put_file(filenames[i], f.read()))
    f.close()
