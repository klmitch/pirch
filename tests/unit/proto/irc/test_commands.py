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

from pirch.proto.irc import commands
from pirch import util


class ArgumentTest(unittest.TestCase):
    def test_init_internal(self):
        self.assertRaises(ValueError, commands.Argument, '_internal', 0)

    def test_init_base(self):
        result = commands.Argument('name', 5)

        self.assertEqual(result.name, 'name')
        self.assertEqual(result.idx, 5)
        self.assertIs(result.default, util.unset)

    def test_init_alt(self):
        result = commands.Argument('name', 5, 'default')

        self.assertEqual(result.name, 'name')
        self.assertEqual(result.idx, 5)
        self.assertEqual(result.default, 'default')

    def test_from_bytes(self):
        arg = commands.Argument('name', 5)

        result = arg.from_bytes('ctxt', 'conn', 'value')

        self.assertEqual(result, 'value')

    def test_to_bytes(self):
        arg = commands.Argument('name', 5)

        result = arg.to_bytes('ctxt', 'conn', 'value')

        self.assertEqual(result, 'value')


class EntityArgumentTest(unittest.TestCase):
    def test_from_bytes(self):
        arg = commands.EntityArgument('name', 5)
        conn = mock.Mock(**{'get_entity.return_value': 'entity'})

        result = arg.from_bytes('ctxt', conn, 'bytes')

        self.assertEqual(result, 'entity')

    def test_to_bytes(self):
        arg = commands.EntityArgument('name', 5)
        entity = mock.Mock(**{'to_bytes.return_value': 'bytes'})

        result = arg.to_bytes('ctxt', 'conn', entity)

        self.assertEqual(result, 'bytes')


class CommandTest(unittest.TestCase):
    @mock.patch.dict(commands.Command._registry, clear=True)
    def test_register_base(self):
        command = mock.Mock(cmd=b'PING')

        commands.Command.register(command)

        self.assertEqual(commands.Command._registry, {b'PING': command})

    @mock.patch.dict(commands.Command._registry, clear=True)
    def test_register_duplicate(self):
        commands.Command._registry[b'PING'] = 'fake'
        command = mock.Mock(cmd=b'PING')

        self.assertRaises(ValueError, commands.Command.register, command)
        self.assertEqual(commands.Command._registry, {b'PING': 'fake'})

    @mock.patch.dict(commands.Command._registry, clear=True)
    def test_lookup_missing(self):
        self.assertRaises(KeyError, commands.Command.lookup, b'PING')

    @mock.patch.dict(commands.Command._registry, clear=True)
    def test_lookup_base(self):
        commands.Command._registry[b'PING'] = 'fake'

        result = commands.Command.lookup(b'PING')

        self.assertEqual(result, 'fake')

    def test_init(self):
        result = commands.Command(b'PING')

        self.assertEqual(result.cmd, b'PING')
        self.assertEqual(result._arguments, {})
        self.assertIsNone(result._argset)

    def test_contains_false(self):
        cmd = commands.Command(b'PING')

        self.assertFalse('token' in cmd)

    def test_contains_true(self):
        cmd = commands.Command(b'PING')
        cmd._arguments['token'] = 'argument'

        self.assertTrue('token' in cmd)

    def test_getitem_missing(self):
        cmd = commands.Command(b'PING')

        self.assertRaises(KeyError, lambda: cmd['token'])

    def test_getitem_base(self):
        cmd = commands.Command(b'PING')
        cmd._arguments['token'] = 'argument'

        self.assertEqual(cmd['token'], 'argument')

    def test_add_argument_base(self):
        cmd = commands.Command(b'PING')
        cmd._argset = 'something'
        desc = mock.Mock()
        desc.name = 'token'

        result = cmd.add_argument(desc)

        self.assertIs(result, cmd)
        self.assertEqual(cmd._arguments, {'token': desc})
        self.assertIsNone(cmd._argset)

    def test_add_argument_duplicate(self):
        cmd = commands.Command(b'PING')
        cmd._arguments['token'] = 'fake'
        cmd._argset = 'something'
        desc = mock.Mock()
        desc.name = 'token'

        self.assertRaises(ValueError, cmd.add_argument, desc)
        self.assertEqual(cmd._arguments, {'token': 'fake'})
        self.assertEqual(cmd._argset, 'something')

    def test_arguments_cached(self):
        cmd = commands.Command(b'PING')
        cmd._arguments = {'a': 1, 'b': 2, 'c': 3}
        cmd._argset = 'cached'

        self.assertEqual(cmd.arguments, 'cached')
        self.assertEqual(cmd._argset, 'cached')

    def test_arguments_uncached(self):
        cmd = commands.Command(b'PING')
        cmd._arguments = {'a': 1, 'b': 2, 'c': 3}

        self.assertEqual(cmd.arguments, {'a', 'b', 'c'})
        self.assertEqual(cmd._argset, {'a', 'b', 'c'})
