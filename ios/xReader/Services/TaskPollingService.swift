import Foundation
import SwiftUI

class TaskPollingService: ObservableObject {
    @Published var activeTasks: [Int: TaskProgress] = [:]
    @Published var isPolling = false

    private var pollingTask: Task<Void, Never>?

    @MainActor
    func startPolling(client: APIClient, bookId: Int) {
        stop()
        isPolling = true
        pollingTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.fetchProgress(client: client, bookId: bookId)
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    @MainActor
    func startPollingSingleTask(client: APIClient, taskId: Int) {
        stop()
        isPolling = true
        pollingTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                do {
                    let progress: TaskProgress = try await client.get(APIEndpoints.taskProgress(taskId))
                    await MainActor.run {
                        self.activeTasks[taskId] = progress
                    }
                    if progress.status == "completed" || progress.status == "failed" {
                        break
                    }
                } catch {
                    break
                }
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    func stop() {
        pollingTask?.cancel()
        pollingTask = nil
        isPolling = false
    }

    private func fetchProgress(client: APIClient, bookId: Int) async {
        do {
            let taskList: TaskList = try await client.get(
                APIEndpoints.tasks,
                queryItems: [
                    URLQueryItem(name: "book_id", value: String(bookId)),
                    URLQueryItem(name: "status", value: "running"),
                ]
            )
            for task in taskList.items {
                let progress: TaskProgress = try await client.get(APIEndpoints.taskProgress(task.id))
                await MainActor.run {
                    self.activeTasks[task.id] = progress
                }
            }
        } catch {
            // Silently continue polling
        }
    }
}
