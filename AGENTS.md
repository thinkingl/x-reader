# AGENTS.md

x-reader: 电子书 → 有声读物转换系统，基于 OmniVoice TTS

## 目录结构

- `backend/` — Python FastAPI + SQLite + pytest
- `frontend/` — React 19 + Ant Design 6 + Vite 8 + ESLint (无 TypeScript)
- `ios/` — Swift + SwiftUI (Xcode 项目)

## Backend

### 运行/测试
```bash
cd backend
source ../../.venv/bin/activate   # 需预先创建 venv
./run.sh   # 或: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
PYTHONPATH=. pytest tests/ -v
```

### 关键信息
- 所有 API 路由在 `app/main.py` (~813 行)，无独立路由文件
- DB schema: `app/models/database.py`，Pydantic schemas: `app/schemas.py`
- 认证已实现：Challenge-Response + JWT Token (`app/services/auth.py`)
- 启动时自动重置 stuck 的 `running` 任务为 `failed`

### 测试模式
- conftest.py 有 autouse fixtures：自动 mock AudioConverter 和 task_queue
- 测试用内存 SQLite，每个测试独立建表/删表
- `client` fixture 提供 TestClient，测试前重置全局 `_global_auth_manager`
- 认证测试需要 `db` fixture 手动传入

## Frontend

```bash
cd frontend
npm run dev    # http://localhost:5173
npm run lint
npm run build
```

### Architecture
- API base URL: 相对路径（通过 Vite proxy 转发到后端）
- Routes: `/` (books), `/books/:id`, `/tasks`, `/presets`, `/config`
- Global audio player via React Context (`AudioProvider` in `src/components/AudioPlayer.jsx`)
- Vite proxy: `/api/*` → `http://localhost:8000`（开发环境自动转发）

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
- 音频下载功能：按章节下载 + 整本书 zip 打包下载
- 前端代理配置：Vite proxy 转发 API 请求

### Pending
- 认证功能（Challenge-Response + JWT Token）
- PDF 按目录书签分章
- 上传文件大小限制 / 进度显示
- 转换任务暂停/恢复
- 语音预设导入/导出 (JSON 格式)
