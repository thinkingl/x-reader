# AGENTS.md

## Project

x-reader: 将用户上传的电子书（EPUB、PDF、TXT）用 OmniVoice 按章节转换为音频文件。
页面含子页面：图书列表、任务列表、语音预设、配置。

Three separate apps, no shared tooling:
- `backend/` — Python FastAPI + SQLite + pytest
- `frontend/` — React 19 + Ant Design 6 + Vite 8 + ESLint (no TypeScript)
- `ios/` — Swift + SwiftUI native iOS app (Xcode project)

GitHub: `https://github.com/thinkingl/x-reader.git`

## Instructions

- 支持语音克隆（上传参考音频，ASR 自动转录）和语音设计（性别、年龄、音调等属性控制）
- 音频文件命名格式 `{序号}_{标题}.{格式}`，按名称排序保持章节顺序
- 文本分段大小可配置（默认 200 字符），支持多音频格式输出
- 计划认证方案：Challenge-Response + JWT Token，明文 key 不传输

## Discoveries

- EPUB 解析需用 `zipfile` + `xml.etree`，`ebooklib` 无法处理某些命名空间
- 长文本会导致转换超时，需 GPU 加速并分段处理
- 文件上传表单需用 `Form()` 声明参数
- 模型路径：OmniVoice `models/OmniVoice`，Whisper ASR `models/whisper-large-v3-turbo`，venv `.venv`

## Backend

### Run/Build/Lint/Test
```bash
cd backend
source ../../.venv/bin/activate
./run.sh   # or: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
PYTHONPATH=. pytest tests/ -v  # auto-mocks GPU, in-memory SQLite
```

### Architecture
- **All API routes in `app/main.py`** (~730 lines), no separate router files
- DB schema: `app/models/database.py`, Pydantic schemas: `app/schemas.py`
- Startup resets stuck `running` tasks to `failed`
- Deps: `fastapi`, `sqlalchemy`, `ebooklib`, `PyMuPDF`, `torch`, `torchaudio`, `omnivoice`, `pytest`, `httpx`

## Frontend

### Run/Lint/Build
```bash
cd frontend
npm run dev    # http://localhost:5173
npm run lint
npm run build
```

### Architecture
- API base URL: `http://localhost:8000` in `src/api.js`
- Routes: `/` (books), `/books/:id`, `/tasks`, `/presets`, `/config`
- Global audio player via React Context (`AudioProvider` in `src/components/AudioPlayer.jsx`)

## iOS

```bash
open ios/xReader.xcodeproj  # Xcode 15+ / iOS 17 SDK
xcodebuild -project ios/xReader.xcodeproj -scheme xReader -destination 'platform=iOS Simulator,name=iPhone 16' build
```

- Server URL user-configurable (UserDefaults), API via `Network/APIClient.swift`
- Audio: `AVPlayer` + `MPRemoteCommandCenter`
- LSP errors on macOS expected (iOS-specific APIs)

## Progress

### Done
- 后端 FastAPI + 任务队列 + 电子书解析器 + 音频转换服务
- 前端 React 应用（5 页面 + 全局浮动播放器 + 实时进度）
- 语音预设管理（设计/克隆/自动模式）+ ASR 自动转录
- 13 个后端测试，iOS SwiftUI 客户端
- 代码推送到 GitHub

### Pending
- 认证功能（Challenge-Response + JWT Token）
- PDF 按目录书签分章
- 上传文件大小限制 / 进度显示
- 转换任务暂停/恢复
- 语音预设导入/导出（JSON 格式）
