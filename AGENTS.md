# AGENTS.md

## Project Structure

Three separate apps, no shared tooling:

- `backend/` — Python FastAPI + SQLite + pytest
- `frontend/` — React 19 + Ant Design 6 + Vite 8 + ESLint (no TypeScript)
- `ios/` — Swift + SwiftUI native iOS app (Xcode project)

## Backend

### Run

```bash
cd backend
source ../../.venv/bin/activate   # venv lives TWO levels up, not in repo
mkdir -p data/books data/audio    # required before first run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use `./run.sh` (does mkdir + uvicorn --reload).

### Test

```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

Tests auto-mock `AudioConverter` and `task_queue` in `conftest.py` so no GPU/model needed.
Uses in-memory SQLite (`sqlite:///:memory:`).

### Architecture Notes

- **All API routes live in `app/main.py`** (~730 lines) — there are no separate router files. The `app/api/` directory is empty.
- Database schema is in `app/models/database.py`, Pydantic schemas in `app/schemas.py`.
- On startup, stuck `running` tasks from previous sessions are reset to `failed`.
- `LOCAL_MODEL_PATH` and `LOCAL_ASR_MODEL_PATH` are hardcoded to `/home/x/code/OmniVoice/models/...` — override via DB config.
- No type checker (mypy/pyright) is configured. No linter configured.

### Dependencies

`requirements.txt` lists deps. Key ones: `fastapi`, `sqlalchemy`, `ebooklib`, `PyMuPDF`, `torch`, `torchaudio`, `omnivoice`, `pytest`, `httpx`.

## Frontend

### Run

```bash
cd frontend
npm install    # first time only
npm run dev    # dev server at http://localhost:5173
```

### Lint

```bash
cd frontend
npm run lint
```

No typecheck command exists (no TypeScript).

### Build

```bash
cd frontend
npm run build
```

### Architecture Notes

- API base URL is hardcoded to `http://localhost:8000` in `src/api.js`.
- Routes: `/` (books), `/books/:id`, `/tasks`, `/presets`, `/config`.
- Global audio player is a floating component managed via React Context (`AudioProvider` in `src/components/AudioPlayer.jsx`).
- No proxy configured in `vite.config.js` — frontend calls backend directly.

## iOS

### Open

```bash
open ios/xReader.xcodeproj
```

Requires Xcode 15+ with iOS 17 SDK. Select an iOS simulator or device, then build & run.

### Build

No CLI build command configured. Build via Xcode (Cmd+B) or use `xcodebuild`:

```bash
xcodebuild -project ios/xReader.xcodeproj -scheme xReader -destination 'platform=iOS Simulator,name=iPhone 16' build
```

### Architecture Notes

- Server URL is user-configurable (stored in UserDefaults, prompted on first launch).
- All API calls go through `Network/APIClient.swift` — single URLSession-based client.
- `Info.plist` sets `NSAllowsArbitraryLoads = true` for HTTP backend access.
- Audio uses `AVPlayer` with `MPRemoteCommandCenter` for lock screen controls.
- LSP errors on macOS are expected — iOS-specific APIs (AVAudioSession, UIDocumentPicker) require the iOS SDK.
