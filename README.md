# 2048

A local, self-contained implementation of the 2048 puzzle game with a Flask web UI
and a pluggable AI "Hint" feature. Runs entirely on your machine. The default
solver (Expectimax) needs no network access and no API keys; optional LLM backends
(OpenAI, Anthropic, Google) are available if you provide your own keys via `.env`.

## Features

- Classic 2048 rules on a 4x4 board. Starts with 2 tiles. Spawns a `2` (90%) or `4` (10%) after each valid move, configurable in the UI.
- Keyboard (arrow keys, WASD) and on-screen controls.
- **Hint** button: shows the best next move for the current board, without executing it.
  - `Local (Expectimax)` — fast, offline, and stronger than the LLMs for this task.
  - `OpenAI`, `Anthropic`, `Google` — optional, if a key is configured in `.env`.
- **Auto-Solve** button: plays moves automatically at 2 moves/sec until win, loss, or Stop. Local solver only.
- Adjustable "chance of spawning a 4" slider for the next new game.
- Pure Python 3.11+, tiny dependency footprint (`Flask`, `httpx`, `python-dotenv`).
- `pytest` test suite covering engine, AI, Flask endpoints, LLM adapters (with HTTP mocked), and key-redaction.

## Requirements

- Python **3.11 or newer**
- A modern browser (Chrome, Firefox, Safari, Edge)

## Install

```bash
git clone <this-repo-url> game_2048
cd game_2048

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run

```bash
python run.py
```

Then open <http://127.0.0.1:5050> in your browser.

The default port is **5050** rather than 5000 because macOS (Monterey and later)
uses port 5000 for AirPlay Receiver. To change the port:
`FLASK_RUN_PORT=8080 python run.py`.

## Use LLM hints (optional)

You can ask OpenAI, Anthropic, or Google for move hints instead of the local solver.

1. Copy the example env file and edit it:
   ```bash
   cp .env.example .env
   ```
2. Fill in **only** the providers you want to use:
   ```ini
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   GOOGLE_API_KEY=AIza...
   ```
3. Restart `python run.py`. The UI's "Provider" dropdown will enable any provider
   whose key is set and display its status in Settings.

### Honest note on LLM quality

LLMs are not good at 2048. The local Expectimax search will reach the 2048 tile
much more reliably and much more cheaply than any of the hosted models. LLM hints
are here because the exercise requires them and because it is fun to compare —
not because they are the best oracle. Auto-Solve only runs with the local solver
to avoid needless API spend.

## API key safety

This project treats API keys as sensitive credentials.

- Keys are read **only** from environment variables at startup (via `.env`).
- The web UI **never** accepts a key as input. There is no route that writes keys.
- The `.gitignore` excludes `.env`; only `.env.example` (no secrets) is committed.
- All logs and HTTP error responses pass through a redaction filter that scrubs
  `sk-...`, `sk-ant-...`, `AIza...`, `Bearer ...` tokens, and any value of any
  environment variable whose name ends in `_API_KEY`.
- LLM requests go to the provider's official HTTPS endpoint only; plain `http://`
  is rejected by the adapter base class.
- No prompts, responses, or keys are persisted anywhere by the app.

**If you accidentally expose a key** (e.g. pasted in a screenshot, committed to a
public repo, shared in chat), rotate it immediately at the provider's dashboard.
That is the only way to make it safe again.

## Tests

```bash
pytest
```

The suite exercises:

- Engine moves, merges, spawns, and endgame detection (including the golden
  examples from the original requirements).
- Expectimax suggestions on fixed boards.
- Every Flask endpoint through the test client, including the Solve lifecycle.
- Each LLM adapter (OpenAI / Anthropic / Google) with HTTP traffic mocked via
  `respx` — no real API calls, no real keys needed.
- Redaction of API keys in logs and HTTP responses.

## Lint and format

```bash
ruff check .
ruff format .
```

## Project layout

```
src/game2048/
  config.py              Load settings from env / .env
  logging_setup.py       Logging config + redaction filter
  engine/                Pure game logic (no Flask, no I/O)
    board.py             Move / merge / spawn / endgame
    rules.py             Direction, GameStatus, constants
    game.py              Stateful wrapper with score + move history
  ai/
    solver.py            Solver protocol + Suggestion dataclass
    heuristics.py        Empty / monotonicity / smoothness / corner
    expectimax.py        Local search with iterative deepening
    registry.py          Name -> Solver factory, provider availability
    llm/
      base.py            Shared prompt, parsing, timeouts, HTTPS-only
      openai.py          OpenAI Chat Completions adapter
      anthropic.py       Anthropic Messages adapter
      google.py          Google Gemini generateContent adapter
  web/
    app.py               Flask app factory + routes
    solver_runner.py     Background thread for Auto-Solve
    templates/index.html
    static/style.css
    static/app.js
tests/                   pytest suite (mirrors the structure above)
```

## Extending

- **New AI** (e.g. Minimax + alpha-beta or Monte Carlo rollouts):
  1. Create a new class implementing the `Solver` protocol from `src/game2048/ai/solver.py`.
  2. Register it in `SolverRegistry` in `src/game2048/ai/registry.py`.
  3. Add it to the UI dropdown in `static/app.js` (or just let `renderProviders`
     pick it up via `/api/state` if you add it to `provider_info`).
- **Undo**: `Game.history` already records every move (`board_before`, `board_after_move`,
  `board_after_spawn`, `score_delta`). A one-method `undo()` can pop the last entry
  and restore state.
- **Different board sizes**: the engine uses a `BOARD_SIZE` constant (`engine/rules.py`)
  but also relies on it in a couple of places; would need a light refactor to
  parameterize fully.
- **Swap the UI**: the Flask JSON API is the only coupling; the engine has no
  Flask imports and could be reused from a CLI or desktop GUI.

## License

MIT. See [LICENSE](LICENSE).

## Assumptions (per the requirements doc's conflict-resolution note)

Where the requirements doc is ambiguous, these are the choices this implementation
makes — all mutable in the code if someone disagrees:

- Board is 4x4. Initial state uses the classic 2-tile start (not the heavily-populated
  example shown in the requirements doc).
- Spawn probability defaults to the classic 10% for a `4`, user-adjustable in the UI.
- Score is the classic 2048 score: each merge adds the merged tile's new value.
- A move that doesn't change the board is a no-op and does not spawn a tile.
- The game ends at 2048 with a "You won!" banner and a New Game button. No continue mode.
- "AI Suggestion" is primarily served by the local Expectimax solver (strongest +
  offline + free). LLM providers fulfill the requirement's optional remote-AI path.
