import SwiftUI

struct ChapterContentView: View {
    let client: APIClient
    let chapterId: Int
    let chapterTitle: String
    
    @State private var content: String?
    @State private var isLoading = true
    @State private var error: String?
    
    var body: some View {
        ScrollView {
            if isLoading {
                ProgressView("加载中...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .padding(.top, 100)
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
                .padding(.top, 100)
            } else if let content {
                Text(content)
                    .font(.body)
                    .lineSpacing(6)
                    .padding()
            }
        }
        .navigationTitle(chapterTitle)
        .navigationBarTitleDisplayMode(.inline)
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
}
