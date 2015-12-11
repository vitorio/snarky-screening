# snarky-screening
Show snarky comments from a chatroom over a video, for your own heckle screenings.

Built on [Errbot](http://errbot.io) and [Kivy](http://kivy.org), plus [Sameroom](https://sameroom.io/) for chat services which don't support bots (like Skype).

Written in 2015 by [Vitorio Miliano](http://vitor.io/).

## Running on Mac OS X

Tested only on OS X 10.10 Yosemite and OS X 10.11 El Capitan.  Packaging the Kivy video player into a standalone app works, but I haven't been able to work out packaging up MrHeckles with either py2app or PyInstaller.  Also I'm not sure the best way to pull down unreleased versions of Kivy so you get the nice outlines before 1.9.2+.  Issues or pull requests welcome.

- Install Kivy per [their OS X instructions](http://kivy.org/docs/installation/installation-osx.html).
- Open Terminal.
- `git clone https://github.com/vitorio/snarky-screening.git`
- `cd snarky-screening`
- Create an errbot `config.py` configuration file [per their instructions](http://errbot.io/user_guide/setup.html#configuration).  `BOT_DATA_DIR`, `BOT_EXTRA_PLUGIN_DIR` and `BOT_EXTRA_BACKEND_DIR` can all be set to `'.'`.  If you're using Sameroom to relay from unsupported chat services into Slack, set `BACKEND` to `'SlackSameroom'`.
- `easy_install --user pip`
- `~/Library/Python/2.7/bin/pip install --user 3to2 six slackclient errbot unidecode`
- `~/Library/Python/2.7/bin/pip install -I --user six`
- `~/Library/Python/2.7/bin/pip install --user --upgrade pygments jinja2 requests pyopenssl`
- `ln -s /Applications/Kivy.app/Contents/Resources/script kivy`
- `./kivy -m pip install twisted requests kivy-garden==0.1.2`
- `ln -s /Applications/Kivy.app/Contents/Resources/venv/bin/garden`
- `./garden install --app recycleview`
- `./garden install --app scrolllabel`
- `./garden install --app desktopvideoplayer`
- Then, in one Terminal, `./kivy main.py` to start the video player, Escape exits.
- Open a second Terminal or tab and `~/Library/Python/2.7/bin/errbot` to start the bot, Ctrl-C exits.

## MrHeckles
Errbot bot that relays anything said in a chat room to a local socket.  Depends on unidecode, available through PyPI.  Errbot depends on 3to2, slackclient, and recent versions of six, pygments, jinja2, requests, and pyopenssl, all available through PyPI.

To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.

You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

## SlackSameroom
Errbot backend which adds additional event data to support Sameroom-relayed messages in Slack.

Slightly modified from the standard Errbot backend for Slack, and so licensed GPLv3.

## main.py
Kivy-based video player which accepts text provided over a local socket and displays it on an ongoing basis, fading out after ten seconds.

This uses [Twisted](http://kivy.org/docs/guide/other-frameworks.html), [ScrollLabel](https://github.com/kivy-garden/garden.scrolllabel) and [DesktopVideoPlayer](https://github.com/kivy-garden/garden.desktopvideoplayer) from the garden.  ScrollLabel depends on [RecycleView](https://github.com/kivy-garden/garden.recycleview).  At this time, you'll also need a patched Kivy `_text_sdl2` and a patched ScrollLabel if you want nice outlines like these (or wait until Kivy 1.9.2+):

![Nice outlines only supported by SDL2](http://i.imgur.com/JAoqAYr.png)

Based on the Kivy examples, and so licensed MIT.

## snarkyscreenshots.py
`MrHeckles` logs chat statements in a Kivy [VideoPlayerAnnotation](http://kivy.org/docs/api-kivy.uix.videoplayer.html)-style format.

You can compile these into a proper JSON file, and pass it along with the original movie you screened, and this will generate screenshots of the film with each statement overlaid onto them.

Same dependencies as `main.py`.

Based on the Kivy examples, and so licensed MIT.
