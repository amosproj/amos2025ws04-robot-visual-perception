# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""CLI entry point for orchestrator service with dynamic port allocation."""

import os
import sys


def main() -> None:
    """Start orchestrator service on a free port."""
    # Import here to avoid early initialization
    from common.port_utils import find_free_port
    
    # Find free port starting from 8002
    port = find_free_port(start_port=8002)
    if port is None:
        print("ERROR: Could not find a free port in range 8002-8101", file=sys.stderr)
        sys.exit(1)
    
    # Set public URL BEFORE importing main
    host = os.getenv("SERVICE_HOST", "localhost")
    public_url = f"http://{host}:{port}"
    os.environ["ORCHESTRATOR_PUBLIC_URL"] = public_url
    
    print(f"Starting orchestrator service on {public_url}")
    print(f"Frontend should use VITE_ORCHESTRATOR_URL={public_url}")
    
    # Now import uvicorn and start
    import uvicorn
    
    uvicorn.run(
        "orchestrator.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "true").lower() in ("true", "1", "yes"),
    )


if __name__ == "__main__":
    main()
