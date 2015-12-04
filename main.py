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


from kivy.garden.desktopvideoplayer import DesktopVideoPlayer

from kivy.garden.scrolllabel import ScrollLabel

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




kv = """
DesktopVideoPlayer:
    source: "/Users/vitorio/Downloads/big_buck_bunny_720p_50mb.mp4"

    AnchorLayout:
        id: chat_window
        anchor_y: 'bottom'
        pos: root.pos
        size_hint: 1, None
        height: 200
        ScrollLabel:
            id: sl
            font_size: sp(36)
            markup: True
"""

class SimplePlayerApp(App):
    def build(self):
        Config.set('input','mouse', 'mouse,disable_multitouch')
        Window.bind(on_filedrop=self.file_drop)
        self.title = 'DesktopVideoPlayer'
        self.root = Builder.load_string(kv)
        
        self.root.remove_widget(self.root.ids.bottom_layout)
        self.root.add_widget(self.root.ids.bottom_layout)
        
        self.root.ids.sl.text += """
Welcome to a Snarky Screening!

You need to kick off auto-scroll by scrolling this text up so you can see the whole thing.  You'll also need to re-do it if you resize the window."""
        
        reactor.listenTCP(8000, EchoFactory(self))
#        return Builder.load_string(kv)

    def file_drop(self, filename, *args):
        print(filename)

    def handle_message(self, msg):
        msg = msg.strip(chr(13) + chr(10)) # remove CRLF
        self.root.ids.sl.text += "\n[color=#bfd0ff]received: %s[/color]" % msg

        if msg == "ping":
            msg = "pong"
        if msg == "plop":
            msg = "kivy rocks"
        self.root.ids.sl.text += "\n[color=#e9ae9e]responded: %s[/color]" % msg

#        return msg

if __name__ == '__main__':
    SimplePlayerApp().run()
