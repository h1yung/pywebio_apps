from pywebio.input import *
from pywebio.output import *

# Import other Python libraries
import json
import base64
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
        Add content in a section
        Update the content variable if content is given
        Set content to None if content not given and 
        the content type is a thumbnail (use default image)
        Update scale of image if content is not given but scale is
        '''
        
        # (1) Add content
        if section_content:
            if self.type in ['thumbnail']:
                self.content = base64.b64encode(section_content['content']).decode('utf-8')
            else:
                self.content = section_content
        
        # (2) Use default image
        elif self.type in ['thumbnail'] and not section_scale:
            self.content = section_content
        
        # (3) Add scale
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
        
        # initialize from user input & create new file
        if "input_filename" in wargs:
            input_filename = wargs["input_filename"]
            time_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            self.filepath = '_'.join([time_tag, input_filename, 'pwb.json'])
    
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
    '''Blog Writer: Step#1'''

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
    
    # Render post preview
    blog_post.render() 
