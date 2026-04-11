import SwiftUI

struct ConfigView: View {
    let client: APIClient
    let settings: SettingsStore

    @State private var config: ConfigResponse?
    @State private var serverURL: String = ""
    @State private var isLoading = false
    @State private var error: String?
    @State private var saved = false
    @State private var testText = "这是一个语音合成测试。"
    @State private var testResult: String?
    @State private var isTesting = false

    // Auth state
    @State private var authKey = ""
    @State private var newAuthKey = ""
    @State private var authLoading = false
    @State private var authMessage: String?

    var body: some View {
        Form {
            Section("认证设置") {
                HStack {
                    Text("状态")
                    Spacer()
                    Text(settings.isAuthEnabled ? "已启用" : "未启用")
                        .foregroundStyle(settings.isAuthEnabled ? .green : .secondary)
                }

                if settings.isAuthEnabled {
                    SecureField("当前认证密钥", text: $authKey)
                    Button(role: .destructive) {
                        Task { await disableAuth() }
                    } label: {
                        Label(authLoading ? "处理中..." : "停用认证", systemImage: "lock.open")
                    }
                    .disabled(authKey.isEmpty || authLoading)
                } else {
                    SecureField("设置认证密钥", text: $newAuthKey)
                    Button {
                        Task { await enableAuth() }
                    } label: {
                        Label(authLoading ? "处理中..." : "启用认证", systemImage: "lock")
                    }
                    .disabled(newAuthKey.isEmpty || authLoading)
                }

                if let msg = authMessage {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section("服务器地址") {
                TextField("服务器 URL", text: $serverURL)
                    .autocorrectionDisabled()
                    #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    #endif
                HStack {
                    Button("测试连接") { Task { await testConnection() } }
                        .buttonStyle(.bordered)
                    if settings.isConnected {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                    }
                    if settings.isCheckingConnection {
                        ProgressView()
                    }
                }
            }

            if let config {
                Section("TTS 引擎") {
                    LabeledContent("设备", value: config.device)
                    LabeledContent("精度", value: config.precision)
                    LabeledContent("并发数", value: "\(config.concurrency)")
                }

                Section("音频输出") {
                    LabeledContent("格式", value: config.audio_format.uppercased())
                    LabeledContent("采样率", value: "\(config.sample_rate) Hz")
                    LabeledContent("分块时长", value: String(format: "%.1f s", config.chunk_duration))
                    LabeledContent("分块阈值", value: String(format: "%.1f s", config.chunk_threshold))
                    LabeledContent("文本分段", value: "\(config.chunk_size) 字")
                }

                Section("路径") {
                    LabeledContent("图书目录", value: config.book_dir)
                    LabeledContent("音频目录", value: config.audio_dir)
                }
            }

            Section("测试语音合成") {
                TextField("测试文本", text: $testText, axis: .vertical)
                    .lineLimit(2...4)
                Button {
                    Task { await testTTS() }
                } label: {
                    Label(isTesting ? "生成中..." : "生成测试音频", systemImage: "waveform")
                }
                .disabled(testText.isEmpty || isTesting)

                if let testResult {
                    Text(testResult)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("配置")
        .task {
            serverURL = settings.serverURL
            await loadConfig()
            await settings.checkAuthStatus()
        }
    }

    private func loadConfig() async {
        isLoading = true
        defer { isLoading = false }
        do {
            config = try await client.get(APIEndpoints.config)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func testConnection() async {
        settings.serverURL = serverURL
        await settings.checkConnection()
        if settings.isConnected {
            await loadConfig()
            await settings.checkAuthStatus()
        }
    }

    private func enableAuth() async {
        authLoading = true
        authMessage = nil
        defer { authLoading = false }

        do {
            let salt = (0..<16).map { _ in String(format: "%02x", UInt8.random(in: 0...255)) }.joined()
            let keyHash = computeSHA256(salt + newAuthKey)

            let request = AuthEnableRequest(key_hash: keyHash, key_salt: salt)
            let result: AuthResponse = try await client.post("/api/auth/enable", body: request)

            if result.success {
                authMessage = "认证已启用"
                await settings.checkAuthStatus()
                newAuthKey = ""
            } else {
                authMessage = result.message
            }
        } catch {
            authMessage = "启用失败: \(error.localizedDescription)"
        }
    }

    private func disableAuth() async {
        authLoading = true
        authMessage = nil
        defer { authLoading = false }

        do {
            let challenge: AuthChallengeResponse = try await client.post("/api/auth/challenge")

            // First compute the key hash (same as stored on server)
            let keyHash = computeSHA256(challenge.salt + authKey)

            // Then compute HMAC response using the key hash
            let response = computeHMAC(key: keyHash, nonce: challenge.nonce, timestamp: challenge.timestamp)

            let request = AuthDisableRequest(response: response, timestamp: challenge.timestamp)
            let result: AuthResponse = try await client.post("/api/auth/disable", body: request)

            if result.success {
                authMessage = "认证已停用"
                client.authToken = nil
                settings.isAuthenticated = false
                await settings.checkAuthStatus()
                authKey = ""
            } else {
                authMessage = result.message
            }
        } catch {
            authMessage = "停用失败: \(error.localizedDescription)"
        }
    }

    private func testTTS() async {
        isTesting = true
        defer { isTesting = false }
        do {
            struct TestResult: Decodable {
                let success: Bool
                let audio_url: String?
                let duration: Double
                let message: String
            }
            // Multipart form post
            let formData: [String: String] = ["text": testText]
            let boundary = UUID().uuidString
            var request = URLRequest(url: URL(string: client.baseURL + APIEndpoints.configTest)!)
            request.httpMethod = "POST"
            request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

            if let token = client.authToken {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            var body = Data()
            for (key, value) in formData {
                body.append("--\(boundary)\r\n".data(using: .utf8)!)
                body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n".data(using: .utf8)!)
                body.append("\(value)\r\n".data(using: .utf8)!)
            }
            body.append("--\(boundary)--\r\n".data(using: .utf8)!)
            request.httpBody = body

            let (data, _) = try await URLSession.shared.data(for: request)
            let result = try JSONDecoder().decode(TestResult.self, from: data)
            testResult = result.message
        } catch {
            testResult = "测试失败: \(error.localizedDescription)"
        }
    }

    private func computeHMAC(key: String, nonce: String, timestamp: Int) -> String {
        let message = "\(nonce)\(timestamp)"
        let keyData = Data(key.utf8)
        let messageData = Data(message.utf8)

        var hmac = [UInt8](repeating: 0, count: 32)
        CCHmac(CCHmacAlgorithm(kCCHmacAlgSHA256), keyData.withUnsafeBytes { $0.baseAddress }, keyData.count,
               messageData.withUnsafeBytes { $0.baseAddress }, messageData.count, &hmac)

        return hmac.map { String(format: "%02x", $0) }.joined()
    }

    private func computeSHA256(_ input: String) -> String {
        let data = Data(input.utf8)
        var hash = [UInt8](repeating: 0, count: 32)
        data.withUnsafeBytes { buffer in
            _ = CC_SHA256(buffer.baseAddress, CC_LONG(data.count), &hash)
        }
        return hash.map { String(format: "%02x", $0) }.joined()
    }
}

import CommonCrypto
