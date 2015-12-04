import kivy
kivy.require('1.2.0')

from sys import argv
from os.path import dirname, join
from kivy.app import App
from kivy.uix.videoplayer import VideoPlayer, VideoPlayerAnnotation

#check what formats are supported for your targetted devices
#for example try h264 video and acc audo for android using an mp4
#container

# install_twisted_rector must be called before importing  and using the reactor
from kivy.support import install_twisted_reactor
install_twisted_reactor()


from twisted.internet import reactor
from twisted.internet import protocol

from kivy.uix.label import Label

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

import math

class VideoPlayerApp(App):
    video = None

    def build(self):
        if len(argv) > 1:
            filename = argv[1]
        else:
            curdir = dirname(__file__)
            filename = join(curdir, 'softboy.mpg')
            
        reactor.listenTCP(8000, EchoFactory(self))
        
        self.video = VideoPlayer(source=filename)
        
        return self.video

    def handle_message(self, msg):
        displaypos = int(math.ceil(self.video.position))
        self.video._annotations_labels.append(
            VideoPlayerAnnotation(annotation={
                'start': displaypos, 'duration': 5, 'text': msg, 'font_name': 'LucidaFax', 'font_size': 36}))

        return str(displaypos)

class EchoProtocol(protocol.Protocol):
    def dataReceived(self, data):
        response = self.factory.app.handle_message(data)
        if response:
            self.transport.write(response)


class EchoFactory(protocol.Factory):
    protocol = EchoProtocol

    def __init__(self, app):
        self.app = app


if __name__ == '__main__':
    VideoPlayerApp().run()
