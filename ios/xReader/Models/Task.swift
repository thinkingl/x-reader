import Foundation

enum TaskStatusEnum: String, Codable {
    case pending
    case running
    case completed
    case failed
    case skipped
}

struct TaskCreate: Codable {
    let book_id: Int
    let chapter_ids: [Int]?
    let voice_preset_id: Int?
}

struct TaskResponse: Codable, Identifiable {
    let id: Int
    let book_id: Int
    let chapter_id: Int
    let voice_preset_id: Int?
    let status: TaskStatusEnum
    let error_message: String?
    let started_at: String?
    let finished_at: String?
    let created_at: String
    let updated_at: String
}

struct TaskList: Codable {
    let items: [TaskResponse]
    let total: Int
}

struct TaskProgress: Codable {
    let task_id: Int
    let status: String
    let message: String
    let elapsed: Double
    let progress: Double
}
