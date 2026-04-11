import Foundation

enum APIEndpoints {
    // Books
    static let books = "/api/books"
    static let uploadBook = "/api/books/upload"

    static func book(_ id: Int) -> String { "/api/books/\(id)" }
    static func chapters(bookId: Int) -> String { "/api/books/\(bookId)/chapters" }
    static func chapter(_ id: Int) -> String { "/api/chapters/\(id)" }

    // Tasks
    static let tasks = "/api/tasks"
    static func task(_ id: Int) -> String { "/api/tasks/\(id)" }
    static func taskProgress(_ id: Int) -> String { "/api/tasks/\(id)/progress" }
    static func retryTask(_ id: Int) -> String { "/api/tasks/\(id)/retry" }

    // Voice Presets
    static let voicePresets = "/api/voice-presets"
    static func voicePreset(_ id: Int) -> String { "/api/voice-presets/\(id)" }
    static func setDefaultPreset(_ id: Int) -> String { "/api/voice-presets/\(id)/set-default" }
    static let uploadReference = "/api/voice-presets/upload-reference"

    // Audio
    static func audioStream(bookId: Int, chapterId: Int) -> String {
        "/api/audio/\(bookId)/\(chapterId)/stream"
    }
    static func audioDownload(bookId: Int, chapterId: Int) -> String {
        "/api/audio/\(bookId)/\(chapterId)"
    }
    static func audioZip(bookId: Int) -> String { "/api/audio/\(bookId)/zip" }

    // Config
    static let config = "/api/config"
    static let configTest = "/api/config/test"
    static func testAudio(filename: String) -> String { "/api/config/test-audio/\(filename)" }

    // Reference Audio
    static func referenceAudio(filename: String) -> String { "/api/reference-audio/\(filename)" }
}
