#This file is identical to step4_renderer.py
#Except for import step5_pyweblog_util instead of step4_pyweblog_util

from pywebio import *
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
from pywebio.platform import * 

# Import other Python libraries
import os
import json
from datetime import datetime
import base64
from urllib import parse

# Import util file with pyweblog classes
import step5_pyweblog_util as pwl

# Define SEO content
blog_name = "My Blog"
blog_desc = "This blog is created with PyWebIO."

def render_frontpage():
    '''
    Render the front page of the blog.
    At the top is the blog name.
    Following are blog posts and their thumbnail, title, 
    date of creation, description, and read more link.
    '''
    
    global blog_name
    
    filenames = pwl.find_blogfiles()

    put_html("<h1>✏️ %s</h1>" %blog_name)
    
    # Parse each JSON blog file in directory for blog post contents
    for filename in filenames:
        with open(filename, "r") as f:
            file_json_content = json.loads(f.read())
        
        # Thumbnail
        thumbnail = "https://labzinga-data.s3.us-west-2.amazonaws.com/media/public/pywebio-images/2a223300-a99f-11ea-9dd1-06cba0b1da95.png"
        if file_json_content['blog_contents'][1]['content']:
            thumbnail = base64.b64decode(file_json_content['blog_contents'][1]['content'])
        style(
            put_image(thumbnail),
            """ 
            height: 200px; 
            padding: 15px 10px;
            display: block;
            """
        )
        # Title and Date of Creation
        dt_obj = datetime.strptime(filename.split('_')[0], '%Y%m%d%H%M%S')
        dt_obj = dt_obj.strftime('%Y/%m/%d')
        style(
            put_text(
                file_json_content['blog_contents'][0]['content'] 
                + " | " 
                + str(dt_obj) 
            ),
            "font-weight: bold"
        )
        # Description
        style(
            put_text(file_json_content['blog_contents'][2]['content']),
            "word-break:normal;"
        )
        # Read more button
        search = eval_js("window.location")
        put_link('read more', search['href'] + '?page=%s' %filename[:-5])
        put_html("<hr>")

@seo(blog_name, blog_desc)
def main():
    '''Blog Writer (Renderer) #4'''

    filenames = pwl.find_blogfiles()
    
    # If the ?page= url contains existing filename, render it. 
    # otherwise, display front page.
    search = eval_js("window.location.search")
    query = {}
    try: 
        query = dict(parse.parse_qsl(search.lstrip('?')))
    except:
        query['page'] = None
    if query['page'] in [filename[:-5] for filename in filenames]:
        blogpost = pwl.BlogPost(filepath=query['page'] + ".json")
        blogpost.render(editing_buttons=False)
    else:
        render_frontpage()
