# x-reader

> 电子书 → 有声读物 转换系统，基于 OmniVoice TTS 引擎

## 功能特性

- 📚 支持 EPUB、PDF、TXT 电子书格式
- 🎯 按章节自动解析，支持中文章节标题识别
- 🎙️ 基于 OmniVoice 的高质量语音合成（支持 600+ 种语言）
- 🎨 语音设计：通过属性（性别、年龄、音调、口音）自定义声音
- 👤 语音克隆：上传参考音频，ASR 自动转录，一键克隆声音
- 📊 实时进度显示（文本分段转换，逐段显示进度）
- 🎵 多种音频格式输出（WAV/MP3/AAC/M4A/OGG/FLAC/OPUS/WMA）
- 🎧 内置浮动音频播放器，切换页面不打断播放
- 🔧 独立语音预设管理页面，可保存多组配置
- 🧪 配置测试功能：输入文本实时验证语音效果

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 16
- NVIDIA GPU（推荐，用于加速转换）

### 1. 启动后端

```bash
cd x-reader/backend

# 激活虚拟环境
source ../../.venv/bin/activate

# 创建数据目录
mkdir -p data/books data/audio

# 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 启动前端

```bash
cd x-reader/frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

## 使用指南

### 上传电子书

1. 点击「上传电子书」按钮
2. 选择 EPUB/PDF/TXT 文件
3. 可选填写书名和作者（自动从电子书提取）
4. 系统自动解析章节结构

### 转换音频

1. 进入图书详情页
2. 选择语音预设（可选）
3. 点击「转换」按钮转换单章，或「转换全部未完成章节」
4. 实时查看进度条和当前状态

### 语音预设配置

进入「语音预设」页面，可创建多个语音预设：

- **语音模式**：语音设计 / 语音克隆 / 自动语音
- **语音属性**：性别、年龄、音调、风格、口音、方言
- **生成参数**：解码步数、引导强度、语速
- **语言设置**：支持 20+ 种常用语言

### 语音克隆

语音克隆模式支持上传参考音频：

1. 进入「语音预设」页面
2. 点击「新建预设」
3. 选择「语音克隆」模式
4. 点击「上传参考音频」选择音频文件（支持 WAV/MP3/M4A/OGG/FLAC/AAC）
5. 系统自动使用 ASR 模型转录参考文本（可手动修改）
6. 音频自动截取前 30 秒
7. 保存预设后即可在转换时使用

### 支持的语音属性

| 类别 | 选项 |
|------|------|
| 性别 | 男 (male)、女 (female) |
| 年龄 | 儿童、少年、青年、中年、老年 |
| 音调 | 极低/低/中/高/极高音调 |
| 风格 | 耳语 (whisper) |
| 英语口音 | 美式、英式、澳式、加拿大、印度等 10 种 |
| 中文方言 | 四川话、东北话、河南话、陕西话等 12 种 |

### 测试语音合成

在「配置」页面可以测试语音效果：

1. 输入测试文本（默认已有一段示例文本）
2. 选择语音预设（可选，不选则为「随机」）
3. 点击「生成测试音频」
4. 等待生成完成后，可在线播放验证效果
5. 调整参数后可重复测试，直到满意

## 项目结构

```
x-reader/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 主应用
│   │   ├── database.py          # 数据库连接
│   │   ├── schemas.py           # Pydantic 数据模型
│   │   ├── models/
│   │   │   └── database.py      # SQLAlchemy ORM 模型
│   │   └── services/
│   │       ├── ebook_parser.py  # 电子书解析
│   │       ├── audio_converter.py # 音频转换
│   │       └── task_queue.py    # 任务队列
│   └── tests/                   # 测试文件
├── frontend/
│   └── src/
│       ├── App.jsx              # 主应用（路由+布局）
│       ├── api.js               # API 客户端
│       ├── pages/
│       │   ├── BookList.jsx     # 图书列表页
│       │   ├── BookDetail.jsx   # 图书详情页
│       │   ├── TaskList.jsx     # 任务列表页
│       │   └── Configuration.jsx # 配置页
│       └── components/
│           └── AudioPlayer.jsx  # 全局浮动播放器
├── data/
│   ├── books/                   # 电子书存储
│   └── audio/                   # 音频输出
└── test_books/                  # 测试电子书
```

## API 接口

### 图书

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/books/upload | 上传电子书 |
| GET | /api/books | 图书列表 |
| GET | /api/books/{id} | 图书详情 |
| DELETE | /api/books/{id} | 删除图书 |

### 章节

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/books/{id}/chapters | 章节列表 |
| GET | /api/chapters/{id} | 章节详情 |

### 任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/tasks | 创建转换任务 |
| GET | /api/tasks | 任务列表 |
| GET | /api/tasks/{id}/progress | 任务进度 |
| POST | /api/tasks/{id}/retry | 重试任务 |
| DELETE | /api/tasks/{id} | 取消任务 |

### 语音预设

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/voice-presets | 创建预设 |
| GET | /api/voice-presets | 预设列表 |
| GET | /api/voice-presets/{id} | 预设详情 |
| PUT | /api/voice-presets/{id} | 更新预设 |
| DELETE | /api/voice-presets/{id} | 删除预设 |
| PATCH | /api/voice-presets/{id}/set-default | 设为默认 |

### 音频

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/audio/{book_id}/{chapter_id} | 下载单章音频 |
| GET | /api/audio/{book_id}/{chapter_id}/stream | 流式播放 |
| GET | /api/audio/{book_id}/zip | 下载整本 ZIP |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/config | 获取配置 |
| PUT | /api/config | 更新配置 |
| POST | /api/config/test | 测试 TTS 配置 |
| GET | /api/config/test-audio/{filename} | 获取测试音频 |

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/challenge | 获取 challenge |
| POST | /api/auth/verify | 登录验证 |
| POST | /api/auth/enable | 启用认证 |
| POST | /api/auth/disable | 停用认证（需验证） |
| GET | /api/auth/status | 获取认证状态 |

## iOS 客户端

项目包含一个 iOS 原生客户端，位于 `ios/` 目录。

### 环境要求

- Xcode 15+
- iOS 17+

### 运行

```bash
open ios/xReader.xcodeproj
```

选择模拟器或设备后 Cmd+R 运行。

### 功能

- 首次启动输入服务器地址
- 图书列表、上传、详情、章节转换
- 语音预设管理
- 音频播放（支持锁屏控制）
- 任务进度实时显示

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 数据库 | SQLite |
| 任务队列 | ThreadPoolExecutor |
| 电子书解析 | zipfile + xml.etree (EPUB), PyMuPDF (PDF) |
| TTS 引擎 | OmniVoice |
| ASR 引擎 | Whisper (HuggingFace) |
| 音频处理 | torchaudio + ffmpeg |
| Web 前端 | React + Ant Design |
| iOS 客户端 | SwiftUI (iOS 17+) |
| 路由 | React Router |

## 测试

```bash
cd x-reader/backend
PYTHONPATH=. pytest tests/ -v
```

## 常见问题

### Q: 转换速度很慢？

A: 
- 确保使用 GPU（CUDA）而非 CPU
- 减少解码步数（num_step）可加快速度，但会降低质量
- 文本会自动分段处理，长文本需要更多时间

### Q: 播放音频没有声音？

A:
- 检查后端是否正常运行
- 确认音频文件已生成
- 浏览器可能不支持某些音频格式，推荐使用 MP3

### Q: 如何使用语音克隆？

A:
1. 在配置页面创建新预设
2. 选择「语音克隆」模式
3. 上传参考音频文件（几秒即可）
4. 填写参考音频的转录文本
5. 保存预设并在转换时选择使用

## 许可证

MIT License
