"""Phase 12 request-session transaction boundary tests."""

import pytest

from app.database.session import get_db_session


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_: object) -> None:
        self.closed = True


class FakeDatabase:
    def __init__(self, session: FakeSession) -> None:
        self.session_factory = lambda: session


@pytest.mark.asyncio
async def test_request_session_commits_and_closes() -> None:
    session = FakeSession()
    generator = get_db_session(FakeDatabase(session))  # type: ignore[arg-type]

    assert await anext(generator) is session
    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closed


@pytest.mark.asyncio
async def test_request_session_rolls_back_and_closes_on_error() -> None:
    session = FakeSession()
    generator = get_db_session(FakeDatabase(session))  # type: ignore[arg-type]

    assert await anext(generator) is session
    with pytest.raises(RuntimeError, match="query failed"):
        await generator.athrow(RuntimeError("query failed"))

    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closed
