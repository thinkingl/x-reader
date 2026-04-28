import Foundation

struct ChapterResponse: Codable, Identifiable {
    let id: Int
    let book_id: Int
    let chapter_number: Int
    let title: String?
    let text_content: String?
    let word_count: Int
    let audio_path: String?
    let audio_duration: Double?
    let status: String
    let created_at: String
    let updated_at: String
}

struct ChapterUpdate: Codable {
    let title: String?
    let text_content: String?
}
