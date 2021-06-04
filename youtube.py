from pywebio import *
from pywebio.output import *
from pywebio.input import *
import urllib.request 
import re
import numpy as np
from functools import partial

video_embed_urls = []

def valid_num_results(x):
    if int(x) <= 0:
        return "number of results must be greater than 0."
def watch(dummy_str, link):
    set_scope("scope_2")
    display = output()
    with use_scope('scope_2', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=500, keep_bottom=True)
    display.append(
        put_html(
            '<iframe width="100%" height="400px" src="' + link + '" </iframe>'
        )
    )
    
def main():
    global video_embed_urls
    
    set_scope("scope")
    display = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(display, height=500, keep_bottom=True)
    
    while (True):
        data = input_group("YouTube Video Search 📺", [
            input(name= "Search", placeholder="search a title"),
            input(name= "Num_Results", placeholder="number of results (max 10)", validate=valid_num_results),
            actions(name= "cmd", buttons =["Search", {'label': 'Logout', 'type': 'cancel'}]),
        ])
        if data is None:
            break
        if data["cmd"] == "Search":
            # (1) Input
            search = data["Search"].replace(" ", "+")
            
            num_results = int(data["Num_Results"])
            if num_results > 10:
                num_results = 10
            
            # (2) Query TODO
            html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            video_embed_urls = ["https://www.youtube.com/embed/" + video_ids[i] for i in range(num_results)]
            video_urls = ["https://www.youtube.com/watch\?v=" + video_ids[i] for i in range(num_results)]
            
            # buttons = []
            # for i in range(len(video_embed_urls)):
            #     buttons.append(put_buttons([str(i)], onclick=watch))
            buttons = [put_buttons(["▶"], 
                onclick=partial(watch, link=video_embed_urls[i])) for i in range(len(video_embed_urls))
                ]
            
            video_titles = []
            video_views = []
            video_durations = []
            
            for video_url in video_embed_urls:
                html = urllib.request.urlopen(video_url)
                # html and regex
                title = re.findall(r'CollapsedRenderer\\\":\{\\\"title\\\":\{\\\"runs\\\":\[\{\\\"text\\\":\\\"(.*?)\\\",\\\"navigationEndpoint', html.read().decode())
                title = title[0].replace("\\u0027", "")
                title = title.replace("\\\\u0026", "&")
                # title = title[0].replace("\\u0026", "")
                
                video_titles.append(title)
            for video_url in video_embed_urls:
                html = urllib.request.urlopen(video_url)
                # html and regex  
                views = re.findall(r'subtitle\\\":\{\\\"runs\\\":\[\{\\\"text\\\":\\\"(.*) views', html.read().decode())
                video_views.append(views[0])
            for video_url in video_embed_urls:
                html = urllib.request.urlopen(video_url)
                # html and regex     
                duration = re.findall(r'videoDurationSeconds\\\":\\\"(.*?)\\\",\\\"webPlayerActions', html.read().decode())
                duration[0] = int(duration[0])
                if duration[0] >= 60:
                    minute = int(duration[0] / 60)
                    second = duration[0] % 60
                    # if minute >= 60:
                    #     hour = int(minute / 60)
                    #     minute = minute % 60
                    if duration[0] >= 3600:
                        hour = int(minute / 60)
                        minute = minute % 60
                        video_durations.append(str(hour) + ":" + str(minute).zfill(2) + ":" + str(second).zfill(2))
                    else:
                        video_durations.append(str(minute).zfill(2) + ":" + str(second).zfill(2))
                else:
                    video_durations.append("0:" + str(second))

            
            matrix_t = list(np.transpose([buttons, video_titles, video_views, video_durations]))
            
            set_scope("scope")
            display = output()
            with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
                put_scrollable(display, height=500, keep_bottom=True)
            # (3.1) List of videos to choose from
                title_shortened = search
                if len(title) > 50:
                    title_shortened = search[:50] + "..."
            display.append(
                put_grid([
                    [style(put_image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Logo_of_YouTube_%282015-2017%29.svg/1280px-Logo_of_YouTube_%282015-2017%29.svg.png"),
                        "width:100px;"
                    )],
                    [style(put_text("Top " + str(num_results) + " results for: " + data["Search"]), 
                        "font-size:80%;")]
                ], direction="column")
            )
            display.append(put_html("<hr>"))
            display.append(
                style(
                    put_table(
                        matrix_t, 
                        header=[
                            'Watch',
                            'Title',
                            'Views',
                            'Duration'
                        ]
                    ),
                        "border: 1px solid black; color: black; overflow:auto; height:400px; word-break: keep-all"
                )
            )
        
    # put_html(
    #     '<iframe width="100%" height="400px" src="https://www.youtube.com/embed/YQHsXMglC9A" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
    # )

    
    

from pywebio.platform.flask import start_server

start_server(main, debug=False, port=49977, cdn=True)
