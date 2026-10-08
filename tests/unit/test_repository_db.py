from contextlib import contextmanager

from packages.repositories.db import connection_scope


class FakeConnection:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


class FakePool:
    def __init__(self, connection):
        self._connection = connection
        self.borrowed = 0
        self.returned = 0

    @contextmanager
    def connection(self):
        self.borrowed += 1
        try:
            yield self._connection
        finally:
            self.returned += 1


def test_connection_scope_uses_raw_connection_unchanged():
    connection = FakeConnection()
    with connection_scope(connection) as actual:
        assert actual is connection


def test_connection_scope_rolls_back_raw_connection_on_error():
    connection = FakeConnection()
    try:
        with connection_scope(connection):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert connection.rollbacks == 1


def test_connection_scope_borrows_and_returns_pool_connection():
    connection = FakeConnection()
    pool = FakePool(connection)
    with connection_scope(pool) as actual:
        assert actual is connection
    assert pool.borrowed == 1
    assert pool.returned == 1
