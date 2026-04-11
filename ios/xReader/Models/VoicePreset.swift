import Foundation

struct VoicePresetCreate: Codable {
    let name: String
    let is_default: Bool?
    let voice_mode: String?
    let instruct: String?
    let ref_audio_path: String?
    let ref_text: String?
    let num_step: Int?
    let guidance_scale: Double?
    let speed: Double?
    let language: String?
}

struct VoicePresetUpdate: Codable {
    let name: String?
    let is_default: Bool?
    let voice_mode: String?
    let instruct: String?
    let ref_audio_path: String?
    let ref_text: String?
    let num_step: Int?
    let guidance_scale: Double?
    let speed: Double?
    let language: String?
}

struct VoicePresetResponse: Codable, Identifiable {
    let id: Int
    let name: String
    let is_default: Bool
    let voice_mode: String
    let instruct: String?
    let ref_audio_path: String?
    let ref_text: String?
    let num_step: Int
    let guidance_scale: Double
    let speed: Double
    let language: String?
    let created_at: String
    let updated_at: String
}

struct VoicePresetList: Codable {
    let items: [VoicePresetResponse]
    let total: Int
}
