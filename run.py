"""Local entrypoint: `python run.py` starts the Flask app on 127.0.0.1."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    src = Path(__file__).resolve().parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from game2048.config import load_settings
    from game2048.logging_setup import configure_logging
    from game2048.web.app import create_app

    settings = load_settings()
    configure_logging()
    app = create_app(settings)
    app.run(host="127.0.0.1", port=settings.port, debug=False)


if __name__ == "__main__":
    main()
