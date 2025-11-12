# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT
import pytest
from unittest.mock import AsyncMock, MagicMock

from common.core.session import WebcamSession

MOCK_URL = "http://localhost:8000/offer"


def test_webcam_session_initialization():
    """Test that WebcamSession initializes correctly."""
    session = WebcamSession(MOCK_URL)

    assert session._offer_url == MOCK_URL
    assert session._pc is None
    assert session._track is None


@pytest.mark.asyncio
async def test_webcam_session_close():
    """Test that session cleanup works correctly."""
    session = WebcamSession(MOCK_URL)

    mock_track = MagicMock()
    session._track = mock_track

    mock_pc = AsyncMock()
    session._pc = mock_pc

    await session.close()

    mock_track.stop.assert_called_once()
    mock_pc.close.assert_awaited_once()

    assert session._track is None
    assert session._pc is None
