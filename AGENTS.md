# AGENTS.md

x-reader: 电子书 → 有声读物转换系统，基于 OmniVoice TTS

## 目录结构

- `backend/` — Python FastAPI + SQLite + pytest
- `frontend/` — React 19 + Ant Design 6 + Vite 8 + ESLint (无 TypeScript)
- `ios/` — Swift + SwiftUI (Xcode 项目)
- `android/` — Kotlin + Jetpack Compose + Material 3 (Android 项目)
- `models/` — 预训练模型 (OmniVoice TTS + whisper-large-v3-turbo ASR)

## Backend

### 运行/测试
```bash
cd backend
source ../.venv/bin/activate   # 需预先创建 venv
./run.sh   # 或: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
PYTHONPATH=. pytest tests/ -v
```

### 关键信息
- 所有 API 路由在 `app/main.py` (~960 行)，无独立路由文件
- DB models: `app/models/database.py`，Pydantic schemas: `app/schemas.py`
- 认证已实现：Challenge-Response + JWT Token (`app/services/auth.py`)
- 启动时自动重置 stuck 的 `running` 任务为 `failed`，修复状态不一致的章节
- 模型路径：`LOCAL_MODEL_PATH = ../models/OmniVoice`，`LOCAL_ASR_MODEL_PATH = ../models/whisper-large-v3-turbo`
- 在线 TTS：`app/services/mimo_tts.py` 封装小米 MiMo API，支持在线优先+失败回退
- 任务状态：pending → queued → running → completed/failed，按段回退本地模型

### 测试模式
- conftest.py 有 autouse fixtures：自动 mock AudioConverter 和 task_queue
- 测试用内存 SQLite，每个测试独立建表/删表
- `client` fixture 提供 TestClient，测试前重置全局 `_global_auth_manager`
- 认证测试需要 `db` fixture 手动传入
- 50 个测试函数 (test_api: 10, test_auth: 27, test_services: 3, test_ebook_parser: 10)

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
- 认证：AuthContext 管理登录状态，支持 SHA-256 + HMAC challenge-response
- 配置页面：支持 TTS 模式切换（本地/在线/在线优先）、MiMo API 配置、分段大小分别配置

## iOS

```bash
open ios/xReader.xcodeproj  # Xcode 15+ / iOS 17 SDK
xcodebuild -project ios/xReader.xcodeproj -scheme xReader -destination 'platform=iOS Simulator,name=iPhone 16' build
```

- Server URL user-configurable (UserDefaults), API via `Network/APIClient.swift`
- Audio: `AVPlayer` + `MPRemoteCommandCenter`
- LSP errors on macOS expected (iOS-specific APIs)

## Android

```bash
cd android
./gradlew assembleDebug   # 构建 debug APK
./gradlew assembleRelease # 构建 release APK
```

### Architecture
- Tech stack: Kotlin, Jetpack Compose, Material 3, Retrofit, OkHttp, Hilt, Media3 ExoPlayer
- Min SDK 26, Target SDK 34
- Server URL stored in DataStore, auth token in EncryptedSharedPreferences
- Adaptive layout: `WindowSizeClass` — phone 单面板, tablet 双面板 (列表+详情)
- API via Retrofit + OkHttp interceptors (动态 base URL + JWT auth)
- Audio: Media3 ExoPlayer + MediaSession (通知栏+锁屏控制)
- Navigation: Navigation Compose, 底部导航栏 (phone) / NavigationRail (tablet)
- DI: Hilt, ViewModels with StateFlow

## Docker

```bash
docker-compose up -d   # 启动服务 (端口 8000 + 5173)
docker-compose down    # 停止服务
```

- 使用 `Dockerfile` 构建，支持 CUDA (`Dockerfile.cuda`)
- 数据卷: `./data:/app/data`
- 环境变量: `PYTHONPATH=/app/backend`

## 当前状态

### 已完成
- 后端 FastAPI + 任务队列 + 电子书解析器 + 音频转换服务
- 前端 React 应用（5 页面 + 全局浮动播放器 + 实时进度）
- 语音预设管理（设计/克隆/自动模式）+ ASR 自动转录
- 50 个后端测试，iOS SwiftUI 客户端
- 音频下载功能：按章节下载 + 整本书 zip 打包下载
- 前端代理配置：Vite proxy 转发 API 请求
- 认证功能：Challenge-Response + JWT Token
- Docker 支持
- 在线 TTS 支持：小米 MiMo V2.5 API，支持在线优先+失败回退
- 任务状态管理：pending → queued → running → completed/failed
- 任务列表后端分页，章节内容查看，播放缓存修复
- Android Kotlin/Jetpack Compose 客户端（自适应布局，支持手机和平板）

### 待修复
- PDF 按目录书签分章
- 上传文件大小限制 / 进度显示
- 转换任务暂停/恢复
- 语音预设导入/导出 (JSON 格式)
