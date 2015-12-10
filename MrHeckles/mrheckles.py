# This is a skeleton for Err plugins, use this to get started quickly.

from errbot import BotPlugin, botcmd
#from errbot.builtins.webserver import webhook

import socket, re, unidecode, sys

hecklechat = 'heckleproxy'
host = 'localhost'
port = 8000
size = 1024
hecklesocket = None

def socket_reconnect(fromname, msgbody):
    global hecklesocket
    try:
        hecklesocket.close()
    except:
        pass
    hecklesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        hecklesocket.connect((host,port))
    except:
        pass
    else:
        try:
            hecklesocket.send('{}{}'.format(fromname, msgbody))
        except:
            pass
        else:
            try:
                data = hecklesocket.recv(size)
            except:
                pass
            else:
                print '{{"start": {}, "text": "{}{}"}}'.format(data, fromname, msgbody)

socket_reconnect('<Mr. Heckles> ', 'Ready!')

class MrHeckles(BotPlugin):
    """An Err plugin skeleton"""
    min_err_version = '1.6.0' # Optional, but recommended
    max_err_version = '3.2.2' # Optional, but recommended

#   def activate(self):
#       """Triggers on plugin activation
#
#       You should delete it if you're not using it to override any default behaviour"""
#       super(Skeleton, self).activate()

#   def deactivate(self):
#       """Triggers on plugin deactivation
#
#       You should delete it if you're not using it to override any default behaviour"""
#       super(Skeleton, self).deactivate()

#   def get_configuration_template(self):
#       """Defines the configuration structure this plugin supports
#
#       You should delete it if your plugin doesn't use any configuration like this"""
#       return {'EXAMPLE_KEY_1': "Example value",
#               'EXAMPLE_KEY_2': ["Example", "Value"]
#              }

#   def check_configuration(self, configuration):
#       """Triggers when the configuration is checked, shortly before activation
#
#       You should delete it if you're not using it to override any default behaviour"""
#       super(Skeleton, self).check_configuration()

#   def callback_connect(self):
#       """Triggers when bot is connected
#
#       You should delete it if you're not using it to override any default behaviour"""
#       pass
    
    def callback_message(self, message):
        """Triggered for every received message that isn't coming from the bot itself
        
        You should delete it if you're not using it to override any default behaviour"""
        
        if message.type == 'groupchat':
            if message.frm.channelname == hecklechat:
                fromname = ''
                msgbody = unidecode.unidecode(message.body)
                fakename = re.split(r'^&lt;(.*)&gt;(.*)', msgbody)
                if len(fakename) == 4:
                    fromname = '<{}> '.format(fakename[1])
                    msgbody = fakename[2].strip()
                elif message.frm.fullname != '<None>':
                    fromname = '<{}> '.format(message.frm.fullname)
                elif 'sameroom_bot' in message.extras:
                    fromname = '<{}> '.format(message.extras['sameroom_username'])
                
                try:
                    hecklesocket.send('{}{}'.format(fromname, msgbody))
                except:
                    socket_reconnect(fromname, msgbody)
                else:
                    try:
                        data = hecklesocket.recv(size)
                    except:
                        pass
                    else:
                        print '{{"start": {}, "text": "{}{}"}}'.format(data, fromname, msgbody)

#   def callback_botmessage(self, message):
#       """Triggered for every message that comes from the bot itself
#
#       You should delete it if you're not using it to override any default behaviour"""
#       pass

#   @webhook
#   def example_webhook(self, incoming_request):
#       """A webhook which simply returns 'Example'"""
#       return "Example"

#   # Passing split_args_with=None will cause arguments to be split on any kind
#   # of whitespace, just like Python's split() does
#   @botcmd(split_args_with=None)
#   def example(self, mess, args):
#       """A command which simply returns 'Example'"""
#       return "Example"
