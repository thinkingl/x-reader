import Foundation

struct ConfigUpdate: Codable {
    let model_path: String?
    let device: String?
    let precision: String?
    let asr_model_path: String?
    let concurrency: Int?
    let audio_format: String?
    let sample_rate: Int?
    let chunk_duration: Double?
    let chunk_threshold: Double?
    let chunk_size: Int?
    let book_dir: String?
    let audio_dir: String?
}

struct ConfigResponse: Codable {
    let model_path: String
    let device: String
    let precision: String
    let asr_model_path: String
    let concurrency: Int
    let audio_format: String
    let sample_rate: Int
    let chunk_duration: Double
    let chunk_threshold: Double
    let chunk_size: Int
    let book_dir: String
    let audio_dir: String
}
