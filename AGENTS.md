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

- API base 动态构建：`${protocol}//${hostname}:8000` (`src/api.js`)
- 路由: `/` (books), `/books/:id`, `/tasks`, `/presets`, `/config`
- 全局音频播放器: `AudioProvider` 在 `src/components/AudioPlayer.jsx`
- ESLint flat config，`no-unused-vars` 规则忽略大写开头变量 (`^[A-Z_]`)

## iOS

```bash
open ios/xReader.xcodeproj  # Xcode 15+ / iOS 17 SDK
xcodebuild -project ios/xReader.xcodeproj -scheme xReader -destination 'platform=iOS Simulator,name=iPhone 16' build
```

- 服务器 URL 可配置 (UserDefaults)，API: `Network/APIClient.swift`
- 音频: `AVPlayer` + `MPRemoteCommandCenter`
- macOS LSP 预期会有 iOS 特有 API 报错

## 待完成

- PDF 按目录书签分章
- 上传文件大小限制 / 进度显示
- 转换任务暂停/恢复
- 语音预设导入/导出 (JSON 格式)
