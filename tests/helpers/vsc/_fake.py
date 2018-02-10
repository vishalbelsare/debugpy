import threading

from tests.helpers import protocol, socket
from ._vsc import encode_message, iter_messages, parse_message


PROTOCOL = protocol.MessageProtocol(
    parse=parse_message,
    encode=encode_message,
    iter=iter_messages,
)


class Started(protocol.Started):

    def send_request(self, msg):
        return self.fake.send_request(msg)


class FakeVSC(protocol.Daemon):
    """A testing double for a VSC debugger protocol client.

    This class facilitates sending VSC debugger protocol messages over
    the socket to ptvsd.  It also supports tracking (and even handling)
    the responses from ptvsd.

    "handler" is a function that reacts to incoming responses and events
    from ptvsd.  It takes a single response/event, along with a function
    for sending messages (requests, events) to ptvsd.

    Example usage:

      >>> pydevd = FakePyDevd()
      >>> fake = FakeVSC(lambda h, p: pydevd.start)
      >>> fake.start(None, 8888)
      >>> with fake.start(None, 8888):
      ...   fake.send_request('<a JSON message>')
      ...   # wait for events...
      ... 
      >>> fake.assert_received(testcase, [
      ...   # messages
      ... ])
      >>> 

    See debugger_protocol/messages/README.md for more about the
    protocol itself.
    """  # noqa

    def __init__(self, start_adapter, handler=None):
        super(FakeVSC, self).__init__(socket.connect, PROTOCOL, handler)

        def start_adapter(host, port, _start_adapter=start_adapter):
            self._adapter = _start_adapter(host, port)

        self._start_adapter = start_adapter
        self._adapter = None

    def start(self, host, port):
        """Start the fake and the adapter."""
        if self._adapter is not None:
            raise RuntimeError('already started')
        return super(FakeVSC, self).start(host, port)

    def send_request(self, req):
        """Send the given Request object."""
        return self.send_message(req)

    # internal methods

    def _start(self, host=None):
        start_adapter = (lambda: self._start_adapter(self._host, self._port))
        if not self._host:
            # The adapter is the server so start it first.
            t = threading.Thread(target=start_adapter)
            t.start()
            super(FakeVSC, self)._start('127.0.0.1')
            t.join(timeout=1)
            if t.is_alive():
                raise RuntimeError('timed out')
        else:
            # The adapter is the client so start it last.
            # TODO: For now don't use this.
            raise NotImplementedError
            t = threading.Thread(target=super(FakeVSC, self)._start)
            t.start()
            start_adapter()
            t.join(timeout=1)
            if t.is_alive():
                raise RuntimeError('timed out')

    def _close(self):
        if self._adapter is not None:
            self._adapter.close()
            self._adapter = None
        super(FakeVSC, self)._close()
