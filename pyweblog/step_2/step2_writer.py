from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *
from pywebio.session import *

# Import other Python libraries
from functools import partial
import os
import json
import base64
import re
from datetime import datetime
from urllib import parse

class PostSection:
    ''' 
    PostSection class contains data for a single section of a blog post. 
    Every PostSection object is instantiated with section_type, a string 
    like 'title', 'thumbnail', 'introduction', etc.
    They also have a default 'scale' variable which determines the relative
    size of images.
    '''
    
    def __init__(self, section_type):
        self.type = section_type # title, thumbnail
        self.scale = 1 # image scale
      
    def add_content(self, section_content=None, section_scale=None):
        '''
        Add, scale, or edit content in a section
        Update the content variable if content is given
        Set content to None if content and scale is not given and 
        the content type is an image or thumbnail (use default image)
        Update scale of image if content is not given but scale is
        '''
        
        # (1) Add / edit content
        if section_content:
            if self.type in ['thumbnail']:
                self.content = base64.b64encode(section_content['content']).decode('utf-8')
            else:
                self.content = section_content
        
        # (2) Use default image
        elif self.type in ['thumbnail'] and not section_scale:
            self.content = section_content
        
        # (3) Add / edit scale
        if section_scale:
            self.scale = section_scale
        
    def render(self):
        '''
        Render individual post section to display as part of a blog.
        Different rendering methods for different types of section.
        For title, display a string in h1 style using markdown syntax
        For thumbnail, put image (if missing, add in default image)
        For introduction, add introduction header in h2 style and parse string as markdown
        '''
        
        if self.type == 'title':
            put_markdown('# ' + self.content)
        if self.type == 'thumbnail':
            if self.content is None:
                put_image("https://labzinga-data.s3.us-west-2.amazonaws.com/media/public/pywebio-images/2a223300-a99f-11ea-9dd1-06cba0b1da95.png")
            else:
                put_image(base64.b64decode(self.content))
        if self.type == 'introduction': 
            put_markdown('## Introduction')
            put_markdown(self.content)
        
    
class BlogPost:
    '''
    BlogPost class contains a list of PostSections objects, 
    methods that add, modify and render a blog post
    '''
    
    def __init__(self,**wargs):
        self._edit_enabled = False # Enable editing of one section at a time to avoid stacking of edit requests
        self.post_section_list = [] # List of PostSections
        
        # initialize BlogPost from preexisting file
        if "filepath" in wargs:
            filepath = wargs["filepath"]
            self.filepath = filepath
            
            with open(filepath, "r") as f:
                file_json_content = json.loads(f.read())
            
            # add content and scale value to postsection; 
            # append the postsection object to blogpost list
            for section in file_json_content['blog_contents']:
                postsection = PostSection(section['type'])
                
                if section['type'] in ['thumbnail']:
                    if section['content'] is None:
                        postsection.add_content(section_content = None)
                    else:
                        postsection.add_content(section_content = {'content':base64.b64decode(section['content'])})
                else:
                    postsection.add_content(section_content = section['content'])
                        
                postsection.add_content(section_scale = section['scale'])
                self.add_to_list(postsection)
        
        # initialize from user input & create new file
        if "input_filename" in wargs:
            input_filename = wargs["input_filename"]
            time_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            self.filepath = '_'.join([time_tag, input_filename, 'pwb.json'])
            
    def update_section(self, idx, section=None):
        '''
        Update section content (edit), render post preview after
        When section is specified, update the content
        '''
        
        self.post_section_list[idx].add_content(section_content=section)
        self.render(editing_buttons=True) # render new updates
        self.save_post() # Save file to local directory
        self.finish_editing_section() # indicate end of editing
        
    
    def add_to_list(self, post_section):
        '''Add new section to post'''
        
        self.post_section_list.append(post_section)

    def save_post(self):
        '''Saving post to local directory'''
        
        json_string = json.dumps({'blog_contents':[ob.__dict__ for ob in self.post_section_list]})
        with open(self.filepath, "w") as f:
            f.write(json_string)
    
    def render(self, editing_buttons=False):
        '''Render all the post contents, either with edit button or not'''
        
        for i, section_ob in enumerate(self.post_section_list): # iterate through all post sections
            with use_scope(str(i), clear=True):
                section_ob.render() # render a single content
                if editing_buttons is True:
                    # Add delete button if it's a section of the header
                    if section_ob.type in ["title", "introduction", "thumbnail"]:
                        put_buttons(
                            [
                                dict(label=["Edit"], value="Edit", color='dark', small=True)
                            ], 
                            onclick=partial(self.handle_update, idx=i)
                        )

    def get_next_input(self):
        '''Request input for next step (finish editing) along with render()'''
        
        self.render(editing_buttons=True)
            
        next_step_input = actions('', 
            ['Finish Editing Post']
        )
        if next_step_input == 'Finish Editing Post':
            # Clear post preview
            for i in range(len(self.post_section_list)):
                clear(str(i))
            put_text("👍")
    
    def _check_enabled(func):
        '''
        Wrapper function used as decorator.
        Only 1 scope is allowed to be edited at one time. 
        Lock in on one section (prevents stacks of input dialogs)
        '''
        
        def check(self, *args):
            if self._edit_enabled:
                toast("You may only edit one section at a time.")
                return
            func(self, *args)
        return check
        
    def finish_editing_section(self):
        '''Unlock out of editing mode of a single section, clear out pin popup'''
        
        close_popup()
        self._edit_enabled = False
    
    def handle_update(self, mode, idx):
        '''Choose function to use based on button type (edit)'''
        
        if mode == 'Edit':
            self.action_edit(idx)
    
    @_check_enabled
    def action_edit(self, idx):
        '''Handling the edit button for a section'''
        
        self._edit_enabled = True
        # (1) EDIT markdown section
        if self.post_section_list[idx].type in ['title', 'introduction']:
            popup('Edit', closable=False, content=
                [
                    put_textarea(label="Your new %s:" %self.post_section_list[idx].type, 
                        name="markdown", value=self.post_section_list[idx].content),
                    put_buttons(['Confirm', 'Exit Without Saving'], 
                        lambda x: self.update_section(idx, pin.markdown) if x == 'Confirm' else self.finish_editing_section())
                ]
            )
        # (2) EDIT image section
        if self.post_section_list[idx].type in ['thumbnail']:
            
            image = input_group("Your new %s" %self.post_section_list[idx].type, [
                file_upload("Upload", name="file", accept=['.jpg','.png','.gif'], help_text="Only accept jpg, gif and png files"),
                actions(name='cmd', buttons=['Upload', 'Exit'])
            ])
            if image['cmd'] == 'Upload' and image['file']:
                self.update_section(idx, image['file'])
            self.finish_editing_section()

def find_blogfiles():
    '''Find all _pwb.json files in a directory'''
    
    r = re.compile(r".+_pwb\.json")
    filepaths = os.listdir()
    filepaths = list(filter(r.match, filepaths))
    filepaths = sorted(filepaths, reverse=True)
    return filepaths
    
def check_illegal_characters(s):
    '''Check if string contains illegal characters'''

    illegal_characters = [
        ':', '/', '?', '#', '[', ']', '@', 
        '!', '$', '&', '"', "'", '(', ')', 
        '*', '+', ',', ';', '=', '<', '>', '%', 
        '{', '}', '|', '\\', '^', '`'
    ]
    
    for character in illegal_characters:
        if character in s:
            return("contains illegal character!")
    # space or empty string       
    if (s.isspace()) or (s == "") or (" " in s):
        return('file name cannot be empty or contain spaces')

def main():
    '''Blog Writer: Step #2'''

    # Find all blog files in directory
    filenames = find_blogfiles()
    
    search = eval_js("window.location.search")
    query = {}
    try:
        query = dict(parse.parse_qsl(search.lstrip('?')))
    except:
        query['page'] = None
    
    # If 'x' in ?page=x is an existing filename, display for edit
    if query['page'] in [filename[:-5] for filename in filenames]:
        blog_post = BlogPost(filepath=query['page'] + ".json")
        blog_post.render(editing_buttons=True)
    # If not, ask to create new blog 
    else:
        choice = actions('✏️ Blog Writer', 
            ['Start New', 'Quit']
        )
        if choice == 'Quit': return
        
        # Ask for new blog header
        header_input = input_group("✏️ Start New Post",
            [
                # title: position 0 in blog_contents
                input(label="Blog Post Title:", name="title", required=True),
                # thumbnail: position 1 in blog_contents
                file_upload(label="Thumbnail:", name="thumbnail", accept=['.jpg','.png','.gif'], help_text="Optional. 2:1 Width to Height Suggested. Only accept jpg, gif and png files"),
                # introduction: position 2 in blog_contents
                textarea(label="Introduction:", name="introduction", help_text="Give readers a taste of what this blog post is about.", required=True),
                input(label="Save this post as:", name="saved_as", required=True, validate=check_illegal_characters)
            ]
        )
            
        # Instantiate BlogPost object and save to local directory
        blog_post = BlogPost(input_filename=header_input['saved_as'])
        for session in ["title", "thumbnail", "introduction"]:
            post_section = PostSection(session)
            post_section.add_content(section_content=header_input[session])
            blog_post.add_to_list(post_section)
        blog_post.save_post()
        
        # Switch to the url; next call of this python script leads to rendering (line 31)
        root_url = eval_js("window.location")['href']
        run_js('window.location.href = a;', a=root_url + "?page=" + blog_post.filepath[:-5])

    # Add option to finish editing
    blog_post.get_next_input()
