import Foundation

struct ConfigUpdate: Codable {
    // TTS 模式
    let tts_mode: String?
    
    // 本地模型配置
    let model_path: String?
    let device: String?
    let precision: String?
    let asr_model_path: String?
    
    // 在线 API 配置 (MiMo)
    let mimo_api_key: String?
    let mimo_base_url: String?
    let mimo_model: String?
    let mimo_default_voice: String?
    
    // 音频输出配置
    let audio_format: String?
    let sample_rate: Int?
    let concurrency: Int?
    
    // 本地模型分段配置
    let local_chunk_size: Int?
    let local_chunk_gap: Double?
    
    // 在线 API 分段配置
    let online_chunk_size: Int?
    let online_chunk_gap: Double?
    
    // 目录配置
    let book_dir: String?
    let audio_dir: String?
}

struct ConfigResponse: Codable {
    // TTS 模式
    let tts_mode: String
    
    // 本地模型配置
    let model_path: String
    let device: String
    let precision: String
    let asr_model_path: String
    
    // 在线 API 配置 (MiMo)
    let mimo_api_key: String
    let mimo_base_url: String
    let mimo_model: String
    let mimo_default_voice: String
    
    // 音频输出配置
    let audio_format: String
    let sample_rate: Int
    let concurrency: Int
    
    // 本地模型分段配置
    let local_chunk_size: Int
    let local_chunk_gap: Double
    
    // 在线 API 分段配置
    let online_chunk_size: Int
    let online_chunk_gap: Double
    
    // 目录配置
    let book_dir: String
    let audio_dir: String
}
