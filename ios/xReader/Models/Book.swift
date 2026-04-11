import Foundation

struct BookResponse: Codable, Identifiable {
    let id: Int
    let title: String
    let author: String?
    let format: String
    let file_path: String
    let cover_path: String?
    let chapter_count: Int
    let status: String
    let publish_year: Int?
    let created_at: String
    let updated_at: String
}

struct BookList: Codable {
    let items: [BookResponse]
    let total: Int
}
