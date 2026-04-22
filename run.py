"""Local entrypoint: `python run.py` starts the Flask app on 127.0.0.1."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from game2048.config import load_settings  # noqa: E402
from game2048.logging_setup import configure_logging  # noqa: E402
from game2048.web.app import create_app  # noqa: E402


def main() -> None:
    settings = load_settings()
    configure_logging()
    app = create_app(settings)
    app.run(host="127.0.0.1", port=settings.port, debug=False)


if __name__ == "__main__":
    main()
