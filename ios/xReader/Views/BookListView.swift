import SwiftUI

struct BookListView: View {
    let client: APIClient
    let player: AudioPlayerService

    @State private var books: [BookResponse] = []
    @State private var total = 0
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingUpload = false
    @State private var searchText = ""

    var body: some View {
        content
            .navigationTitle("图书")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showingUpload = true } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .overlay {
                if isLoading {
                    ProgressView("加载中...")
                }
            }
            .alert("错误", isPresented: Binding(
                get: { errorMessage != nil },
                set: { if !$0 { errorMessage = nil } }
            )) {
                Button("确定") { errorMessage = nil }
            } message: {
                if let msg = errorMessage { Text(msg) }
            }
            .sheet(isPresented: $showingUpload) {
                EBookPicker { url in
                    showingUpload = false
                    Task { await uploadBook(fileURL: url) }
                }
            }
            .task { await loadBooks() }
            .onChange(of: searchText) { _ in
                Task { await loadBooks() }
            }
            .refreshable { await loadBooks() }
    }

    @ViewBuilder
    private var content: some View {
        if books.isEmpty && !isLoading {
            EmptyPlaceholderView(title: "暂无图书", systemImage: "book.closed", description: "点击右上角 + 上传电子书")
        } else {
            List(books) { book in
                let detail = BookDetailView(client: client, player: player, bookId: book.id)
                NavigationLink(destination: detail) {
                    BookRow(book: book)
                }
            }
            .searchable(text: $searchText, prompt: "搜索书名或作者")
        }
    }

    private func loadBooks() async {
        isLoading = true
        defer { isLoading = false }
        do {
            var query: [URLQueryItem] = []
            if !searchText.isEmpty {
                query.append(URLQueryItem(name: "search", value: searchText))
            }
            let result: BookList = try await client.get(APIEndpoints.books, queryItems: query)
            books = result.items
            total = result.total
        } catch let e {
            errorMessage = e.localizedDescription
        }
    }

    private func uploadBook(fileURL: URL) async {
        isLoading = true
        defer { isLoading = false }
        do {
            let data = try await client.uploadFile(path: APIEndpoints.uploadBook, fileURL: fileURL, fieldName: "file")
            let book: BookResponse = try JSONDecoder().decode(BookResponse.self, from: data)
            books.insert(book, at: 0)
        } catch let e {
            errorMessage = "上传失败: \(e.localizedDescription)"
        }
    }
}

struct BookRow: View {
    let book: BookResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(book.title)
                .font(.headline)
            HStack {
                if let author = book.author {
                    Text(author)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Label("\(book.chapter_count) 章", systemImage: "doc.text")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            HStack {
                Text(book.format.uppercased())
                    .font(.caption2)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(.blue.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(statusColor)
                Spacer()
                if let date = ISO8601DateFormatter().date(from: book.created_at) {
                    Text(date, style: .relative)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var statusText: String {
        switch book.status {
        case "parsed": return "已解析"
        case "completed": return "已完成"
        default: return book.status
        }
    }

    private var statusColor: Color {
        switch book.status {
        case "completed": return .green
        case "parsed": return .blue
        default: return .secondary
        }
    }
}
