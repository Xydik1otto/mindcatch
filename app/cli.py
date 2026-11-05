"""Console entry point: `mindcatch` boots the local server and prints the URL."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    port = int(os.environ.get("MINDCATCH_PORT", "8000"))
    print(f"Mindcatch running at http://localhost:{port}  (Ctrl+C to stop)")
    uvicorn.run("app.main:app", port=port)


if __name__ == "__main__":
    main()
