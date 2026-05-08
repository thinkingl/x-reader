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
./docker/start.sh    # 一键构建+启动，自动探测内网缓存
docker-compose up -d   # 启动服务 (端口 8000 + 5173)
docker-compose down    # 停止服务
```

- 使用 `Dockerfile.cuda` 构建，支持 CUDA
- `start.sh` 自动探测内网缓存服务（Nexus/apt-cacher-ng），可用时使用缓存代理加速
- `docker build` 传递 `--build-arg USE_INTERNAL_CACHE=true/false` 控制是否使用缓存
- 数据卷: `./data:/app/backend/data`，模型卷: `./models:/app/models`
- 环境变量: `PYTHONPATH=/app/backend`, `ALLOW_MODEL_DOWNLOAD=true`

## 当前状态

### 已完成
- 后端 FastAPI + 任务队列 + 电子书解析器 + 音频转换服务
- 前端 React 应用（5 页面 + 全局浮动播放器 + 实时进度）
- 语音预设管理（设计/克隆/自动模式）+ ASR 自动转录
- 50+ 后端测试，iOS SwiftUI 客户端
- 音频下载功能：按章节下载 + 整本书 zip 打包下载
- 前端代理配置：Vite proxy 转发 API 请求
- 认证功能：Challenge-Response + JWT Token
- Docker 支持 (CUDA + GPU passthrough)
- 在线 TTS 支持：小米 MiMo V2.5 API，支持在线优先+失败回退
- 任务状态管理：pending → queued → running → completed/failed/cancelled
- 任务列表后端分页，章节内容查看，播放缓存修复
- Android Kotlin/Jetpack Compose 客户端（自适应布局，支持手机和平板）
- EPUB 章节目录文本级拆分（支持第X章/中文数字/特殊标记）
- EPUB 圆圈数字注解内联 (`①` → `(注: xxx)`)
- EPUB TTS 文本清理：移除《》等非语音符号
- EPUB 硬换行截断修复 (`unwrap_text`)：合并不以句号结尾的断行
- 章节列表分页 API (`ChapterListItem`/`ChapterListResponse`，排除 `text_content`)
- 转换失败退避重试：最多 3 次，间隔 1s/2s/3s
- SQLite 连接池优化（`NullPool` 多线程安全）
- TTS 超时配置 (`tts_timeout`，默认 120s，前端可配置)
- 英文分句支持 + 超长句次级标点拆分（优先级：逗号 > 冒号 > 空格）
- 中/英文分段大小分别配置 (`local_chunk_size_en`/`online_chunk_size_en`)
- 自动语言检测（CJK 字符占比 >30% 用中文限，否则英文限）
- 容器优雅重启：shutdown 保存任务状态，startup 自动恢复
- 转换任务的语音预设名称记录与展示（Chapter.voice_preset_name）
- 任务列表按状态筛选
- 任务取消（RUNNING/CHANNING 任务可取消，converter 分段间检测取消标志）
- 并发模型加载保护 (`threading.Lock` 防止 GPU OOM)
- 前端 Table 水平滚动 + 列宽优化 + 增量更新（仅变动的行重渲染）
- 前端智能轮询（仅 pending/queued/converting 时刷新）
- 日志时间戳格式 (`logging.basicConfig`)
- 前端时长显示格式（x时x分x秒）
- 测试数据：`tests/data/nana.epub` + `tests/data/worlds_end.epub`
- 单元测试：ebook_parser (10), nana_epub (12), tts_sanitize (30), split_text (34)

### 待修复 / 待优化
- PDF 按目录书签分章
- 上传文件大小限制 / 进度显示
- 语音预设导入/导出 (JSON 格式)
- MOBI 格式支持（`mobi` 包需在 Docker 镜像构建时安装，目前 Nexus 下载慢）
- 章节标题中的《》书名号清理
