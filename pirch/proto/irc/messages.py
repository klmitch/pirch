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

import collections

import six

from pirch.proto.irc import commands
from pirch import util


def _argsplit(msg):
    """
    A generator that splits an IRC protocol message up according to
    the rules of the IRC protocol.  In particular, the sentinel ':'
    found while looking for a space indicates that the remainder of
    the message is a single argument.  (Note that the sentinel ':' is
    ignored for the first argument.)

    :param msg: An IRC protocol message.

    :returns: An iterator over each argument in the message.
    """

    # Tracks the start of the argument currently being processed; if
    # None, we're looking for the next non-space character.
    prev = 0

    for i in range(len(msg)):
        # Are we skipping spaces?
        if prev is None:
            if msg[i] == b' ':
                continue
            elif msg[i] == b':':
                # Hit the last argument; yield it and get out of here
                yield msg[i + 1:]
                break
            else:
                # Hit the next argument...
                prev = i
        else:
            # Have we hit a space?
            if msg[i] == b' ':
                yield msg[prev:i]
                prev = None
    else:
        if prev is not None:
            # Yield the last argument
            yield msg[prev:]


class Arguments(collections.Sequence):
    """
    Represent the command arguments from an IRC protocol message.  Raw
    values may be accessed via indexing, as for a sequence, but
    translated values may be accessed via attribute syntax.
    """

    @classmethod
    def from_dict(cls, ctxt, conn, command, value):
        """
        Given a mapping of argument names to their values, constructs
        an ``Arguments`` object representing those arguments.

        :param ctxt: The current context.
        :param conn: The connection context for the arguments.  This
                     will be the connection the arguments will be sent
                     to.
        :param command: A ``pirch.commands.Command`` object
                        representing the command the arguments are
                        for.
        :param value: A dictionary value containing a mapping between
                      argument names and their values.

        :returns: An ``Arguments`` object.
        """

        # Initialize status data for the algorithm
        head = {}
        tail = {}
        highest_idx = -1
        seen = set()

        # Work through the dictionary values
        for arg, val in value.items():
            if isinstance(arg, six.integer_types):
                # Direct mapping
                if arg >= 0:
                    head[arg] = val
                    if arg > highest_idx:  # pragma: no branch
                        highest_idx = arg
                else:
                    tail[arg] = val

                continue

            # Get the argument description
            desc = command[arg]

            # Track that we've handled this argument
            seen.add(arg)

            # Convert the value
            val = desc.to_bytes(ctxt, conn, val)

            # Save it
            if desc.idx >= 0:
                head[desc.idx] = val
                if desc.idx > highest_idx:  # pragma: no branch
                    highest_idx = desc.idx
            else:
                tail[desc.idx] = val

        # OK, we handled all the values we were passed; fill in
        # defaults
        for arg in command.arguments - seen:
            desc = command[arg]
            if desc.default is util.unset:
                # No default specified
                continue

            # Save the default
            val = desc.to_bytes(ctxt, conn, desc.default)
            if desc.idx >= 0:
                head[desc.idx] = val
                if desc.idx > highest_idx:  # pragma: no branch
                    highest_idx = desc.idx
            else:
                tail[desc.idx] = val

        # Now that we have the total argument count, fold the tail
        # into the result
        total_len = highest_idx + 1 + len(tail)
        for orig_idx, val in tail.items():
            idx = total_len + orig_idx
            head[idx] = val
            if idx > highest_idx:  # pragma: no branch
                highest_idx = idx

        # Now fill in any gaps with the unset singleton
        head.update((idx, util.unset) for idx in
                    set(range(highest_idx + 1)) - set(head.keys()))

        # Convert from a dictionary into a list of values and
        # construct the Arguments
        arglist = [v for k, v in sorted(head.items(), key=lambda x: x[0])]
        args = cls(ctxt, conn, arglist, command)

        # Now we prime the attribute cache
        args._attr_cache = {k: v for k, v in value.items()
                            if not isinstance(k, six.integer_types)}

        return args

    def __init__(self, ctxt, conn, value, command):
        """
        Initialize an ``Arguments`` instance.

        :param ctxt: The current context.
        :param conn: The connection the arguments were received from.
        :param value: The arguments.  Must be a list of ``bytes``
                      instances.
        :param command: A ``pirch.commands.Command`` object
                        representing the command the arguments are
                        for.
        """

        self._ctxt = ctxt
        self._conn = conn
        self._value = value
        self._command = command

        # Initialize the caches
        self._attr_cache = {}
        self._seq_len = None

    def __len__(self):
        """
        Determine the length of an ``Arguments`` instance.  This will
        be the number of items in the ``Arguments`` sequence, less any
        trailing unset values.

        :returns: The length of the ``Arguments`` instance.
        """

        # Do we need to compute it?
        if self._seq_len is None:
            self._seq_len = len(self._value)

            # Decrement for trailing unset values
            for item in reversed(self._value):
                if item is not util.unset:
                    break
                self._seq_len -= 1

        return self._seq_len

    def __getitem__(self, idx):
        """
        Retrieve an item from the sequence by its index.

        :param idx: An integer or a ``slice`` object.

        :returns: The appropriate elements.
        """

        # Properly interpret integer indices
        if isinstance(idx, six.integer_types):
            if idx < -len(self) or idx >= len(self):
                raise IndexError('list index out of range')
            elif idx < 0:
                idx += len(self)

            return self._value[idx]

        # Handle slices
        elif isinstance(idx, slice):
            indices = idx.indices(len(self))
            return [self._value[idx] for idx in range(*indices)]

        # Raise an appropriate TypeError
        raise TypeError('list indices must be integers, not %s' %
                        idx.__class__.__name__)

    def __getattr__(self, attr):
        """
        Retrieve an argument by name.

        :param attr: The name of the argument to retrieve.

        :returns: The appropriately converted value.
        """

        # Make sure the attribute has been declared
        if attr not in self._command:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, attr))

        # Build it into the attribute cache
        if attr not in self._attr_cache:
            desc = self._command[attr]

            # Look it up
            try:
                value = self._value[desc.idx]
            except IndexError:
                # Identical to "unset"
                value = util.unset
            else:
                # We have it, so convert from bytes
                value = desc.from_bytes(self._ctxt, self._conn, value)

            # If the value is unset, use the argument default
            if value is util.unset:
                value = desc.default

            # Cache the value
            self._attr_cache[attr] = value

        return self._attr_cache[attr]


class Message(object):
    """
    Represent a single IRC protocol message.  Object attributes
    include:

    ``ctxt``
        The current context.

    ``conn``
        The connection the message was received from.

    ``origin``
        The origin of the message.  Will be an instance of
        ``pirch.Entity``.

    ``command``
        The command to execute.  May be ``None`` if no command was
        provided, or a string if the command was not recognized;
        otherwise, it will be an instance of ``pirch.Command``.

    ``args``
        A dictionary of command arguments.  This dictionary may be
        generated by the command's ``argmap()`` method.  If the
        command was not given or was not recognized, the dictionary
        will map integer indexes (beginning at 0) with the arguments
        as interpreted from the message.
    """

    @classmethod
    def from_bytes(cls, ctxt, conn, msg):
        """
        Construct a ``Message`` object from a protocol message.

        :param ctxt: The current context.
        :param conn: The connection the message was received from.
        :param msg: The bare IRC message, as received from the
                    network, in ``bytes``.

        :returns: A constructed ``Message`` object representing the
                  protocol message.
        """

        # Split the message into arguments and process them.  Note
        # that there should be no more than 15 arguments in a 510 byte
        # message, so we convert to a list immediately
        parts = list(_argsplit(msg))
        idx = 0

        # Bail out if it's an empty message
        if not parts[0]:
            return None

        # Determine the message origin
        if parts[idx][0] == b':':
            origin = conn.get_entity(parts[idx][1:])
            idx += 1
        else:
            # No prefix indicates a local origin
            origin = conn.peer

        # Determine the command
        if len(parts) > idx:
            command = commands.get_command(parts[idx])
            idx += 1
        else:
            # No command, no way to construct a Message
            return None

        # Construct the arguments
        args = Arguments(ctxt, conn, parts[idx:], command)

        # Construct a Message
        result = cls(ctxt, conn, origin, command, args)

        # Prime the message cache
        result._msg = msg

        return result

    @classmethod
    def new(cls, ctxt, conn, command, **kwargs):
        """
        Construct a ``Message`` instance.  This is a helper method
        which may be used to specify command arguments via keyword
        arguments.

        :param ctxt: The current context.
        :param conn: The connection the message will be sent to.
        :param command: The command contained in the message.  Must be
                        an instance of ``pirch.commands.Command``.
        :param kwargs: Keyword arguments are interpreted as arguments
                       for the command.

        :returns: A constructed ``Message`` object representing the
                  protocol message.
        """

        # Begin by building the arguments
        args = Arguments.from_dict(ctxt, conn, command, kwargs)

        # Construct and return the Message
        return cls(ctxt, conn, conn.me, command, args)

    def __init__(self, ctxt, conn, origin, command, args):
        """
        Initialize a ``Message`` instance.

        :param ctxt: The current context.
        :param conn: The connection the message was received from.
        :param origin: The origin of the message.  Must be an instance
                       of ``pirch.Entity``.
        :param command: The command contained in the message.  Must be
                        an instance of ``pirch.commands.Command``, or
                        a byte string for unrecognized commands.
        :param args: An instance of ``Arguments`` containing the
                     arguments for the command.
        """

        # Save the basic information
        self.ctxt = ctxt
        self.conn = conn
        self.origin = origin
        self.command = command
        self.args = args

        # A cache for the byte string form of the message
        self._msg = None

    @property
    def msg(self):
        """
        Return the message as ``bytes``.
        """

        # Do we need to compute the bytes form?
        if self._msg is None:
            parts = []

            # Begin with the origin
            if self.origin is not self.conn.me:
                parts.append(b':' + self.origin.to_bytes())

            # Add the command
            parts.append(self.command.cmd)

            # And the arguments, using the sentinel where necessary
            sentinel = False
            for arg in self.args:
                if arg is util.unset:
                    # No sanity checking is possible here...
                    continue

                # Do we need the sentinel?
                if arg[0] == b':' or b' ' in arg:
                    if sentinel:
                        raise ValueError('multiple trailing arguments')
                    parts.append(b':' + arg)
                    sentinel = True
                else:
                    parts.append(arg)

            # Compose the message from its parts
            self._msg = b' '.join(parts)

        return self._msg
