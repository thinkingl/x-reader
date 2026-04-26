import SwiftUI
import CommonCrypto

struct ConfigView: View {
    let client: APIClient
    let settings: SettingsStore

    @State private var config: ConfigResponse?
    @State private var serverURL: String = ""
    @State private var isLoading = false
    @State private var error: String?
    @State private var saved = false

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
                    LabeledContent("模式", value: ttsModeLabel(config.tts_mode))
                    LabeledContent("设备", value: config.device)
                    LabeledContent("精度", value: config.precision)
                    LabeledContent("并发数", value: "\(config.concurrency)")
                }

                Section("在线 TTS (MiMo)") {
                    LabeledContent("API 地址", value: config.mimo_base_url)
                        .font(.caption)
                    LabeledContent("模型", value: config.mimo_model)
                    LabeledContent("默认语音", value: config.mimo_default_voice)
                    LabeledContent("API Key", value: config.mimo_api_key.isEmpty ? "未配置" : "已配置")
                }

                Section("文本分段") {
                    LabeledContent("本地分段", value: "\(config.local_chunk_size) 字符")
                    LabeledContent("在线分段", value: "\(config.online_chunk_size) 字符")
                    LabeledContent("本地间隔", value: String(format: "%.1f s", config.local_chunk_gap))
                    LabeledContent("在线间隔", value: String(format: "%.1f s", config.online_chunk_gap))
                }

                Section("音频输出") {
                    LabeledContent("格式", value: config.audio_format.uppercased())
                    LabeledContent("采样率", value: "\(config.sample_rate) Hz")
                }

                Section("路径") {
                    LabeledContent("图书目录", value: config.book_dir)
                    LabeledContent("音频目录", value: config.audio_dir)
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

    private func ttsModeLabel(_ mode: String) -> String {
        switch mode {
        case "local": return "仅本地"
        case "online": return "仅在线"
        case "online_first": return "在线优先"
        default: return mode
        }
    }
}
