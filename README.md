# snarky-screening
Show snarky comments from a chatroom over a video, for your own heckle screenings.

Built on [Errbot](http://errbot.io) and [Kivy](http://kivy.org), plus [Sameroom](https://sameroom.io/) for chat services which don't support bots (like Skype).

Written in 2015 by [Vitorio Miliano](http://vitor.io/).

## MrHeckles
Errbot bot that relays anything said in a chat room to a local socket.

To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.

You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

## SlackSameroom
Errbot backend which adds additional event data to support Sameroom-relayed messages in Slack.

Slightly modified from the standard Errbot backend for Slack, and so licensed GPLv3.

## test06.py
Kivy-based video player which accepts text provided over a local socket and displays it at the next-nearest second.

Based on the Kivy examples, and so licensed MIT.