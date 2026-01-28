# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""CLI entry point for streamer service with dynamic port allocation."""

import os
import sys


def main() -> None:
    """Start streamer service on a free port."""
    # Import here to delay initialization
    from common.port_utils import find_free_port

    # Find free port starting from 8000
    port = find_free_port(start_port=8000)
    if port is None:
        print("ERROR: Could not find a free port in range 8000-8099", file=sys.stderr)
        sys.exit(1)

    # Set public URL for orchestrator registration BEFORE importing main
    host = os.getenv("SERVICE_HOST", "localhost")
    public_url = f"http://{host}:{port}"
    os.environ["STREAMER_PUBLIC_URL"] = public_url

    print(f"Starting streamer service on {public_url}")

    # Now import uvicorn and start
    import uvicorn

    uvicorn.run(
        "streamer.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "true").lower() in ("true", "1", "yes"),
    )


if __name__ == "__main__":
    main()
