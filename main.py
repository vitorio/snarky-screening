import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.logger import Logger

Config.set('graphics', 'width', 800)
Config.set('graphics','height', 400)

from kivy.core.window import Window
kivy.require('1.9.0')
# Logger.setLevel('DEBUG')

from kivy.core.text import LabelBase
KIVY_FONTS = [
    {
        "name": "LucidaFax",
        "fn_regular": "/Users/vitorio/Library/Fonts/Monotype  - Lucida Fax.otf",
        "fn_bold": "/Users/vitorio/Library/Fonts/Monotype  - Lucida Fax Bold.otf",
        "fn_italic": "/Users/vitorio/Library/Fonts/Monotype  - Lucida Fax Italic.otf",
        "fn_bolditalic": "/Users/vitorio/Library/Fonts/Monotype  - Lucida Fax Bold Italic.otf"
    }
]
    
for font in KIVY_FONTS:
    LabelBase.register(**font)

from kivy.garden.desktopvideoplayer import DesktopVideoPlayer

from kivy.garden.scrolllabel import ScrollLabel


from sys import argv

from kivy.support import install_twisted_reactor
install_twisted_reactor()


from twisted.internet import reactor
from twisted.internet import protocol


class EchoProtocol(protocol.Protocol):
    def dataReceived(self, data):
        response = self.factory.app.handle_message(data)
        if response:
            self.transport.write(response)


class EchoFactory(protocol.Factory):
    protocol = EchoProtocol

    def __init__(self, app):
        self.app = app

import re

from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.animation import Animation

kv = """
DesktopVideoPlayer:

    ContextMenuDivider:
        id: snarky_divider

    ContextMenuTextItem:
        id: snarky_opendialog
        text: "Open file"
        on_release: print('hi')
    
    AnchorLayout:
        id: snarky_chatwindow
        anchor_y: 'bottom'
        pos: root.pos
        size_hint: 1, None
        height: dp(200)
        opacity: 1.0
        ScrollLabel:
            id: snarky_chatstream
            font_size: sp(36)
            markup: True
            font_name: 'LucidaFax'
            outline: True
            outline_size: dp(4)
"""

class SimplePlayerApp(App):
    def build(self):
        Config.set('input','mouse', 'mouse,disable_multitouch')

        self.title = 'DesktopVideoPlayer'
        self.root = Builder.load_string(kv)
        
        # self.root.ids.snarky_filechooser.on_submit = self.handle_selection
        
        self.root.remove_widget(self.root.ids.bottom_layout)
        self.root.add_widget(self.root.ids.bottom_layout)
        
        fc = FileChooserIconView()
        fc.on_submit = self.handle_selection
        self.popup = Popup(title='Open file', content=fc)
        self.root.ids.snarky_opendialog.on_release = self.popup.open
        
        self.root.remove_widget(self.root.ids.snarky_divider)
        self.root.remove_widget(self.root.ids.snarky_opendialog)
        self.root.ids._context_menu.add_widget(self.root.ids.snarky_divider)
        self.root.ids._context_menu.add_widget(self.root.ids.snarky_opendialog)

        self.root.ids.snarky_chatstream.text += """
Welcome to a [b]Snarky Screening[/b]!

[i]You[/i] need to kick off [i]auto-scroll[/i] by scrolling this text up so you can see the whole thing.  You'll also need to re-do it if you [i]resize[/i] the window."""
        
        if len(argv) > 1:
            self.root.ids.video.source = argv[1]
        
        reactor.listenTCP(8000, EchoFactory(self))

    def handle_message(self, msg):
        msg = msg.strip(chr(13) + chr(10)) # remove CRLF
        
        msg = re.sub(r"\*(.*)\*", r"[b]\1[/b]", msg)
        msg = re.sub(r"_(.*)_",   r"[i]\1[/i]", msg)
        
        self.root.ids.snarky_chatstream.text += "\n{}".format(msg)
        
        Animation.cancel_all(self.root.ids.snarky_chatwindow)
        self.root.ids.snarky_chatwindow.opacity = 1.0
        anim = Animation(duration=7.0) + Animation(opacity=0.0, duration=3.0)
        anim.start(self.root.ids.snarky_chatwindow)
        
        return str(self.root.ids.video.position)

    def handle_selection(self, selection, touch):
        self.popup.dismiss()
        self.root.ids._context_menu.visible = False
        self.root.ids.video.source = selection[0]
        

if __name__ == '__main__':
    SimplePlayerApp().run()
