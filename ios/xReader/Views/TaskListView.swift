import SwiftUI

struct TaskListView: View {
    let client: APIClient
    let player: AudioPlayerService

    @State private var tasks: [TaskResponse] = []
    @State private var total = 0
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var statusFilter: String?

    private let statusOptions: [(String?, String)] = [
        (nil, "全部"),
        ("pending", "待处理"),
        ("queued", "排队中"),
        ("running", "进行中"),
        ("completed", "已完成"),
        ("failed", "失败"),
    ]

    var body: some View {
        List(tasks) { task in
            TaskRow(task: task, onRetry: {
                Task { await retryTask(task) }
            }, onCancel: {
                Task { await cancelTask(task) }
            })
        }
        .navigationTitle("任务")
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Menu {
                    ForEach(statusOptions, id: \.0) { value, label in
                        Button {
                            statusFilter = value
                            Task { await loadTasks() }
                        } label: {
                            HStack {
                                Text(label)
                                if statusFilter == value {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                } label: {
                    Label("筛选", systemImage: "line.3.horizontal.decrease.circle")
                }
            }
        }
        .overlay {
            if isLoading {
                ProgressView()
            }
            if tasks.isEmpty && !isLoading {
                EmptyPlaceholderView(title: "暂无任务", systemImage: "list.bullet.rectangle")
            }
        }
        .task { await loadTasks() }
        .refreshable { await loadTasks() }
        .alert("错误", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("确定") { errorMessage = nil }
        } message: {
            if let msg = errorMessage { Text(msg) }
        }
    }

    private func loadTasks() async {
        isLoading = true
        defer { isLoading = false }
        do {
            var query: [URLQueryItem] = []
            if let statusFilter {
                query.append(URLQueryItem(name: "status", value: statusFilter))
            }
            let result: TaskList = try await client.get(APIEndpoints.tasks, queryItems: query)
            tasks = result.items
            total = result.total
        } catch let e {
            errorMessage = e.localizedDescription
        }
    }

    private func retryTask(_ task: TaskResponse) async {
        do {
            let _: TaskResponse = try await client.post(APIEndpoints.retryTask(task.id))
            await loadTasks()
        } catch let e {
            errorMessage = "重试失败: \(e.localizedDescription)"
        }
    }

    private func cancelTask(_ task: TaskResponse) async {
        do {
            let _: [String: String] = try await client.delete(APIEndpoints.task(task.id))
            await loadTasks()
        } catch let e {
            errorMessage = "取消失败: \(e.localizedDescription)"
        }
    }
}

struct TaskRow: View {
    let task: TaskResponse
    let onRetry: () -> Void
    let onCancel: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                StatusBadge(status: task.status.rawValue)
                Spacer()
                if let date = ISO8601DateFormatter().date(from: task.created_at) {
                    Text(date, style: .relative)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }

            HStack {
                Text("图书 #\(task.book_id) · 章节 #\(task.chapter_id)")
                    .font(.subheadline)
                Spacer()
                if task.status == .failed || task.status == .skipped {
                    Button("重试", action: onRetry)
                        .font(.caption)
                        .buttonStyle(.bordered)
                }
                if task.status == .pending || task.status == .queued {
                    Button("取消", action: onCancel)
                        .font(.caption)
                        .buttonStyle(.bordered)
                        .tint(.red)
                }
            }

            if let errorMsg = task.error_message {
                Text(errorMsg)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}
