import Foundation

final class APIClient {
    let baseURL: String

    init(baseURL: String) {
        self.baseURL = baseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    }

    // MARK: - Generic JSON request

    func get<T: Decodable>(_ path: String, queryItems: [URLQueryItem]? = nil) async throws -> T {
        let data = try await request(path: path, method: "GET", queryItems: queryItems)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func post<T: Decodable>(_ path: String, body: Encodable? = nil as String?) async throws -> T {
        let bodyData: Data?
        if let body {
            let encoder = JSONEncoder()
            bodyData = try encoder.encode(AnyEncodable(body))
        } else {
            bodyData = nil
        }
        let data = try await request(path: path, method: "POST", body: bodyData)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func put<T: Decodable>(_ path: String, body: Encodable) async throws -> T {
        let data = try await request(path: path, method: "PUT", body: try JSONEncoder().encode(body))
        return try JSONDecoder().decode(T.self, from: data)
    }

    func patch<T: Decodable>(_ path: String, body: Encodable? = nil as String?) async throws -> T {
        let bodyData: Data?
        if let body {
            bodyData = try JSONEncoder().encode(AnyEncodable(body))
        } else {
            bodyData = nil
        }
        let data = try await request(path: path, method: "PATCH", body: bodyData)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func delete(_ path: String) async throws -> [String: String] {
        let data = try await request(path: path, method: "DELETE")
        return try JSONDecoder().decode([String: String].self, from: data)
    }

    // MARK: - Multipart upload

    func uploadFile(path: String, fileURL: URL, fieldName: String, formFields: [String: String] = [:]) async throws -> Data {
        let boundary = UUID().uuidString
        var request = try makeRequest(path: path, method: "POST")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let fileData = try Data(contentsOf: fileURL)
        var body = Data()

        for (key, value) in formFields {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(fileURL.lastPathComponent)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response, data: data)
        return data
    }

    // MARK: - Download

    func download(_ path: String) async throws -> URL {
        let request = try makeRequest(path: path, method: "GET")
        let (tempURL, response) = try await URLSession.shared.download(for: request)
        try validateResponse(response)

        let dest = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "_" + URL(string: baseURL + path)!.lastPathComponent)
        try FileManager.default.moveItem(at: tempURL, to: dest)
        return dest
    }

    // MARK: - Private

    private func request(path: String, method: String, queryItems: [URLQueryItem]? = nil, body: Data? = nil) async throws -> Data {
        var request = try makeRequest(path: path, method: method, queryItems: queryItems)
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response, data: data)
        return data
    }

    private func makeRequest(path: String, method: String, queryItems: [URLQueryItem]? = nil) throws -> URLRequest {
        guard var components = URLComponents(string: baseURL + path) else {
            throw APIError.invalidURL
        }
        if let queryItems, !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        return request
    }

    private func validateResponse(_ response: URLResponse, data: Data? = nil) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        if http.statusCode >= 400 {
            let message: String
            if let data, let body = try? JSONDecoder().decode([String: String].self, from: data) {
                message = body["detail"] ?? body["message"] ?? "HTTP \(http.statusCode)"
            } else {
                message = "HTTP \(http.statusCode)"
            }
            throw APIError.httpError(statusCode: http.statusCode, message: message)
        }
    }
}

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, message: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "无效的 URL"
        case .invalidResponse: return "服务器响应无效"
        case .httpError(_, let message): return message
        }
    }
}

private struct AnyEncodable: Encodable {
    private let encodeClosure: (Encoder) throws -> Void

    init(_ value: any Encodable) {
        encodeClosure = value.encode
    }

    func encode(to encoder: Encoder) throws {
        try encodeClosure(encoder)
    }
}
