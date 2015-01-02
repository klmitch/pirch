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

from pirch import util


class Argument(object):
    """
    Describe a single argument.
    """

    def __init__(self, name, idx, default=util.unset):
        """
        Initialize an ``Argument`` instance.

        :param name: The argument name.
        :param idx: The index it will appear in the command argument
                    list.  May be negative.
        :param default: An optional default value for the argument to
                        assume.  This may be passed to the
                        ``to_raw()`` method when creating a
                        ``pirch.messages.Message`` object.
        """

        if name[0] == '_':
            raise ValueError('Argument names may not begin with "_".')

        # Save the relevant data
        self.name = name
        self.idx = idx
        self.default = default

    def from_bytes(self, ctxt, conn, value):
        """
        Given a ``bytes`` value, generate an appropriate object
        representing the value of the argument.  The default
        implementation returns the ``bytes`` value unchanged.

        :param ctxt: The current context.
        :param conn: The connection the argument was received from.
        :param value: The raw ``bytes`` value.

        :returns: The decoded value.
        """

        return value

    def to_bytes(self, ctxt, conn, value):
        """
        Given an object representing the value of an argument,
        generate the appropriate ``bytes`` value.  The default
        implementation returns the value unchanged, making the
        assumption that it is already ``bytes``.

        :param ctxt: The current context.
        :param conn: The connection the argument will be sent to.
        :param value: The argument value.

        :returns: The encoded value.
        """

        return value


class EntityArgument(Argument):
    """
    Describe a single argument that specifies an entity.
    """

    def from_bytes(self, ctxt, conn, value):
        """
        Given a ``bytes`` value, generate an appropriate object
        representing the value of the argument.

        :param ctxt: The current context.
        :param conn: The connection the argument was received from.
        :param value: The raw ``bytes`` value.

        :returns: A ``pirch.entities.Entity`` object describing the
                  designated entity.
        """

        return conn.get_entity(value)

    def to_bytes(self, ctxt, conn, value):
        """
        Given a ``pirch.entities.Entity`` object representing the
        value of an argument, generate the appropriate ``bytes``
        value.

        :param ctxt: The current context.
        :param conn: The connection the argument will be sent to.
        :param value: The ``pirch.entities.Entity`` object describing
                      the entity.

        :returns: The ``bytes`` form of the entity.
        """

        return value.to_bytes()


class Command(object):
    """
    Represent an IRC command.
    """

    # A registry of recognized commands
    _registry = {}

    @classmethod
    def register(cls, command):
        """
        Register a command.

        :param command: An instance of ``Command`` describing the
                        command.
        """

        # Inhibit duplicate registrations
        if command.cmd in cls._registry:
            raise ValueError('duplicate registration of command "%s"' %
                             command.cmd.decode('ascii'))

        cls._registry[command.cmd] = command

    @classmethod
    def lookup(cls, cmd):
        """
        Look up the ``Command`` instance describing a command.

        :param cmd: The ``bytes`` instance naming the command.

        :returns: An instance of ``Command`` describing the command.
        """

        # Look up and return the command, throwing a KeyError if it
        # doesn't exist
        return cls._registry[cmd]

    def __init__(self, cmd):
        """
        Initialize a ``Command`` instance.

        :param cmd: The ``bytes`` for the command, e.g. b"PING", etc.
        """

        self.cmd = cmd
        self._arguments = {}
        self._argset = None

    def __contains__(self, name):
        """
        Determine if an argument has been declared.

        :params name: The name of the argument.

        :returns: A ``True`` value if the argument has been declared,
                  ``False`` otherwise.
        """

        return name in self._arguments

    def __getitem__(self, name):
        """
        Retrieve an appropriate ``Argument`` instance describing the
        argument with a given name.

        :param name: The name of the argument.

        :returns: The ``Argument`` instance for the argument.
        """

        return self._arguments[name]

    def add_argument(self, desc):
        """
        Add an argument descriptor.

        :param desc: The ``Argument`` instance to add to this
                     ``Command`` instance.

        :returns: The ``Command`` instance, for convenience.
        """

        # Inhibit duplicate argument names
        if desc.name in self._arguments:
            raise ValueError('duplicate argument "%s"' % desc.name)

        self._arguments[desc.name] = desc
        self._argset = None

        return self

    @property
    def arguments(self):
        """
        Retrieve a set of all recognized argument names.
        """

        if self._argset is None:
            self._argset = set(self._arguments.keys())
        return self._argset


# Register the basic keep-alive commands
Command.register(
    Command(b'PING')
    .add_argument(Argument('token', 0))
)
Command.register(
    Command(b'PONG')
    .add_argument(Argument('token', 0))
)
