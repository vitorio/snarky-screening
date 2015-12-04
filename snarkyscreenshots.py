import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.logger import Logger
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.garden.desktopvideoplayer import DesktopVideoPlayer
from kivy.garden.scrolllabel import ScrollLabel
from kivy.clock import Clock

from sys import argv
import os.path
import json
import time

Config.set('graphics', 'width', 800)
Config.set('graphics','height', 400)

kivy.require('1.9.0')
# Logger.setLevel('DEBUG')

UseLucidaFax = False
if os.path.exists(os.path.join(os.path.expanduser('~'), 'Library/Fonts/Monotype  - Lucida Fax.otf')):
    KIVY_FONTS = [
        {
            "name": "LucidaFax",
            "fn_regular": os.path.join(os.path.expanduser('~'), 'Library/Fonts/Monotype  - Lucida Fax.otf'),
            "fn_bold": os.path.join(os.path.expanduser('~'), 'Library/Fonts/Monotype  - Lucida Fax Bold.otf'),
            "fn_italic": os.path.join(os.path.expanduser('~'), 'Library/Fonts/Monotype  - Lucida Fax Italic.otf'),
            "fn_bolditalic": os.path.join(os.path.expanduser('~'), 'Library/Fonts/Monotype  - Lucida Fax Bold Italic.otf')
        }
    ]
    for font in KIVY_FONTS:
        LabelBase.register(**font)
    UseLucidaFax = True

kv = """
DesktopVideoPlayer:
    volume_muted: True

    AnchorLayout:
        id: snarky_chatwindow
        anchor_y: 'bottom'
        pos: root.pos
        size_hint: 1, None
        height: dp(160)
        opacity: 1.0
        ScrollLabel:
            id: snarky_chatstream
            font_size: sp(36)
            markup: True
            outline: True
            outline_size: dp(4)
"""

class SnarkyScreenshotsApp(App):
    def build(self):
        Config.set('input','mouse', 'mouse,disable_multitouch')

        self.title = 'Snarky Screenshots'
        self.root = Builder.load_string(kv)
        
        self.root.remove_widget(self.root.ids.bottom_layout)
        
        if len(argv) > 2:
            self.root.ids.video.source = argv[1]
            if os.path.exists(argv[2]):
                with open(argv[2], 'r') as fd:
                    self.quotes = json.load(fd)

            Clock.schedule_once(self.on_loaded, 5)

    def on_loaded(self, dt):
        if self.root.ids.video.duration != -1:
            if self.quotes:
                quote = self.quotes.pop(0)
                print quote
                self.root.ids.snarky_chatstream.text = "{}".format(quote['text'])
                self.root.ids.video.seek(float(quote['start']) / self.root.ids.video.duration)
                Clock.schedule_once(self.on_seeked, -1)
        else:
            Clock.schedule_once(self.on_loaded, 5)

    def on_seeked(self, dt):
        self.root.ids.video.state = 'pause'
        Clock.schedule_once(self.on_paused, 1)

    def on_paused(self, dt):
        print str(self.root.ids.video.position)
        Window.screenshot()
        self.root.ids.video.state = 'play'
        Clock.schedule_once(self.on_loaded, 1)

if __name__ == '__main__':
    SnarkyScreenshotsApp().run()
