from pywebio import *
from pywebio.output import *
from pywebio.input import *

if __name__ == '__main__':
    '''HTML Code Editor'''
    
    # (1) header
    style(put_text("HTML Editor 💻"), 'text-align:center; font-size:200%, font-color:black')
    
    # (2) output
    set_scope("scope")
    html = output()
    with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
        put_scrollable(html, height=400, keep_bottom=True)
    
    # (3) input
    while True:
        data = input_group('Write Your HTML Code', [
            textarea(name='code', code={
                'mode': "html",
                'theme': 'darcula'
                }),
            actions(name='cmd', buttons=['Run', {'label': 'Exit', 'type': 'cancel'}])
        ])
        if data is None:
            break
        # clearing scope
        html = output()
        with use_scope('scope', clear=True):  # enter the existing scope and clear the previous content
            put_scrollable(html, height=400, keep_bottom=True)
        html.append(put_html(data['code']))
