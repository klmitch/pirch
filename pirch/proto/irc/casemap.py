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

import string

import six


# Select the correct translation table maker for the Python version
if six.PY2:  # pragma: no cover
    _maketrans = string.maketrans
else:  # pragma: no cover
    _maketrans = str.maketrans


# Need translation tables for ascii, rfc1459, and strict-rfc1459
_transtab = {
    'ascii': _maketrans(string.ascii_uppercase,
                        string.ascii_lowercase),
    'rfc1459': _maketrans(string.ascii_uppercase + r'[\]^',
                          string.ascii_lowercase + r'{|}~'),
    'strict-rfc1459': _maketrans(string.ascii_uppercase + r'[\]',
                                 string.ascii_lowercase + r'{|}'),
}


def _make_mapper(mapping):
    """
    Construct a mapping callable for the designated mapping.

    :param mapping: The name of the mapping.

    :returns: A callable taking one argument and returning that
              argument converted to lower case.
    """

    return lambda x: x.translate(_transtab[mapping])


# Construct the actual mappers
mappers = {m: _make_mapper(m) for m in _transtab}
