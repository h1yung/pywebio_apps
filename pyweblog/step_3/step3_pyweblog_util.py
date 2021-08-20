from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *

# Import other Python libraries
from functools import partial
import os
import json
import base64
import re
from datetime import datetime


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
            if self.type in ['thumbnail', 'image']:
                self.content = base64.b64encode(section_content['content']).decode('utf-8')
            else:
                self.content = section_content
        
        # (2) Use default image
        elif self.type in ['thumbnail', 'image'] and not section_scale:
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
        For markdown, parse string as markdown
        For image, do the same as thumbnail, except when the image content exists, consider its scale value and resize accordingly
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
        if self.type == 'markdown':
            put_markdown(self.content)
        if self.type == 'image':
            if self.content is None:
                put_image("https://labzinga-data.s3.us-west-2.amazonaws.com/media/public/pywebio-images/2a223300-a99f-11ea-9dd1-06cba0b1da95.png")
            else:
                put_html(
                    "<center><div style='transform:" 
                    + "scale(" + str(self.scale) + ")'>"
                    + "<img style='width:100%; height:100%' "
                    + "src='data:image/png;base64," + self.content + "'></div></center>"
                )
                
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
                
                if section['type'] in ['thumbnail', 'image']:
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
        Update section content (scale or edit), render post preview after
        When section is not specified (only applicable to PostSections with type 'image'), get the persistant input value of image scale and update it (from self.action_resize)
        When section is specified, update the content
        '''
        
        if section is None:
            self.post_section_list[idx].add_content(section_scale=pin.scale)
        else:
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
                    # Add edit and delete button if it's not a section of the header and not an image
                    if section_ob.type in ['markdown']:
                        put_buttons(
                            [
                                dict(label=["Edit"], value="Edit", color='dark', small=True),
                                dict(label=["Delete"], value="Delete", color='dark', small=True)
                            ], 
                            onclick=partial(self.handle_update, idx=i)
                        )
                    # Add edit, resize, and delete button for images
                    if section_ob.type in ['image']:
                        put_buttons(
                            [
                                dict(label=["Resize"], value="Resize", color='dark', small=True),
                                dict(label=["Edit"], value="Edit", color='dark', small=True),
                                dict(label=["Delete"], value="Delete", color='dark', small=True)
                            ], 
                            onclick=partial(self.handle_update, idx=i)
                        )
    
    def get_next_input(self):
        '''
        Request input for: markdown, image, or finish editing post
        Re-render all the contents before every request loop
        '''
    
        while True:
            self.render(editing_buttons=True)
            
            next_step_input = actions('', 
                ['Markdown', 'Image', 'Finish Editing Post']
            ) 
            
            if next_step_input == 'Markdown':
                self.append_markdown_or_image('markdown')
            if next_step_input == 'Image':
                self.append_markdown_or_image('image')
            if next_step_input == 'Finish Editing Post':
                # Clear post preview
                for i in range(len(self.post_section_list)):
                    clear(str(i))
                put_text("👍")
                break
    
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
    
    @_check_enabled
    def append_markdown_or_image(self, content_type):
        '''
        Request new markdown or image.
        Instantiate a PostSection object and add to content list
        '''
        
        self._edit_enabled = True
                
        if content_type == 'markdown':
            request = input_group("Markdown", [
                textarea('Text', name='markdown'),
                actions(name='cmd', buttons=['Confirm', 'Exit'])
            ])
        if content_type == 'image':
            request = input_group("Image", [
                file_upload("Upload An Image", name='image'),
                actions(name='cmd', buttons=['Confirm', 'Exit'])
            ])
        if request['cmd'] == 'Confirm':
            post_section = PostSection(content_type)
            post_section.add_content(request[content_type])
            self.add_to_list(post_section)
        
        self.finish_editing_section()
                
    
    def finish_editing_section(self):
        '''Unlock out of editing mode of a single section, clear out pin popup'''
        
        close_popup()
        self._edit_enabled = False
    
    def handle_update(self, mode, idx):
        '''Choose function to use based on button type (edit, resize, or delete)'''
        
        if mode == 'Resize':
            self.action_resize(idx)
        if mode == 'Edit':
            self.action_edit(idx)
        if mode == 'Delete':
            self.action_delete(idx)
    
    @_check_enabled
    def action_resize(self, idx):
        '''Handling the resize button for a section'''
        
        # skip resizing if it's the default image
        if self.post_section_list[idx].content is None:
            toast("You cannot resize the default image!")
            return
        
        if self.post_section_list[idx].type == 'image':
            # image scaling with slider
            popup('Resize', closable=False, content=
                [
                    put_slider(label="Scale original dimensions:", 
                        name="scale", 
                        value=self.post_section_list[idx].scale,
                        min_value=0.1, 
                        max_value=1, 
                        step=0.1
                    ),
                    put_buttons(['Confirm', 'Exit Without Saving'], 
                        lambda x: self.update_section(idx) if x == 'Confirm' else self.finish_editing_section())
                ]
            )
        
    @_check_enabled
    def action_edit(self, idx):
        '''Handling the edit button for a section'''
        
        self._edit_enabled = True
        # (1) EDIT markdown section
        if self.post_section_list[idx].type in ['title', 'introduction', 'markdown']:
            popup('Edit', closable=False, content=
                [
                    put_textarea(label="Your new %s:" %self.post_section_list[idx].type, 
                        name="markdown", value=self.post_section_list[idx].content),
                    put_buttons(['Confirm', 'Exit Without Saving'], 
                        lambda x: self.update_section(idx, pin.markdown) if x == 'Confirm' else self.finish_editing_section())
                ]
            )
        # (2) EDIT image section
        if self.post_section_list[idx].type in ['thumbnail', 'image']:
            
            image = input_group("Your new %s" %self.post_section_list[idx].type, [
                file_upload("Upload", name="file", accept=['.jpg','.png','.gif'], help_text="Only accept jpg, gif and png files"),
                actions(name='cmd', buttons=['Upload', 'Exit'])
            ])
            if image['cmd'] == 'Upload' and image['file']:
                self.update_section(idx, image['file'])
            self.finish_editing_section()

    @_check_enabled
    def action_delete(self, idx):
        '''
        Handling the delete button for a section
        Remove section from the section list and then render page
        '''
        
        # clear display
        for i in range(len(self.post_section_list)):
            clear(str(i))
         
        self.post_section_list.pop(idx)
        self.render(editing_buttons=True)
    
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
    pass

