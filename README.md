# snarky-screening
Show snarky comments from a chatroom over a video, for your own heckle screenings.

Built on [Errbot](http://errbot.io) and [Kivy](http://kivy.org), plus [Sameroom](https://sameroom.io/) for chat services which don't support bots (like Skype).

Written in 2015 by [Vitorio Miliano](http://vitor.io/).

## MrHeckles
Errbot bot that relays anything said in a chat room to a local socket.  Depends on unidecode, available through PyPI.  Errbot depends on 3to2, slackclient, and recent versions of six, pygments, jinja2, requests, and pyopenssl, all available through PyPI.

To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.

You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

## SlackSameroom
Errbot backend which adds additional event data to support Sameroom-relayed messages in Slack.

Slightly modified from the standard Errbot backend for Slack, and so licensed GPLv3.

## main.py
Kivy-based video player which accepts text provided over a local socket and displays it on an ongoing basis, fading out after ten seconds.

This uses [Twisted](http://kivy.org/docs/guide/other-frameworks.html), [ScrollLabel](https://github.com/kivy-garden/garden.scrolllabel) and [DesktopVideoPlayer](https://github.com/kivy-garden/garden.desktopvideoplayer) from the garden.  ScrollView depends on [RecycleView](https://github.com/kivy-garden/garden.recycleview).  At this time, you'll also need a patched Kivy `_text_sdl2` and a patched ScrollLabel if you want nice outlines like these (or wait until Kivy 1.9.2+):

![Nice outlines only supported by SDL2](http://i.imgur.com/JAoqAYr.png)

Based on the Kivy examples, and so licensed MIT.

## snarkyscreenshots.py
`MrHeckles` logs chat statements in a Kivy [VideoPlayerAnnotation](http://kivy.org/docs/api-kivy.uix.videoplayer.html)-style format.

You can compile these into a proper JSON file, and pass it along with the original movie you screened, and this will generate screenshots of the film with each statement overlaid onto them.

Same dependencies as `main.py`.

Based on the Kivy examples, and so licensed MIT.
