import SwiftUI

struct BookDetailView: View {
    let client: APIClient
    let player: AudioPlayerService
    let bookId: Int

    @State private var book: BookResponse?
    @State private var chapters: [ChapterResponse] = []
    @State private var presets: [VoicePresetResponse] = []
    @State private var selectedPresetId: Int?
    @State private var selectedChapterIds: Set<Int> = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var isConverting = false
    @State private var convertingChapterIds: Set<Int> = []
    @State private var viewingChapter: ChapterResponse?
    @StateObject private var polling = TaskPollingService()

    var body: some View {
        List {
            if let book {
                Section("图书信息") {
                    LabeledContent("书名", value: book.title)
                    if let author = book.author {
                        LabeledContent("作者", value: author)
                    }
                    LabeledContent("格式", value: book.format.uppercased())
                    LabeledContent("章节数", value: "\(book.chapter_count)")
                }
            }

            Section("转换设置") {
                Picker("语音预设", selection: $selectedPresetId) {
                    Text("随机").tag(nil as Int?)
                    ForEach(presets) { preset in
                        Text(preset.name).tag(preset.id as Int?)
                    }
                }
            }

            Section {
                Button {
                    Task { await convertChapters(Array(chapters), skipCompleted: true) }
                } label: {
                    Label(isConverting ? "转换中..." : "转换全部未完成章节", systemImage: "play.rectangle.fill")
                }
                .disabled(isConverting || chapters.allSatisfy { $0.status == "completed" })
            }

            Section("章节 (\(chapters.count))") {
                ForEach(chapters) { chapter in
                    ChapterRow(
                        chapter: chapter,
                        isSelected: selectedChapterIds.contains(chapter.id),
                        isConverting: convertingChapterIds.contains(chapter.id),
                        progress: progressForChapter(chapter.id),
                        onTap: {
                            toggleSelection(chapter.id)
                        },
                        onPlay: {
                            Task { await playChapter(chapter) }
                        },
                        onConvert: {
                            Task { await convertChapters([chapter]) }
                        },
                        onDownload: {
                            Task { await downloadChapter(chapter) }
                        },
                        onViewContent: {
                            viewingChapter = chapter
                        },
                        baseURL: client.baseURL
                    )
                }
            }
        }
        .navigationTitle(book?.title ?? "图书详情")
        .sheet(item: $viewingChapter) { chapter in
            NavigationStack {
                ChapterContentView(
                    client: client,
                    chapterId: chapter.id,
                    chapterTitle: chapter.title ?? "第\(chapter.chapter_number)章"
                )
            }
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                HStack {
                    if !selectedChapterIds.isEmpty {
                        Button("转换选中 (\(selectedChapterIds.count))") {
                            let selected = chapters.filter { selectedChapterIds.contains($0.id) }
                            Task { await convertChapters(selected) }
                        }
                    }
                    
                    if chapters.contains(where: { $0.status == "completed" }) {
                        Button {
                            Task { await downloadBookAudio() }
                        } label: {
                            Image(systemName: "arrow.down.circle")
                        }
                    }
                }
            }
        }
        .task { await loadData() }
        .refreshable { await loadData() }
        .alert("错误", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("确定") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
        .safeAreaInset(edge: .bottom) {
            if player.isPlaying {
                AudioPlayerBar(player: player)
            }
        }
    }

    private func toggleSelection(_ id: Int) {
        if selectedChapterIds.contains(id) {
            selectedChapterIds.remove(id)
        } else {
            selectedChapterIds.insert(id)
        }
    }

    private func loadData() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let bookResult: BookResponse = client.get(APIEndpoints.book(bookId))
            async let chaptersResult: [ChapterResponse] = client.get(APIEndpoints.chapters(bookId: bookId))
            async let presetsResult: VoicePresetList = try await client.get(APIEndpoints.voicePresets)

            let (b, ch, pr) = try await (bookResult, chaptersResult, presetsResult)
            book = b
            chapters = ch
            presets = pr.items
        } catch let e {
            self.errorMessage = e.localizedDescription
        }
    }

    private func progressForChapter(_ chapterId: Int) -> TaskProgress? {
        for (_, progress) in polling.activeTasks {
            if progress.message.contains("#\(chapterId)") || progress.task_id == chapterId {
                return progress
            }
        }
        return nil
    }

    private func convertChapters(_ chapters: [ChapterResponse], skipCompleted: Bool = false) async {
        isConverting = true
        defer { isConverting = false }
        do {
            let target = skipCompleted ? chapters.filter { $0.status != "completed" } : chapters
            guard !target.isEmpty else {
                errorMessage = skipCompleted ? "没有需要转换的章节" : "请选择章节"
                return
            }
            let targetIds = target.map { $0.id }
            convertingChapterIds = Set(targetIds)

            let body = TaskCreate(
                book_id: bookId,
                chapter_ids: targetIds,
                voice_preset_id: selectedPresetId
            )
            let _: TaskResponse = try await client.post(APIEndpoints.tasks, body: body)

            // Start polling and wait until all tasks finish
            polling.startPolling(client: client, bookId: bookId)
            await waitForCompletion()
            polling.stop()
            convertingChapterIds.removeAll()

            await loadData()
        } catch let e {
            self.errorMessage = "转换失败: \(e.localizedDescription)"
            polling.stop()
            convertingChapterIds.removeAll()
        }
    }

    private func waitForCompletion() async {
        // Poll until no running tasks remain for this book
        while true {
            do {
                let taskList: TaskList = try await client.get(
                    APIEndpoints.tasks,
                    queryItems: [
                        URLQueryItem(name: "book_id", value: String(bookId)),
                        URLQueryItem(name: "status", value: "running"),
                    ]
                )
                if taskList.items.isEmpty {
                    // Also check queued tasks
                    let queuedList: TaskList = try await client.get(
                        APIEndpoints.tasks,
                        queryItems: [
                            URLQueryItem(name: "book_id", value: String(bookId)),
                            URLQueryItem(name: "status", value: "queued"),
                        ]
                    )
                    if queuedList.items.isEmpty {
                        // Also check pending tasks
                        let pendingList: TaskList = try await client.get(
                            APIEndpoints.tasks,
                            queryItems: [
                                URLQueryItem(name: "book_id", value: String(bookId)),
                                URLQueryItem(name: "status", value: "pending"),
                            ]
                        )
                        if pendingList.items.isEmpty {
                            break
                        }
                    }
                }
            } catch {
                break
            }
            try? await Task.sleep(for: .seconds(2))
        }
    }

    private func downloadBookAudio() async {
        let url = client.baseURL + APIEndpoints.audioZip(bookId: bookId)
        guard let downloadURL = URL(string: url) else { return }

        let task = URLSession.shared.downloadTask(with: downloadURL) { localURL, response, error in
            guard let localURL = localURL, error == nil else {
                DispatchQueue.main.async {
                    errorMessage = "下载失败: \(error?.localizedDescription ?? "未知错误")"
                }
                return
            }

            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let destinationURL = documentsPath.appendingPathComponent("\(book?.title ?? "book").zip")

            do {
                if FileManager.default.fileExists(atPath: destinationURL.path) {
                    try FileManager.default.removeItem(at: destinationURL)
                }
                try FileManager.default.moveItem(at: localURL, to: destinationURL)
                DispatchQueue.main.async {
                    errorMessage = "下载完成: \(destinationURL.lastPathComponent)"
                }
            } catch {
                DispatchQueue.main.async {
                    errorMessage = "保存失败: \(error.localizedDescription)"
                }
            }
        }
        task.resume()
    }

    private func playChapter(_ chapter: ChapterResponse) async {
        let url = client.baseURL + APIEndpoints.audioStream(bookId: bookId, chapterId: chapter.id)
        guard let audioURL = URL(string: url) else { return }
        player.play(url: audioURL, title: chapter.title ?? "第\(chapter.chapter_number)章", bookTitle: book?.title ?? "")
    }

    private func downloadChapter(_ chapter: ChapterResponse) async {
        let url = client.baseURL + APIEndpoints.audioDownload(bookId: bookId, chapterId: chapter.id)
        guard let downloadURL = URL(string: url) else { return }

        let task = URLSession.shared.downloadTask(with: downloadURL) { localURL, response, error in
            guard let localURL = localURL, error == nil else {
                DispatchQueue.main.async {
                    errorMessage = "下载失败: \(error?.localizedDescription ?? "未知错误")"
                }
                return
            }

            // 从响应头获取文件名，或使用默认扩展名
            var fileExtension = ".mp3"
            if let httpResponse = response as? HTTPURLResponse,
               let contentDisposition = httpResponse.allHeaderFields["Content-Disposition"] as? String {
                // 尝试从Content-Disposition头解析文件名
                if let filename = contentDisposition.components(separatedBy: "filename=").last?.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "\"")) {
                    fileExtension = (filename as NSString).pathExtension.isEmpty ? ".mp3" : ".\((filename as NSString).pathExtension)"
                }
            }

            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let destinationURL = documentsPath.appendingPathComponent("\(chapter.title ?? "第\(chapter.chapter_number)章")\(fileExtension)")

            do {
                if FileManager.default.fileExists(atPath: destinationURL.path) {
                    try FileManager.default.removeItem(at: destinationURL)
                }
                try FileManager.default.moveItem(at: localURL, to: destinationURL)
                DispatchQueue.main.async {
                    errorMessage = "下载完成: \(destinationURL.lastPathComponent)"
                }
            } catch {
                DispatchQueue.main.async {
                    errorMessage = "保存失败: \(error.localizedDescription)"
                }
            }
        }
        task.resume()
    }
}

struct ChapterRow: View {
    let chapter: ChapterResponse
    let isSelected: Bool
    let isConverting: Bool
    let progress: TaskProgress?
    let onTap: () -> Void
    let onPlay: () -> Void
    let onConvert: () -> Void
    let onDownload: () -> Void
    let onViewContent: () -> Void
    let baseURL: String

    var body: some View {
        HStack {
            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(isSelected ? .blue : .secondary)
                .onTapGesture { onTap() }

            VStack(alignment: .leading, spacing: 2) {
                Text(chapter.title ?? "第\(chapter.chapter_number)章")
                    .font(.body)
                HStack(spacing: 8) {
                    Text("\(chapter.word_count) 字")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if let duration = chapter.audio_duration {
                        Text(formatDuration(duration))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if isConverting {
                        Text("转换中...")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    } else {
                        StatusBadge(status: chapter.status)
                    }
                }

                if isConverting, let p = progress {
                    VStack(alignment: .leading, spacing: 2) {
                        ProgressView(value: p.progress, total: 1.0)
                            .tint(.orange)
                        Text(p.message)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }
            }

            Spacer()

            HStack(spacing: 12) {
                Button { onViewContent() } label: {
                    Image(systemName: "doc.text")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                
                if chapter.status == "completed" && !isConverting {
                    Button { onPlay() } label: {
                        Image(systemName: "play.circle.fill")
                            .font(.title2)
                            .foregroundStyle(.blue)
                    }
                    .buttonStyle(.plain)
                    
                    Button { onDownload() } label: {
                        Image(systemName: "arrow.down.circle.fill")
                            .font(.title2)
                            .foregroundStyle(.green)
                    }
                    .buttonStyle(.plain)
                }

                if isConverting {
                    ProgressView()
                        .scaleEffect(0.7)
                } else {
                    Button { onConvert() } label: {
                        Image(systemName: "arrow.triangle.2.circlepath")
                            .foregroundStyle(.orange)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(.vertical, 2)
    }

    private func formatDuration(_ seconds: Double) -> String {
        let m = Int(seconds) / 60
        let s = Int(seconds) % 60
        return String(format: "%d:%02d", m, s)
    }
}

struct StatusBadge: View {
    let status: String

    var body: some View {
        Text(label)
            .font(.caption2)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .foregroundStyle(color)
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }

    private var label: String {
        switch status {
        case "pending": return "待转换"
        case "queued": return "排队中"
        case "converting": return "转换中"
        case "completed": return "已完成"
        case "failed": return "失败"
        default: return status
        }
    }

    private var color: Color {
        switch status {
        case "completed": return .green
        case "converting": return .orange
        case "queued": return .yellow
        case "failed": return .red
        default: return .secondary
        }
    }
}
