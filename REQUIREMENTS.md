# x-reader 需求文档

> 电子书 → 音频 转换系统，基于 OmniVoice TTS 引擎

---

## 1. 项目概述

x-reader 是一个前后端系统，核心功能是将用户上传的电子书按章节解析，并调用 OmniVoice TTS 引擎将每章文本转换为音频文件，最终输出有声读物。

---

## 2. 功能模块

### 2.1 图书列表（Book List）

#### 2.1.1 电子书上传 ✅

- [x] 支持上传 EPUB、PDF、TXT 格式
- [x] 上传时可填写图书元信息（书名、作者）或自动从电子书中提取
- [ ] 上传文件大小限制（待定：默认 100MB）
- [ ] 上传进度显示
- [x] 上传后自动解析章节结构

#### 2.1.2 章节解析 ✅

- [x] EPUB：解析 OPF/NCX 获取章节目录和正文
- [ ] PDF：按目录书签分章，若无书签则按页数/标题检测分章
- [x] TXT：按特定分隔符（如 `第X章`）或固定行数分章
- [ ] 解析后展示章节树（可展开/折叠）
- [ ] 支持手动合并/拆分章节

#### 2.1.3 图书列表展示 ✅

- [x] 展示所有已上传图书（书名、作者、章节总数、转换状态）
- [x] 按名称/上传时间排序
- [x] 搜索/筛选
- [x] 删除图书（同时删除关联的章节和音频）

#### 2.1.4 图书详情 ✅

- [x] 图书元信息（书名、作者、格式、文件大小）
- [x] 章节列表（章节号、标题、字数、音频状态）
- [ ] 预览章节文本内容
- [x] 触发整本书或指定章节的音频转换

---

### 2.2 任务列表（Task List）

#### 2.2.1 任务定义 ✅

- [x] 一个任务 = 将一个章节的文本转换为一个音频文件
- [x] 任务关联到具体的图书和章节

#### 2.2.2 任务状态 ✅

- [x] pending — 待处理
- [x] running — 转换中
- [x] completed — 已完成
- [x] failed — 失败（可重试）
- [x] skipped — 跳过（章节为空或用户手动跳过）

#### 2.2.3 任务队列 ✅

- [x] 展示所有任务，按创建时间倒序
- [x] 支持按状态筛选（全部/待处理/进行中/已完成/失败）
- [x] 支持按图书筛选
- [x] 显示任务进度（当前任务进度百分比）
- [x] 显示任务耗时

#### 2.2.4 任务操作 ✅

- [x] 重试失败任务
- [x] 取消排队中的任务
- [ ] 批量重试所有失败任务
- [ ] 清除已完成任务
- [x] 查看失败任务的错误日志

#### 2.2.5 转换完成处理 ✅

- [x] 单章音频文件存储为 `{book_id}/{chapter_id}.{format}`
- [x] 音频文件 Metadata：
  - Title：章节标题
  - Artist：图书作者
  - Album：图书书名
  - Genre：有声书
  - Track Number：章节序号（从 1 开始）
  - Total Tracks：总章节数
  - Year：图书出版年份（如有）
- [x] 重新生成：已生成过的章节可再次生成，生成成功后覆盖原音频，失败则保留原音频
- [ ] 提供下载链接：
  - 单章下载：直接下载音频文件
  - 整本下载：将所有章节音频打包为 ZIP 下载

#### 2.2.6 音频播放 ✅

- [x] 图书详情页章节列表中，已完成的章节显示播放按钮
- [x] 点击播放按钮在线播放该章节音频
- [x] 播放器控件：播放/暂停、进度条、音量、倍速（0.5x ~ 2.0x）
- [ ] 支持连续播放（播放完当前章节自动播放下一章）
- [ ] 播放进度记忆（回到该章节时从上次位置继续）
- [x] 全局浮动播放器：切换页面/功能时不打断播放，播放器固定在页面底部

---

### 2.3 配置（Configuration）

#### 2.3.1 TTS 引擎配置 ✅

- [x] 模型路径（本地路径或 HuggingFace repo id）
- [x] 设备选择（auto / cuda / cpu）
- [x] 推理精度（float16 / float32）
- [x] ASR 模型路径（用于自动转录参考音频）
- [x] 并发数（同时转换的章节数，默认 1）
- [x] 电子书存储目录
- [x] 音频输出目录

#### 2.3.2 语音参数配置 ✅

- [x] 支持创建多个语音配置预设，每个预设可命名（如"温柔女声"、"严肃男声"）
- [x] 预设包含以下参数：
  - **语音模式**：语音克隆 / 语音设计 / 自动语音
  - **语音设计参数**（当模式为"语音设计"时）：
    - 性别（male / female）
    - 年龄（child / teenager / young adult / middle-aged / elderly）
    - 音调（very low / low / moderate / high / very high pitch）
    - 风格（whisper）
    - 口音（american / british / australian / ... accent）
    - 方言（四川话、东北话、河南话等）
  - **参考音频**（当模式为"语音克隆"时）：
    - 上传参考音频文件
    - 填写/自动识别参考文本
  - **生成参数**：
    - 解码步数（num_step: 16/32/64）
    - 引导强度（guidance_scale: 1.0 ~ 3.0）
    - 语速（speed: 0.5 ~ 2.0）
  - **语言设置**：自动检测 / 手动指定语言
- [x] 预设管理：
  - 创建新预设
  - 编辑已有预设
  - 删除预设
  - 设为默认预设
  - [ ] 导入/导出预设（JSON 格式）
- [x] 创建转换任务时选择使用哪个语音预设

#### 2.3.3 分块设置 ✅

- [x] 是否启用长文本分块（默认启用）
- [x] 分块时长（audio_chunk_duration: 5 ~ 30 秒）
- [x] 分块阈值（audio_chunk_threshold: 15 ~ 60 秒）

#### 2.3.4 输出设置 ✅

- [x] 音频格式（WAV / MP3 / AAC / M4A / OGG / FLAC / OPUS / WMA）
- [x] 采样率（24000 / 16000）
- [x] 文本分段大小（50-500 字符，默认 200）
- [x] 电子书存储目录（默认 data/books）
- [x] 音频输出目录（默认 data/audio）

---

## 3. 非功能需求

### 3.1 后端 ✅

- [x] 技术栈：Python + FastAPI
- [x] 数据库：SQLite（轻量，单机部署）或可选 PostgreSQL
- [x] 任务队列：使用简单的线程池或 Celery（可选）
- [x] 文件存储：本地文件系统
- [x] API 设计：RESTful

### 3.2 前端 ✅

- [x] 技术栈：React + Ant Design
- [x] 响应式布局

### 3.3 性能 ✅

- [x] 并发转换数可配置，默认 1 路（在配置页面设置）
- [ ] 转换任务支持暂停/恢复

### 3.4 安全

- [x] 上传文件类型白名单校验
- [x] 文件大小限制

### 3.5 测试 ✅

- [x] 单元测试覆盖核心模块：电子书解析、音频转换、任务管理
- [x] 接口测试覆盖所有 RESTful API
- [x] 测试覆盖率 ≥ 80%
- [x] 测试框架：pytest（后端）、Jest + React Testing Library（前端）

---

## 4. 数据模型

```
Book:
  id, title, author, format, file_path, cover_path,
  chapter_count, status, publish_year, created_at, updated_at

Chapter:
  id, book_id, chapter_number, title, text_content,
  word_count, audio_path, audio_duration, status,
  created_at, updated_at

Task:
  id, book_id, chapter_id, voice_preset_id, status, error_message,
  started_at, finished_at, created_at

VoicePreset:
  id, name, is_default, voice_mode, instruct, ref_audio_path,
  ref_text, num_step, guidance_scale, speed, language,
  created_at, updated_at

SystemConfig:
  key, value, updated_at
```

---

## 5. API 接口

```
# 图书
POST   /api/books/upload          # 上传电子书
GET    /api/books                  # 图书列表
GET    /api/books/{id}             # 图书详情（含章节列表）
DELETE /api/books/{id}             # 删除图书

# 章节
GET    /api/books/{id}/chapters    # 章节列表
GET    /api/chapters/{id}          # 章节详情（含文本内容）
PATCH  /api/chapters/{id}          # 更新章节（合并/拆分）

# 任务
POST   /api/tasks                  # 创建转换任务（选择语音预设）
GET    /api/tasks                   # 任务列表
GET    /api/tasks/{id}/progress    # 任务进度
POST   /api/tasks/{id}/retry       # 重试任务
DELETE /api/tasks/{id}             # 取消任务

# 语音预设
POST   /api/voice-presets          # 创建语音预设
GET    /api/voice-presets           # 预设列表
GET    /api/voice-presets/{id}     # 预设详情
PUT    /api/voice-presets/{id}     # 更新预设
DELETE /api/voice-presets/{id}     # 删除预设
PATCH  /api/voice-presets/{id}/set-default  # 设为默认预设
POST   /api/voice-presets/export   # 导出预设
POST   /api/voice-presets/import   # 导入预设

# 音频
GET    /api/audio/{book_id}/{chapter_id}       # 下载单章音频
GET    /api/audio/{book_id}/{chapter_id}/stream # 流式播放单章音频
GET    /api/audio/{book_id}/zip                 # 下载整本音频（ZIP 打包）

# 配置
GET    /api/config                 # 获取配置
PUT    /api/config                 # 更新配置
POST   /api/config/test            # 测试 TTS 配置
GET    /api/config/test-audio/{filename}  # 获取测试音频
```

---

## 6. 技术选型

| 组件 | 推荐方案 | 备选 |
|------|----------|------|
| 后端框架 | FastAPI | Flask |
| 前端框架 | React + Ant Design | Vue 3 + Element Plus |
| 数据库 | SQLite | PostgreSQL |
| 任务队列 | 线程池 | Celery + Redis |
| 电子书解析 | zipfile + xml.etree (EPUB) | ebooklib |
| PDF 解析 | PyMuPDF | PyPDF2 |
| 音频格式转换 | torchaudio + ffmpeg | pydub |
| 后端测试 | pytest | |
| 前端测试 | Jest + React Testing Library | |

---

## 7. 开发成本估算

### 7.1 代码量预估

| 模块 | 实际代码行数 | 说明 |
|------|-------------|------|
| 后端 API | ~450 行 | main.py |
| 数据模型 | ~90 行 | database.py |
| 电子书解析 | ~180 行 | ebook_parser.py |
| 音频转换 | ~230 行 | audio_converter.py |
| 任务队列 | ~190 行 | task_queue.py |
| 前端页面 | ~800 行 | 4 个页面 |
| 音频播放器 | ~150 行 | AudioPlayer.jsx |
| 测试 | ~120 行 | test_api.py + test_services.py |
| **合计** | **~2300 行** | |

### 7.2 已完成功能

- ✅ 电子书上传（EPUB/TXT）
- ✅ 章节自动解析
- ✅ 语音转换（支持 GPU 加速、文本分段）
- ✅ 实时进度显示
- ✅ 语音预设管理（独立页面，语音设计/克隆/自动）
- ✅ 语音克隆：上传参考音频 + ASR 自动转录
- ✅ 多种音频格式输出（WAV/MP3/AAC/M4A/OGG/FLAC/OPUS/WMA）
- ✅ 音频播放器
- ✅ 任务管理
- ✅ 后端重启自动清理残留任务
- ✅ 音频文件命名（{序号}_{标题}.{格式}）
- ✅ 文本分段大小可配置
- ✅ 配置测试功能（输入文本测试语音合成）
- ✅ 重新生成时删除旧音频文件

---

## 8. 修改日志

### 2026-04-09

**新增功能：**
1. 语音预设独立为单独页面（/presets），便于管理
2. 语音克隆模式支持上传参考音频文件（WAV/MP3/M4A/OGG/FLAC/AAC）
3. 上传音频后自动使用 Whisper ASR 模型转录参考文本
4. 参考音频自动截取前 30 秒

**API 新增：**
- `POST /api/voice-presets/upload-reference` - 上传参考音频并 ASR 转录

### 2026-04-08

**新增功能：**
1. 音频文件命名改为 `{序号}_{标题}.{格式}` 格式（如 `001_我的精神家园.mp3`），按名称排序时保持章节顺序
2. 文本分段大小可在配置界面中配置（默认 200 字符，范围 50-500）
3. 配置界面增加测试功能：输入文本 → 选择预设 → 生成音频 → 在线播放验证效果
4. 支持更多音频格式：WAV/MP3/AAC/M4A/OGG/FLAC/OPUS/WMA

**Bug 修复：**
1. 修复重新生成音频时旧文件未删除的问题
2. 修复播放功能 URL 未包含后端地址的问题
3. 修复章节状态未更新为 `converting` 导致进度不显示的问题
4. 修复 `os` 模块未导入导致任务执行失败的问题
5. 修复长文本导致转换超时的问题（改为 GPU + 分段处理）

**优化改进：**
1. 使用 GPU (CUDA) 加速转换，RTF 低至 0.025
2. 长文本自动分段处理，每段独立转换后合并
3. 进度条实时显示当前段数和百分比
4. 后端启动时自动清理残留的 running 状态任务
5. 语音预设默认选项改为「随机」
