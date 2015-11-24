from __future__ import absolute_import
import json
import logging
import re
import time
import sys
import pprint

from errbot.backends.base import Message, Presence, ONLINE, AWAY, MUCRoom, RoomError, RoomDoesNotExistError, \
    UserDoesNotExistError, Identifier, MUCIdentifier
from errbot.errBot import ErrBot
from errbot.utils import deprecated, PY3, split_string_after
from errbot.rendering import imtext


# Can't use __name__ because of Yapsy
log = logging.getLogger(u'errbot.backends.slack')

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache
try:
    from slackclient import SlackClient
except ImportError:
    log.exception(u"Could not start the Slack back-end")
    log.fatal(
        u"You need to install the slackclient package in order to use the Slack "
        u"back-end. You should be able to install this package using: "
        u"pip install slackclient"
    )
    sys.exit(1)
except SyntaxError:
    if not PY3:
        raise
    log.exception(u"Could not start the Slack back-end")
    log.fatal(
        u"I cannot start the Slack back-end because I cannot import the SlackClient. "
        u"Python 3 compatibility on SlackClient is still quite young, you may be "
        u"running an old version or perhaps they released a version with a Python "
        u"3 regression. As a last resort to fix this, you could try installing the "
        u"latest master version from them using: "
        u"pip install --upgrade https://github.com/slackhq/python-slackclient/archive/master.zip"
    )
    sys.exit(1)


# The Slack client automatically turns a channel name into a clickable
# link if you prefix it with a #. Other clients receive this link as a
# token matching this regex.
SLACK_CLIENT_CHANNEL_HYPERLINK = re.compile(ur'^<#(?P<id>(C|G)[0-9A-Z]+)>$')

# Empirically determined message size limit.
SLACK_MESSAGE_LIMIT = 4096

USER_IS_BOT_HELPTEXT = (
    u"Connected to Slack using a bot account, which cannot manage "
    u"channels itself (you must invite the bot to channels instead, "
    u"it will auto-accept) nor invite people.\n\n"
    u"If you need this functionality, you will have to create a "
    u"regular user account and connect Err using that account. "
    u"For this, you will also need to generate a user token at "
    u"https://api.slack.com/web."
)


class SlackAPIResponseError(RuntimeError):
    u"""Slack API returned a non-OK response"""

    def __init__(self, *args, **kwargs):
        if 'error' in kwargs: error = kwargs['error']; del kwargs['error']
        else: error = u''
        u"""
        :param error:
            The 'error' key from the API response data
        """
        self.error = error
        super(SlackAPIResponseError, self).__init__(*args, **kwargs)


class SlackIdentifier(Identifier):
    u"""
    This class describes a person on Slack's network.
    """

    def __init__(self, sc, userid=None, channelid=None):
        if userid is not None and userid[0] not in (u'U', u'B'):
            raise Exception(u'This is not a Slack user or bot id: %s (should start with U or B)' % userid)

        if channelid is not None and channelid[0] not in (u'D', u'C', u'G'):
            raise Exception(u'This is not a valid Slack channelid: %s (should start with D, C or G)' % channelid)

        self._userid = userid
        self._channelid = channelid
        self._sc = sc

    @property
    def userid(self):
        return self._userid

    @property
    def username(self):
        u"""Convert a Slack user ID to their user name"""
        user = self._sc.server.users.find(self._userid)
        if user is None:
            log.error(u"Cannot find user with ID %s" % self._userid)
            return u"<%s>" % self._userid
        return user.name

    @property
    def channelid(self):
        return self._channelid

    @property
    def channelname(self):
        u"""Convert a Slack channel ID to its channel name"""
        if self._channelid is None:
            return None

        channel = self._sc.server.channels.find(self._channelid)
        if channel is None:
            raise RoomDoesNotExistError(u"No channel with ID %s exists" % self._channelid)
        return channel.name

    @property
    def domain(self):
        return self._sc.server.domain

    # Compatibility with the generic API.
    person = userid
    client = channelid
    nick = username

    # Override for ACLs
    @property
    def aclattr(self):
        # Note: Don't use str(self) here because that will return
        # an incorrect format from SlackMUCOccupant.
        return u"@%s" % self.username

    @property
    def fullname(self):
        u"""Convert a Slack user ID to their user name"""
        user = self._sc.server.users.find(self._userid)
        if user is None:
            log.error(u"Cannot find user with ID %s" % self._userid)
            return u"<%s>" % self._userid
        return user.real_name

    def __unicode__(self):
        return u"@%s" % self.username

    def __str__(self):
        return self.__unicode__()


class SlackMUCOccupant(MUCIdentifier, SlackIdentifier):
    u"""
    This class represents a person inside a MUC.
    """
    room = SlackIdentifier.channelname

    def __unicode__(self):
        return u"#%s/%s" % (self.room, self.username)

    def __str__(self):
        return self.__unicode__()


class SlackBackend(ErrBot):
    def __init__(self, config):
        super(SlackBackend, self).__init__(config)
        identity = config.BOT_IDENTITY
        self.token = identity.get(u'token', None)
        if not self.token:
            log.fatal(
                u'You need to set your token (found under "Bot Integration" on Slack) in '
                u'the BOT_IDENTITY setting in your configuration. Without this token I '
                u'cannot connect to Slack.'
            )
            sys.exit(1)
        self.sc = None  # Will be initialized in serve_once
        self.md = imtext()

    def api_call(self, method, data=None, raise_errors=True):
        u"""
        Make an API call to the Slack API and return response data.

        This is a thin wrapper around `SlackClient.server.api_call`.

        :param method:
            The API method to invoke (see https://api.slack.com/methods/).
        :param raise_errors:
            Whether to raise :class:`~SlackAPIResponseError` if the API
            returns an error
        :param data:
            A dictionary with data to pass along in the API request.
        :returns:
            The JSON-decoded API response
        :raises:
            :class:`~SlackAPIResponseError` if raise_errors is True and the
            API responds with `{"ok": false}`
        """
        if data is None:
            data = {}
        response = json.loads(self.sc.server.api_call(method, **data).decode(u'utf-8'))
        if raise_errors and not response[u'ok']:
            raise SlackAPIResponseError(
                u"Slack API call to %s failed: %s" % (method, response[u'error']),
                error=response[u'error']
            )
        return response

    def serve_once(self):
        self.sc = SlackClient(self.token)
        log.info(u"Verifying authentication token")
        self.auth = self.api_call(u"auth.test", raise_errors=False)
        if not self.auth[u'ok']:
            raise SlackAPIResponseError(error=u"Couldn't authenticate with Slack. Server said: %s" % self.auth[u'error'])
        log.debug(u"Token accepted")
        self.bot_identifier = SlackIdentifier(self.sc, self.auth[u"user_id"])

        log.info(u"Connecting to Slack real-time-messaging API")
        if self.sc.rtm_connect():
            log.info(u"Connected")
            self.reset_reconnection_count()
            try:
                while True:
                    for message in self.sc.rtm_read():
                        self._dispatch_slack_message(message)
                    time.sleep(1)
            except KeyboardInterrupt:
                log.info(u"Interrupt received, shutting down..")
                return True
            except:
                log.exception(u"Error reading from RTM stream:")
            finally:
                log.debug(u"Triggering disconnect callback")
                self.disconnect_callback()
        else:
            raise Exception(u'Connection failed, invalid token ?')

    def _dispatch_slack_message(self, message):
        u"""
        Process an incoming message from slack.

        """
        if u'type' not in message:
            log.debug(u"Ignoring non-event message: %s" % message)
            return

        event_type = message[u'type']

        event_handlers = {
            u'hello': self._hello_event_handler,
            u'presence_change': self._presence_change_event_handler,
            u'team_join': self._team_join_event_handler,
            u'message': self._message_event_handler,
        }

        event_handler = event_handlers.get(event_type)

        if event_handler is None:
            log.debug(u"No event handler available for %s, ignoring this event" % event_type)
            return
        try:
            log.debug(u"Processing slack event: %s" % message)
            event_handler(message)
        except Exception:
            log.exception(u"%s event handler raised an exception" % event_type)

    def _hello_event_handler(self, event):
        u"""Event handler for the 'hello' event"""
        self.connect_callback()
        self.callback_presence(Presence(identifier=self.bot_identifier, status=ONLINE))

    def _presence_change_event_handler(self, event):
        u"""Event handler for the 'presence_change' event"""

        idd = SlackIdentifier(self.sc, event[u'user'])
        presence = event[u'presence']
        # According to https://api.slack.com/docs/presence, presence can
        # only be one of 'active' and 'away'
        if presence == u'active':
            status = ONLINE
        elif presence == u'away':
            status = AWAY
        else:
            log.error(
                u"It appears the Slack API changed, I received an unknown presence type %s" % presence
            )
            status = ONLINE
        self.callback_presence(Presence(identifier=idd, status=status))

    def _team_join_event_handler(self, event):
        self.sc.parse_user_data((event[u'user'],))

    def _message_event_handler(self, event):
        u"""Event handler for the 'message' event"""
        channel = event[u'channel']
        if channel.startswith(u'C'):
            log.debug(u"Handling message from a public channel")
            message_type = u'groupchat'
        elif channel.startswith(u'G'):
            log.debug(u"Handling message from a private group")
            message_type = u'groupchat'
        elif channel.startswith(u'D'):
            log.debug(u"Handling message from a user")
            message_type = u'chat'
        else:
            log.warning(u"Unknown message type! Unable to handle")
            return
        subtype = event.get(u'subtype', None)

        if subtype == u"message_deleted":
            log.debug(u"Message of type message_deleted, ignoring this event")
            return
        if subtype == u"message_changed" and u'attachments' in event[u'message']:
            # If you paste a link into Slack, it does a call-out to grab details
            # from it so it can display this in the chatroom. These show up as
            # message_changed events with an 'attachments' key in the embedded
            # message. We should completely ignore these events otherwise we
            # could end up processing bot commands twice (user issues a command
            # containing a link, it gets processed, then Slack triggers the
            # message_changed event and we end up processing it again as a new
            # message. This is not what we want).
            log.debug(
                u"Ignoring message_changed event with attachments, likely caused "
                u"by Slack auto-expanding a link"
            )
            return

        if u'message' in event:
            text = event[u'message'][u'text']
            user = event[u'message'].get(u'user', event.get(u'bot_id'))
        else:
            text = event[u'text']
            user = event.get(u'user', event.get(u'bot_id'))

        text = re.sub(u"<[^>]*>", self.remove_angle_brackets_from_uris, text)

        log.debug(u"Saw an event: %s" % pprint.pformat(event))

        msg = Message(
            text,
            type_=message_type,
            extras={u'attachments': event.get(u'attachments')})

        # sameroom.io bots don't include user or bot ids, handle this specially
        if subtype == u'bot_message' and not user:
            msg.extras[u'sameroom_bot'] = True
            msg.extras[u'sameroom_username'] = event.get(u'username', None)

        if message_type == u'chat':
            msg.frm = SlackIdentifier(self.sc, user, event[u'channel'])
            msg.to = SlackIdentifier(self.sc, self.username_to_userid(self.sc.server.username),
                                     event[u'channel'])
        else:
            msg.frm = SlackMUCOccupant(self.sc, user, event[u'channel'])
            msg.to = SlackMUCOccupant(self.sc, self.username_to_userid(self.sc.server.username),
                                      event[u'channel'])

        self.callback_message(msg)

    def userid_to_username(self, id_):
        u"""Convert a Slack user ID to their user name"""
        user = [user for user in self.sc.server.users if user.id == id_]
        if not user:
            raise UserDoesNotExistError(u"Cannot find user with ID %s" % id_)
        return user[0].name

    def username_to_userid(self, name):
        u"""Convert a Slack user name to their user ID"""
        user = [user for user in self.sc.server.users if user.name == name]
        if not user:
            raise UserDoesNotExistError(u"Cannot find user %s" % name)
        return user[0].id

    def channelid_to_channelname(self, id_):
        u"""Convert a Slack channel ID to its channel name"""
        channel = [channel for channel in self.sc.server.channels if channel.id == id_]
        if not channel:
            raise RoomDoesNotExistError(u"No channel with ID %s exists" % id_)
        return channel[0].name

    def channelname_to_channelid(self, name):
        u"""Convert a Slack channel name to its channel ID"""
        if name.startswith(u'#'):
            name = name[1:]
        channel = [channel for channel in self.sc.server.channels if channel.name == name]
        if not channel:
            raise RoomDoesNotExistError(u"No channel named %s exists" % name)
        return channel[0].id

    def channels(self, exclude_archived=True, joined_only=False):
        u"""
        Get all channels and groups and return information about them.

        :param exclude_archived:
            Exclude archived channels/groups
        :param joined_only:
            Filter out channels the bot hasn't joined
        :returns:
            A list of channel (https://api.slack.com/types/channel)
            and group (https://api.slack.com/types/group) types.

        See also:
          * https://api.slack.com/methods/channels.list
          * https://api.slack.com/methods/groups.list
        """
        response = self.api_call(u'channels.list', data={u'exclude_archived': exclude_archived})
        channels = [channel for channel in response[u'channels']
                    if channel[u'is_member'] or not joined_only]

        response = self.api_call(u'groups.list', data={u'exclude_archived': exclude_archived})
        # No need to filter for 'is_member' in this next call (it doesn't
        # (even exist) because leaving a group means you have to get invited
        # back again by somebody else.
        groups = [group for group in response[u'groups']]

        return channels + groups

    @lru_cache(50)
    def get_im_channel(self, id_):
        u"""Open a direct message channel to a user"""
        response = self.api_call(u'im.open', data={u'user': id_})
        return response[u'channel'][u'id']

    def send_message(self, mess):
        super(SlackBackend, self).send_message(mess)
        to_humanreadable = u"<unknown>"
        try:
            if mess.type == u'groupchat':
                to_humanreadable = mess.to.username
                to_channel_id = mess.to.channelid
            else:
                to_humanreadable = mess.to.username
                to_channel_id = mess.to.channelid
                if to_channel_id.startswith(u'C'):
                    log.debug(u"This is a divert to private message, sending it directly to the user.")
                    to_channel_id = self.get_im_channel(self.username_to_userid(to_humanreadable))
            log.debug(u'Sending %s message to %s (%s)' % (mess.type, to_humanreadable, to_channel_id))
            body = self.md.convert(mess.body)
            log.debug(u'Message size: %d' % len(body))

            limit = min(self.bot_config.MESSAGE_SIZE_LIMIT, SLACK_MESSAGE_LIMIT)
            parts = self.prepare_message_body(body, limit)

            for part in parts:
                self.sc.rtm_send_message(to_channel_id, part)
        except Exception:
            log.exception(
                u"An exception occurred while trying to send the following message "
                u"to %s: %s" % (to_humanreadable, mess.body)
            )

    def change_presence(self, status = ONLINE, message = u''):
        self.api_call(u'users.setPresence', data={u'presence': u'auto' if status == ONLINE else u'away'})

    @staticmethod
    def prepare_message_body(body, size_limit):
        u"""
        Returns the parts of a message chunked and ready for sending.

        This is a staticmethod for easier testing.

        Args:
            body (str)
            size_limit (int): chunk the body into sizes capped at this maximum

        Returns:
            [str]

        """
        fixed_format = body.startswith(u'```')  # hack to fix the formatting
        parts = list(split_string_after(body, size_limit))

        if len(parts) == 1:
            # If we've got an open fixed block, close it out
            if parts[0].count(u'```') % 2 != 0:
                parts[0] += u'\n```\n'
        else:
            for i, part in enumerate(parts):
                starts_with_code = part.startswith(u'```')

                # If we're continuing a fixed block from the last part
                if fixed_format and not starts_with_code:
                    parts[i] = u'```\n' + part

                # If we've got an open fixed block, close it out
                if part.count(u'```') % 2 != 0:
                    parts[i] += u'\n```\n'

        return parts

    @staticmethod
    def extract_identifiers_from_string(text):
        u"""
        Parse a string for Slack user/channel IDs.

        Supports strings with the following formats::

            <#C12345>
            <@U12345>
            @user
            #channel/user
            #channel

        Returns the tuple (username, userid, channelname, channelid).
        Some elements may come back as None.
        """
        exception_message = (
            u"Unparseable slack identifier, should be of the format `<#C12345>`, `<@U12345>`, "
            u"`@user`, `#channel/user` or `#channel`. (Got `%s`)"
        )
        text = text.strip()

        if text == u"":
            raise ValueError(exception_message % u"")

        channelname = None
        username = None
        channelid = None
        userid = None

        if text[0] == u"<" and text[-1] == u">":
            exception_message = (
                u"Unparseable slack ID, should start with U, B, C, G or D "
                u"(got `%s`)"
            )
            text = text[2:-1]
            if text == u"":
                raise ValueError(exception_message % u"")
            if text[0] in (u'U', u'B'):
                userid = text
            elif text[0] in (u'C', u'G', u'D'):
                channelid = text
            else:
                raise ValueError(exception_message % text)
        elif text[0] == u'@':
            username = text[1:]
        elif text[0] == u'#':
            plainrep = text[1:]
            if u'/' in text:
                channelname, username = plainrep.split(u'/', 1)
            else:
                channelname = plainrep
        else:
            raise ValueError(exception_message % text)

        return username, userid, channelname, channelid

    def build_identifier(self, txtrep):
        u"""
        Build a :class:`SlackIdentifier` from the given string txtrep.

        Supports strings with the formats accepted by
        :func:`~extract_identifiers_from_string`.
        """
        log.debug(u"building an identifier from %s" % txtrep)
        username, userid, channelname, channelid = self.extract_identifiers_from_string(txtrep)

        if userid is not None:
            return SlackIdentifier(self.sc, userid, self.get_im_channel(userid))
        if channelid is not None:
            return SlackIdentifier(self.sc, None, channelid)
        if username is not None:
            userid = self.username_to_userid(username)
            return SlackIdentifier(self.sc, userid, self.get_im_channel(userid))
        if channelname is not None:
            channelid = self.channelname_to_channelid(channelname)
            return SlackMUCOccupant(self.sc, userid, channelid)

        raise Exception(
            u"You found a bug. I expected at least one of userid, channelid, username or channelname "
            u"to be resolved but none of them were. This shouldn't happen so, please file a bug."
        )

    def build_reply(self, mess, text=None, private=False):
        msg_type = mess.type
        response = self.build_message(text)

        response.frm = self.bot_identifier
        response.to = mess.frm
        response.type = u'chat' if private else msg_type

        return response

    def shutdown(self):
        super(SlackBackend, self).shutdown()

    @deprecated
    def join_room(self, room, username=None, password=None):
        return self.query_room(room)

    @property
    def mode(self):
        return u'slack'

    def query_room(self, room):
        u""" Room can either be a name or a channelid """
        if room.startswith(u'C') or room.startswith(u'G'):
            return SlackRoom(channelid=room, bot=self)

        m = SLACK_CLIENT_CHANNEL_HYPERLINK.match(room)
        if m is not None:
            return SlackRoom(channelid=m.groupdict()[u'id'], bot=self)

        return SlackRoom(name=room, bot=self)

    def rooms(self):
        u"""
        Return a list of rooms the bot is currently in.

        :returns:
            A list of :class:`~SlackRoom` instances.
        """
        channels = self.channels(joined_only=True, exclude_archived=True)
        return [SlackRoom(channelid=channel[u'id'], bot=self) for channel in channels]

    def prefix_groupchat_reply(self, message, identifier):
        message.body = u'@{0}: {1}'.format(identifier.nick, message.body)

    def remove_angle_brackets_from_uris(self, match_object):
        if u"://" in match_object.group():
            return match_object.group().strip(u"<>")
        return match_object.group()


class SlackRoom(MUCRoom):
    def __init__(self, name=None, channelid=None, bot=None):
        if channelid is not None and name is not None:
            raise ValueError(u"channelid and name are mutually exclusive")

        if name is not None:
            if name.startswith(u'#'):
                self._name = name[1:]
            else:
                self._name = name
        else:
            self._name = bot.channelid_to_channelname(channelid)

        self._id = None
        self._bot = bot
        self.sc = bot.sc

    def __str__(self):
        return u"#%s" % self.name

    @property
    def _channel(self):
        u"""
        The channel object exposed by SlackClient
        """
        id_ = self.sc.server.channels.find(self.name)
        if id_ is None:
            raise RoomDoesNotExistError(
                u"%s does not exist (or is a private group you don't have access to)" % unicode(self)
            )
        return id_

    @property
    def _channel_info(self):
        u"""
        Channel info as returned by the Slack API.

        See also:
          * https://api.slack.com/methods/channels.list
          * https://api.slack.com/methods/groups.list
        """
        if self.private:
            return self._bot.api_call(u'groups.info', data={u'channel': self.id})[u"group"]
        else:
            return self._bot.api_call(u'channels.info', data={u'channel': self.id})[u"channel"]

    @property
    def private(self):
        u"""Return True if the room is a private group"""
        return self._channel.id.startswith(u'G')

    @property
    def id(self):
        u"""Return the ID of this room"""
        if self._id is None:
            self._id = self._channel.id
        return self._id

    @property
    def name(self):
        u"""Return the name of this room"""
        return self._name

    def join(self, username=None, password=None):
        log.info(u"Joining channel %s" % unicode(self))
        try:
            self._bot.api_call(u'channels.join', data={u'name': self.name})
        except SlackAPIResponseError, e:
            if e.error == u"user_is_bot":
                raise RoomError(u"Unable to join channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)

    def leave(self, reason=None):
        try:
            if self.id.startswith(u'C'):
                log.info(u"Leaving channel %s (%s)" % (unicode(self), self.id))
                self._bot.api_call(u'channels.leave', data={u'channel': self.id})
            else:
                log.info(u"Leaving group %s (%s)" % (unicode(self), self.id))
                self._bot.api_call(u'groups.leave', data={u'channel': self.id})
        except SlackAPIResponseError, e:
            if e.error == u"user_is_bot":
                raise RoomError(u"Unable to leave channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)
        self._id = None

    def create(self, private=False):
        try:
            if private:
                log.info(u"Creating group %s" % unicode(self))
                self._bot.api_call(u'groups.create', data={u'name': self.name})
            else:
                log.info(u"Creating channel %s" % unicode(self))
                self._bot.api_call(u'channels.create', data={u'name': self.name})
        except SlackAPIResponseError, e:
            if e.error == u"user_is_bot":
                raise RoomError(u"Unable to create channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)

    def destroy(self):
        try:
            if self.id.startswith(u'C'):
                log.info(u"Archiving channel %s (%s)" % (unicode(self), self.id))
                self._bot.api_call(u'channels.archive', data={u'channel': self.id})
            else:
                log.info(u"Archiving group %s (%s)" % (unicode(self), self.id))
                self._bot.api_call(u'groups.archive', data={u'channel': self.id})
        except SlackAPIResponseError, e:
            if e.error == u"user_is_bot":
                raise RoomError(u"Unable to archive channel. " + USER_IS_BOT_HELPTEXT)
            else:
                raise RoomError(e)
        self._id = None

    @property
    def exists(self):
        channels = self._bot.channels(joined_only=False, exclude_archived=False)
        return len([c for c in channels if c[u'name'] == self.name]) > 0

    @property
    def joined(self):
        channels = self._bot.channels(joined_only=True)
        return len([c for c in channels if c[u'name'] == self.name]) > 0

    @property
    def topic(self):
        if self._channel_info[u'topic'][u'value'] == u'':
            return None
        else:
            return self._channel_info[u'topic'][u'value']

    @topic.setter
    def topic(self, topic):
        if self.private:
            log.info(u"Setting topic of %s (%s) to '%s'" % (unicode(self), self.id, topic))
            self._bot.api_call(u'groups.setTopic', data={u'channel': self.id, u'topic': topic})
        else:
            log.info(u"Setting topic of %s (%s) to '%s'" % (unicode(self), self.id, topic))
            self._bot.api_call(u'channels.setTopic', data={u'channel': self.id, u'topic': topic})

    @property
    def purpose(self):
        if self._channel_info[u'purpose'][u'value'] == u'':
            return None
        else:
            return self._channel_info[u'purpose'][u'value']

    @purpose.setter
    def purpose(self, purpose):
        if self.private:
            log.info(u"Setting purpose of %s (%s) to '%s'" % (unicode(self), self.id, purpose))
            self._bot.api_call(u'groups.setPurpose', data={u'channel': self.id, u'purpose': purpose})
        else:
            log.info(u"Setting purpose of %s (%s) to '%s'" % (unicode(self), self.id, purpose))
            self._bot.api_call(u'channels.setPurpose', data={u'channel': self.id, u'purpose': purpose})

    @property
    def occupants(self):
        members = self._channel_info[u'members']
        return [SlackMUCOccupant(self.sc, self._bot.userid_to_username(m), self._name) for m in members]

    def invite(self, *args):
        users = dict((user[u'name'], user[u'id']) for user in self._bot.api_call(u'users.list')[u'members'])
        for user in args:
            if user not in users:
                raise UserDoesNotExistError(u"User '%s' not found" % user)
            log.info(u"Inviting %s into %s (%s)" % (user, unicode(self), self.id))
            method = u'groups.invite' if self.private else u'channels.invite'
            response = self._bot.api_call(
                method,
                data={u'channel': self.id, u'user': users[user]},
                raise_errors=False
            )

            if not response[u'ok']:
                if response[u'error'] == u"user_is_bot":
                    raise RoomError(u"Unable to invite people. " + USER_IS_BOT_HELPTEXT)
                elif response[u'error'] != u"already_in_channel":
                    raise SlackAPIResponseError(error=u"Slack API call to %s failed: %s" % (method, response[u'error']))
