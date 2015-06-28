import logging
import uuid
import weakref
from phoenixdb import errors
from phoenixdb.cursor import Cursor
from phoenixdb.errors import OperationalError, NotSupportedError, ProgrammingError

__all__ = ['Connection']

logger = logging.getLogger(__name__)


class Connection(object):
    """Database connection.
    
    You should not construct this object manually, use :func:`~phoenixdb.connect` instead.
    """

    def __init__(self, client, **kwargs):
        self._client = client
        self._id = str(uuid.uuid4())
        self._closed = False
        self._cursors = []
        self.set_session(**kwargs)

    def __del__(self):
        if not self._closed:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._closed:
            self.close()

    def close(self):
        """Closes the connection.
       
        No further operations are allowed, either on the connection or any
        of its cursors, once the cursor is closed.
        """
        if self._closed:
            raise ProgrammingError('the connection is already closed')
        for cursor_ref in self._cursors:
            cursor = cursor_ref()
            if cursor is not None and not cursor._closed:
                cursor.close()
        self._client.closeConnection(self._id)
        self._client.close()
        self._closed = True

    def commit(self):
        """Commits pending database changes.

        Currently, this does nothing, because the RPC does not support
        transactions. Only defined for DB API 2.0 compatibility.
        You need to use :attr:`autocommit` mode.
        """
        if self._closed:
            raise ProgrammingError('the connection is already closed')

    def cursor(self):
        """Creates a new cursor.

        :returns:
            A :class:`~phoenixdb.cursor.Cursor` object.
        """
        if self._closed:
            raise ProgrammingError('the connection is already closed')
        cursor = Cursor(self)
        self._cursors.append(weakref.ref(cursor, self._cursors.remove))
        return cursor

    def set_session(self, autocommit=None, readonly=None):
        """Sets one or more parameters in the current connection.
        
        :param autocommit:
            Switch the connection to autocommit mode. With the current
            version, you need to always enable this, because
            :meth:`commit` is not implemented.
        
        :param readonly:
            Switch the connection to read-only mode.
        """
        props = {}
        if autocommit is not None:
            props['autoCommit'] = bool(autocommit)
        if readonly is not None:
            props['readOnly'] = bool(readonly)
        props = self._client.connectionSync(self._id, props)
        self._autocommit = props['autoCommit']
        self._readonly = props['readOnly']

    @property
    def autocommit(self):
        """Read/write property for switching the connection's autocommit mode."""
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value):
        if self._closed:
            raise ProgrammingError('the connection is already closed')
        props = self._client.connectionSync(self._id, {'autoCommit': bool(value)})
        self._autocommit = props['autoCommit']

    @property
    def readonly(self):
        """Read/write property for switching the connection's readonly mode."""
        return self._readonly

    @readonly.setter
    def readonly(self, value):
        if self._closed:
            raise ProgrammingError('the connection is already closed')
        props = self._client.connectionSync(self._id, {'readOnly': bool(value)})
        self._readonly = props['readOnly']


for name in errors.__all__:
    setattr(Connection, name, getattr(errors, name))
