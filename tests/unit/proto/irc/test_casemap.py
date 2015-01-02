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

from pirch.proto.irc import casemap


class MappersTest(unittest.TestCase):
    def assert_mapper(self, mapper, exemplar, expected):
        actual = casemap.mappers[mapper](exemplar)

        self.assertEqual(expected, actual)

    def test_ascii(self):
        self.assert_mapper('ascii',
                           'This IS a TeSt [\\]^',
                           'this is a test [\\]^')

    def test_rfc1459(self):
        self.assert_mapper('rfc1459',
                           'This IS a TeSt [\\]^',
                           'this is a test {|}~')

    def test_strict_rfc1459(self):
        self.assert_mapper('strict-rfc1459',
                           'This IS a TeSt [\\]^',
                           'this is a test {|}^')
