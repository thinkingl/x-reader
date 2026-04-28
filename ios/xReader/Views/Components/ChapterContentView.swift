import SwiftUI

struct ChapterContentView: View {
    let client: APIClient
    let chapterId: Int
    let chapterTitle: String
    
    @State private var content: String?
    @State private var editContent: String = ""
    @State private var isLoading = true
    @State private var error: String?
    @State private var isEditing = false
    @State private var isSaving = false
    
    var body: some View {
        Group {
            if isLoading {
                ProgressView("加载中...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error {
                VStack {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text(error)
                        .foregroundStyle(.secondary)
                        .padding()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if isEditing {
                TextEditor(text: $editContent)
                    .font(.body)
                    .lineSpacing(6)
                    .padding(.horizontal, 4)
            } else if let content {
                ScrollView {
                    Text(content)
                        .font(.body)
                        .lineSpacing(6)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .navigationTitle(chapterTitle)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                if isEditing {
                    Button {
                        Task { await saveContent() }
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("保存")
                        }
                    }
                    .disabled(isSaving)
                } else if content != nil {
                    Button {
                        editContent = content ?? ""
                        isEditing = true
                    } label: {
                        Text("编辑")
                    }
                }
            }
            if isEditing {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") {
                        isEditing = false
                        editContent = ""
                    }
                }
            }
        }
        .task { await loadContent() }
    }
    
    private func loadContent() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let chapter: ChapterResponse = try await client.get("/api/chapters/\(chapterId)")
            content = chapter.text_content ?? "无内容"
        } catch {
            self.error = "加载失败: \(error.localizedDescription)"
        }
    }
    
    private func saveContent() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let update = ChapterUpdate(title: nil, text_content: editContent)
            let updated: ChapterResponse = try await client.patch("/api/chapters/\(chapterId)", body: update)
            content = updated.text_content ?? ""
            isEditing = false
        } catch {
            self.error = "保存失败: \(error.localizedDescription)"
        }
    }
}
