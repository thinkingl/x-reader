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

    var body: some View {
        Form {
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
}
