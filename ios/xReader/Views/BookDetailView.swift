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
    @State private var convertingAll = false
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
                    Label(convertingAll ? "转换中..." : "转换全部未完成章节", systemImage: "play.rectangle.fill")
                }
                .disabled(convertingAll || chapters.allSatisfy { $0.status == "completed" })
            }

            Section("章节 (\(chapters.count))") {
                ForEach(chapters) { chapter in
                    ChapterRow(
                        chapter: chapter,
                        isSelected: selectedChapterIds.contains(chapter.id),
                        onTap: {
                            toggleSelection(chapter.id)
                        },
                        onPlay: {
                            Task { await playChapter(chapter) }
                        },
                        onConvert: {
                            Task { await convertChapters([chapter]) }
                        },
                        baseURL: client.baseURL
                    )
                }
            }
        }
        .navigationTitle(book?.title ?? "图书详情")
        .toolbar {
            if !selectedChapterIds.isEmpty {
                ToolbarItem(placement: .primaryAction) {
                    Button("转换选中 (\(selectedChapterIds.count))") {
                        let selected = chapters.filter { selectedChapterIds.contains($0.id) }
                        Task { await convertChapters(selected) }
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
            async let presetsResult: VoicePresetList = client.get(APIEndpoints.voicePresets)

            let (b, ch, pr) = try await (bookResult, chaptersResult, presetsResult)
            book = b
            chapters = ch
            presets = pr.items
        } catch let e {
            self.errorMessage = e.localizedDescription
        }
    }

    private func convertChapters(_ chapters: [ChapterResponse], skipCompleted: Bool = false) async {
        convertingAll = true
        defer { convertingAll = false }
        do {
            let target = skipCompleted ? chapters.filter { $0.status != "completed" } : chapters
            guard !target.isEmpty else {
                errorMessage = skipCompleted ? "没有需要转换的章节" : "请选择章节"
                return
            }
            let targetIds = target.map { $0.id }
            let body = TaskCreate(
                book_id: bookId,
                chapter_ids: pendingIds,
                voice_preset_id: selectedPresetId
            )
            let _: TaskResponse = try await client.post(APIEndpoints.tasks, body: body)
            polling.startPolling(client: client, bookId: bookId)
            try? await Task.sleep(for: .seconds(2))
            await loadData()
        } catch let e {
            self.errorMessage = "转换失败: \(e.localizedDescription)"
        }
    }

    private func playChapter(_ chapter: ChapterResponse) async {
        let url = client.baseURL + APIEndpoints.audioStream(bookId: bookId, chapterId: chapter.id)
        guard let audioURL = URL(string: url) else { return }
        player.play(url: audioURL, title: chapter.title ?? "第\(chapter.chapter_number)章", bookTitle: book?.title ?? "")
    }
}

struct ChapterRow: View {
    let chapter: ChapterResponse
    let isSelected: Bool
    let onTap: () -> Void
    let onPlay: () -> Void
    let onConvert: () -> Void
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
                    StatusBadge(status: chapter.status)
                }
            }

            Spacer()

            HStack(spacing: 12) {
                if chapter.status == "completed" {
                    Button { onPlay() } label: {
                        Image(systemName: "play.circle.fill")
                            .font(.title2)
                            .foregroundStyle(.blue)
                    }
                    .buttonStyle(.plain)
                }

                Button { onConvert() } label: {
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .foregroundStyle(.orange)
                }
                .buttonStyle(.plain)
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
        case "failed": return .red
        default: return .secondary
        }
    }
}
