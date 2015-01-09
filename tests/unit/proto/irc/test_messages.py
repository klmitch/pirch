# Copyright (C) 2015 by Kevin L. Mitchell <klmitch@mit.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

import unittest

import mock

from pirch.proto.irc import messages
from pirch import util


class ArgSplitTest(unittest.TestCase):
    def test_base(self):
        result = list(messages._argsplit(b'this  is    a  test  '))

        self.assertEqual(result, [b'this', b'is', b'a', b'test'])

    def test_minimal(self):
        result = list(messages._argsplit(b'this is a test'))

        self.assertEqual(result, [b'this', b'is', b'a', b'test'])

    def test_sentinel(self):
        result = list(messages._argsplit(b'this  is    :a test  '))

        self.assertEqual(result, [b'this', b'is', b'a test  '])

    def test_leading_sentinel(self):
        result = list(messages._argsplit(b':this is :a test'))

        self.assertEqual(result, [b':this', b'is', b'a test'])


class FakeCommand(dict):
    def __init__(self, **kwargs):
        super(FakeCommand, self).__init__()

        for key, value in kwargs.items():
            if isinstance(value, tuple):
                idx = value[0]
                default = value[1]
            else:
                idx = value
                default = 'def%d' % idx

            self[key] = mock.Mock(**{
                'idx': idx,
                'default': default,
                'to_bytes.side_effect': lambda x, c, v: v,
            })

        self.arguments = set(self.keys())


class ArgumentsTest(unittest.TestCase):
    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_base(self, mock_init):
        command = FakeCommand(zero=0, one=1, two=2, three=3)
        value = {
            'zero': 'v0',
            'one': 'v1',
            'two': 'v2',
            'three': 'v3',
        }

        result = messages.Arguments.from_dict('ctxt', 'conn', command, value)

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, value)
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['v0', 'v1', 'v2', 'v3'], command)
        for key, cmd in command.items():
            cmd.to_bytes.assert_called_once_with('ctxt', 'conn', value[key])

    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_integer(self, mock_init):
        command = FakeCommand()
        value = {
            0: 'v0',
            1: 'v1',
            -2: 'v2',
            -1: 'v3',
        }

        result = messages.Arguments.from_dict('ctxt', 'conn', command, value)

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, {})
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['v0', 'v1', 'v2', 'v3'], command)

    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_defaults(self, mock_init):
        command = FakeCommand(zero=0, one=1, two=2, three=3)

        result = messages.Arguments.from_dict('ctxt', 'conn', command, {})

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, {})
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['def0', 'def1', 'def2', 'def3'], command)
        for cmd in command.values():
            cmd.to_bytes.assert_called_once_with('ctxt', 'conn', cmd.default)

    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_tail(self, mock_init):
        command = FakeCommand(zero=0, one=1, two=-2, three=-1)
        value = {
            'zero': 'v0',
            'one': 'v1',
            'two': 'v2',
            'three': 'v3',
        }

        result = messages.Arguments.from_dict('ctxt', 'conn', command, value)

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, value)
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['v0', 'v1', 'v2', 'v3'], command)
        for key, cmd in command.items():
            cmd.to_bytes.assert_called_once_with('ctxt', 'conn', value[key])

    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_tail_defaults(self, mock_init):
        command = FakeCommand(zero=0, one=1, two=-2, three=-1)

        result = messages.Arguments.from_dict('ctxt', 'conn', command, {})

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, {})
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['def0', 'def1', 'def-2', 'def-1'], command)
        for cmd in command.values():
            cmd.to_bytes.assert_called_once_with('ctxt', 'conn', cmd.default)

    @mock.patch.object(messages.Arguments, '__init__', return_value=None)
    def test_from_dict_gap(self, mock_init):
        command = FakeCommand(zero=0, one=(1, util.unset), two=-2, three=-1)

        result = messages.Arguments.from_dict('ctxt', 'conn', command, {})

        self.assertIsInstance(result, messages.Arguments)
        self.assertEqual(result._attr_cache, {})
        mock_init.assert_called_once_with(
            'ctxt', 'conn', ['def0', 'def-2', 'def-1'], command)
        for cmd in command.values():
            if cmd.default is util.unset:
                self.assertFalse(cmd.to_bytes.called)
            else:
                cmd.to_bytes.assert_called_once_with(
                    'ctxt', 'conn', cmd.default)

    def test_init(self):
        result = messages.Arguments('ctxt', 'conn', 'value', 'command')

        self.assertEqual(result._ctxt, 'ctxt')
        self.assertEqual(result._conn, 'conn')
        self.assertEqual(result._value, 'value')
        self.assertEqual(result._command, 'command')
        self.assertEqual(result._attr_cache, {})
        self.assertIsNone(result._seq_len)

    def test_len_cached(self):
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one'], 'command')
        args._seq_len = 100

        self.assertEqual(len(args), 100)
        self.assertEqual(args._seq_len, 100)

    def test_len_uncached_base(self):
        args = messages.Arguments('ctxt', 'conn', [util.unset, 'one', 'two'],
                                  'command')

        self.assertEqual(len(args), 3)
        self.assertEqual(args._seq_len, 3)

    def test_len_uncached_trailing(self):
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', util.unset],
                                  'command')

        self.assertEqual(len(args), 2)
        self.assertEqual(args._seq_len, 2)

    def test_len_uncached_empty(self):
        args = messages.Arguments('ctxt', 'conn', [util.unset, util.unset],
                                  'command')

        self.assertEqual(len(args), 0)
        self.assertEqual(args._seq_len, 0)

    def test_getitem_int(self):
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'],
                                  'command')
        args._seq_len = 2

        self.assertRaises(IndexError, lambda: args[-3])
        self.assertEqual(args[-2], 'zero')
        self.assertEqual(args[-1], 'one')
        self.assertEqual(args[0], 'zero')
        self.assertEqual(args[1], 'one')
        self.assertRaises(IndexError, lambda: args[2])

    def test_getitem_slice(self):
        args = messages.Arguments('ctxt', 'conn', [
            'zero',
            'one',
            'two',
            'three',
            'four',
            'five',
            'six',
            'seven',
            'eight',
            'nine',
            'ten',
        ], 'command')
        args._seq_len = 5

        self.assertEqual(args[:], ['zero', 'one', 'two', 'three', 'four'])
        self.assertEqual(args[1:3], ['one', 'two'])
        self.assertEqual(args[2:7], ['two', 'three', 'four'])
        self.assertEqual(args[-4:-1], ['one', 'two', 'three'])
        self.assertEqual(args[-7:-3], ['zero', 'one'])
        self.assertEqual(args[1:5:2], ['one', 'three'])

    def test_getitem_other(self):
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'],
                                  'command')

        self.assertRaises(TypeError, lambda: args['spam'])

    def test_getattr_unknown(self):
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'], {})
        args._attr_cache['spam'] = 'cached'

        self.assertRaises(AttributeError, lambda: args.spam)

    def test_getattr_cached(self):
        desc = mock.Mock(idx=100, default='default')
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'],
                                  {'spam': desc})
        args._attr_cache['spam'] = 'cached'

        self.assertEqual(args.spam, 'cached')
        self.assertFalse(desc.from_bytes.called)
        self.assertEqual(args._attr_cache, {'spam': 'cached'})

    def test_getattr_uncached_idxerr(self):
        desc = mock.Mock(idx=100, default='default')
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'],
                                  {'spam': desc})

        self.assertEqual(args.spam, 'default')
        self.assertFalse(desc.from_bytes.called)
        self.assertEqual(args._attr_cache, {'spam': 'default'})

    def test_getattr_uncached_value(self):
        desc = mock.Mock(**{
            'idx': 1,
            'default': 'default',
            'from_bytes.return_value': 'bytes',
        })
        args = messages.Arguments('ctxt', 'conn', ['zero', 'one', 'two'],
                                  {'spam': desc})

        self.assertEqual(args.spam, 'bytes')
        desc.from_bytes.assert_called_once_with('ctxt', 'conn', 'one')
        self.assertEqual(args._attr_cache, {'spam': 'bytes'})


class MessageTest(unittest.TestCase):
    @mock.patch('pirch.proto.irc.commands.get_command', return_value='command')
    @mock.patch.object(messages, 'Arguments', return_value='args')
    @mock.patch.object(messages.Message, '__init__', return_value=None)
    def test_from_bytes_base(self, mock_init, mock_Arguments,
                             mock_get_command):
        conn = mock.Mock(**{'get_entity.return_value': 'origin'})
        message = b'CMD arg1 arg2 arg3'

        result = messages.Message.from_bytes('ctxt', conn, message)

        self.assertIsInstance(result, messages.Message)
        self.assertEqual(result._msg, message)
        self.assertFalse(conn.get_entity.called)
        mock_get_command.assert_called_once_with(b'CMD')
        mock_Arguments.assert_called_once_with(
            'ctxt', conn, [b'arg1', b'arg2', b'arg3'], 'command')
        mock_init.assert_called_once_with(
            'ctxt', conn, conn.peer, 'command', 'args')

    @mock.patch('pirch.proto.irc.commands.get_command', return_value='command')
    @mock.patch.object(messages, 'Arguments', return_value='args')
    @mock.patch.object(messages.Message, '__init__', return_value=None)
    def test_from_bytes_origin(self, mock_init, mock_Arguments,
                               mock_get_command):
        conn = mock.Mock(**{'get_entity.return_value': 'origin'})
        message = b':origin CMD arg1 arg2 arg3'

        result = messages.Message.from_bytes('ctxt', conn, message)

        self.assertIsInstance(result, messages.Message)
        self.assertEqual(result._msg, message)
        conn.get_entity.assert_called_once_with(b'origin')
        mock_get_command.assert_called_once_with(b'CMD')
        mock_Arguments.assert_called_once_with(
            'ctxt', conn, [b'arg1', b'arg2', b'arg3'], 'command')
        mock_init.assert_called_once_with(
            'ctxt', conn, 'origin', 'command', 'args')

    @mock.patch('pirch.proto.irc.commands.get_command', return_value='command')
    @mock.patch.object(messages, 'Arguments', return_value='args')
    @mock.patch.object(messages.Message, '__init__', return_value=None)
    def test_from_bytes_empty(self, mock_init, mock_Arguments,
                              mock_get_command):
        conn = mock.Mock(**{'get_entity.return_value': 'origin'})
        message = b''

        result = messages.Message.from_bytes('ctxt', conn, message)

        self.assertIsNone(result)
        self.assertFalse(conn.get_entity.called)
        self.assertFalse(mock_get_command.called)
        self.assertFalse(mock_Arguments.called)
        self.assertFalse(mock_init.called)

    @mock.patch('pirch.proto.irc.commands.get_command', return_value='command')
    @mock.patch.object(messages, 'Arguments', return_value='args')
    @mock.patch.object(messages.Message, '__init__', return_value=None)
    def test_from_bytes_nocmd(self, mock_init, mock_Arguments,
                              mock_get_command):
        conn = mock.Mock(**{'get_entity.return_value': 'origin'})
        message = b':origin'

        result = messages.Message.from_bytes('ctxt', conn, message)

        self.assertIsNone(result)
        conn.get_entity.assert_called_once_with(b'origin')
        self.assertFalse(mock_get_command.called)
        self.assertFalse(mock_Arguments.called)
        self.assertFalse(mock_init.called)

    @mock.patch.object(messages.Arguments, 'from_dict', return_value='args')
    @mock.patch.object(messages.Message, '__init__', return_value=None)
    def test_new(self, mock_init, mock_from_dict):
        conn = mock.Mock()

        result = messages.Message.new('ctxt', conn, 'command', a=1, b=2)

        self.assertIsInstance(result, messages.Message)
        mock_from_dict.assert_called_once_with(
            'ctxt', conn, 'command', {'a': 1, 'b': 2})
        mock_init.assert_called_once_with(
            'ctxt', conn, conn.me, 'command', 'args')

    def test_init(self):
        msg = messages.Message('ctxt', 'conn', 'origin', 'command', 'args')

        self.assertEqual(msg.ctxt, 'ctxt')
        self.assertEqual(msg.conn, 'conn')
        self.assertEqual(msg.origin, 'origin')
        self.assertEqual(msg.command, 'command')
        self.assertEqual(msg.args, 'args')
        self.assertIsNone(msg._msg)

    def test_msg_cached(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', b'arg3']
        msg = messages.Message('ctxt', conn, origin, command, args)
        msg._msg = 'cached'

        self.assertEqual(msg.msg, 'cached')
        self.assertEqual(msg._msg, 'cached')

    def test_msg_uncached_base(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', b'arg3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertEqual(msg.msg, b':origin CMD arg1 arg2 arg3')
        self.assertEqual(msg._msg, b':origin CMD arg1 arg2 arg3')

    def test_msg_uncached_me(self):
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        conn = mock.Mock(me=origin)
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', b'arg3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertEqual(msg.msg, b'CMD arg1 arg2 arg3')
        self.assertEqual(msg._msg, b'CMD arg1 arg2 arg3')

    def test_msg_uncached_skip_unset(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', util.unset, b'arg3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertEqual(msg.msg, b':origin CMD arg1 arg2 arg3')
        self.assertEqual(msg._msg, b':origin CMD arg1 arg2 arg3')

    def test_msg_uncached_sentinel(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', b':arg3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertEqual(msg.msg, b':origin CMD arg1 arg2 ::arg3')
        self.assertEqual(msg._msg, b':origin CMD arg1 arg2 ::arg3')

    def test_msg_uncached_spaced(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg2', b'arg 3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertEqual(msg.msg, b':origin CMD arg1 arg2 :arg 3')
        self.assertEqual(msg._msg, b':origin CMD arg1 arg2 :arg 3')

    def test_msg_uncached_double_trailing(self):
        conn = mock.Mock()
        origin = mock.Mock(**{'to_bytes.return_value': b'origin'})
        command = mock.Mock(cmd=b'CMD')
        args = [b'arg1', b'arg 2', b'arg 3']
        msg = messages.Message('ctxt', conn, origin, command, args)

        self.assertRaises(ValueError, lambda: msg.msg)
        self.assertIsNone(msg._msg)
