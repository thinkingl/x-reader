import Foundation

struct AuthStatusResponse: Codable {
    let enabled: Bool
    let has_key: Bool
}

struct AuthChallengeResponse: Codable {
    let nonce: String
    let timestamp: Int
    let salt: String
}

struct AuthVerifyRequest: Codable {
    let response: String
    let timestamp: Int
}

struct AuthEnableRequest: Codable {
    let key_hash: String
    let key_salt: String
}

struct AuthDisableRequest: Codable {
    let response: String
    let timestamp: Int
}

struct AuthResponse: Codable {
    let success: Bool
    let message: String
    let token: String?
    let expires_in: Int?
}
