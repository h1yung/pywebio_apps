from pywebio import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *

# Import other Python libraries
from urllib import parse

# Import util file with pyweblog classes
import step3_pyweblog_util as pwl

def main():
    '''Blog Writer: Step#3'''

    # Find all blog files in directory
    filenames = pwl.find_blogfiles()
    
    search = eval_js("window.location.search")
    query = {}
    try:
        query = dict(parse.parse_qsl(search.lstrip('?')))
    except:
        query['page'] = None
    
    # If 'x' in ?page=x is an existing filename, display for edit
    if query['page'] in [filename[:-5] for filename in filenames]:
        blog_post = pwl.BlogPost(filepath=query['page'] + ".json")
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
                input(label="Save this post as:", name="saved_as", required=True, validate=pwl.check_illegal_characters)
            ]
        )
            
        # Instantiate BlogPost object and save to local directory
        blog_post = pwl.BlogPost(input_filename=header_input['saved_as'])
        for session in ["title", "thumbnail", "introduction"]:
            post_section = pwl.PostSection(session)
            post_section.add_content(section_content=header_input[session])
            blog_post.add_to_list(post_section)
        blog_post.save_post()
        
        # Switch to the url; next call of this python script leads to rendering (line 31)
        root_url = eval_js("window.location")['href']
        run_js('window.location.href = a;', a=root_url + "?page=" + blog_post.filepath[:-5])

    # Add option to finish editing
    blog_post.get_next_input()


