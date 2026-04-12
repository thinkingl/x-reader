import SwiftUI

struct VoicePresetEditView: View {
    let client: APIClient
    let preset: VoicePresetResponse
    let onSave: () -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var name: String
    @State private var voiceMode: String
    @State private var instruct: String
    @State private var language: String
    @State private var numStep: Int
    @State private var guidanceScale: Double
    @State private var speed: Double
    @State private var refText: String
    @State private var isSaving = false
    @State private var error: String?

    // Test state
    @State private var testText = "这是一段测试语音，用于验证当前预设的效果。"
    @State private var isTesting = false
    @State private var testResult: TestAudioResult?
    @State private var testMessage: String?
    @StateObject private var player = AudioPlayerService()

    private let voiceModes = ["clone", "design", "auto"]

    init(client: APIClient, preset: VoicePresetResponse, onSave: @escaping () -> Void) {
        self.client = client
        self.preset = preset
        self.onSave = onSave
        _name = State(initialValue: preset.name)
        _voiceMode = State(initialValue: preset.voice_mode)
        _instruct = State(initialValue: preset.instruct ?? "")
        _language = State(initialValue: preset.language ?? "")
        _numStep = State(initialValue: preset.num_step)
        _guidanceScale = State(initialValue: preset.guidance_scale)
        _speed = State(initialValue: preset.speed)
        _refText = State(initialValue: preset.ref_text ?? "")
    }

    var body: some View {
        Form {
            Section("基本信息") {
                TextField("预设名称", text: $name)
                Picker("语音模式", selection: $voiceMode) {
                    ForEach(voiceModes, id: \.self) { mode in
                        Text(modeLabel(mode)).tag(mode)
                    }
                }
            }

            if voiceMode == "design" {
                Section("语音设计") {
                    TextField("指令（如：female, young adult）", text: $instruct, axis: .vertical)
                        .lineLimit(2...4)
                    TextField("语言（如：zh）", text: $language)
                }
            }

            if voiceMode == "clone" {
                Section("语音克隆") {
                    if let path = preset.ref_audio_path {
                        Label(path, systemImage: "waveform")
                    }
                    TextField("参考文本", text: $refText, axis: .vertical)
                        .lineLimit(3...6)
                }
            }

            Section("生成参数") {
                Stepper("解码步数: \(numStep)", value: $numStep, in: 1...64, step: 16)
                HStack {
                    Text("引导强度")
                    Slider(value: $guidanceScale, in: 1.0...3.0, step: 0.1)
                    Text(String(format: "%.1f", guidanceScale))
                        .foregroundStyle(.secondary)
                        .frame(width: 36)
                }
                HStack {
                    Text("语速")
                    Slider(value: $speed, in: 0.5...2.0, step: 0.1)
                    Text(String(format: "%.1f", speed))
                        .foregroundStyle(.secondary)
                        .frame(width: 36)
                }
            }

            Section("测试预设效果") {
                TextField("测试文本", text: $testText, axis: .vertical)
                    .lineLimit(2...4)

                HStack(spacing: 12) {
                    Button {
                        Task { await testPreset() }
                    } label: {
                        Label(isTesting ? "生成中..." : "生成语音", systemImage: "waveform.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(testText.isEmpty || isTesting)
                }

                if let msg = testMessage {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if let result = testResult, result.success {
                    HStack {
                        Text(String(format: "时长: %.1f 秒", result.duration))
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Spacer()

                        Button {
                            Task { await playTestAudio(result: result) }
                        } label: {
                            Label(player.isPlaying ? "播放中" : "播放", systemImage: player.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                        }
                        .buttonStyle(.bordered)

                        if player.isPlaying {
                            Button {
                                player.stop()
                            } label: {
                                Image(systemName: "stop.circle.fill")
                                    .foregroundStyle(.red)
                            }
                            .buttonStyle(.bordered)
                        }
                    }

                    if player.isPlaying {
                        VStack(spacing: 4) {
                            ProgressView(value: player.currentTime, total: max(player.duration, 1))
                                .tint(.blue)
                            HStack {
                                Text(formatTime(player.currentTime))
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(formatTime(player.duration))
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("编辑预设")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("保存") { Task { await save() } }
                    .disabled(name.isEmpty || isSaving)
            }
        }
        .alert("错误", isPresented: Binding(
            get: { error != nil },
            set: { if !$0 { error = nil } }
        )) {
            Button("确定") { error = nil }
        } message: {
            if let msg = error { Text(msg) }
        }
    }

    private func testPreset() async {
        isTesting = true
        testResult = nil
        testMessage = nil
        defer { isTesting = false }
        do {
            let boundary = UUID().uuidString
            var request = URLRequest(url: URL(string: client.baseURL + APIEndpoints.configTest)!)
            request.httpMethod = "POST"
            request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
            if let token = client.authToken {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            var body = Data()
            let fields: [(String, String)] = [
                ("text", testText),
                ("voice_preset_id", String(preset.id)),
            ]
            for (key, value) in fields {
                body.append("--\(boundary)\r\n".data(using: .utf8)!)
                body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n".data(using: .utf8)!)
                body.append("\(value)\r\n".data(using: .utf8)!)
            }
            body.append("--\(boundary)--\r\n".data(using: .utf8)!)
            request.httpBody = body

            let (data, _) = try await URLSession.shared.data(for: request)
            let result = try JSONDecoder().decode(TestAudioResult.self, from: data)
            testResult = result
            testMessage = result.message
        } catch let e {
            testMessage = "生成失败: \(e.localizedDescription)"
        }
    }

    private func playTestAudio(result: TestAudioResult) async {
        guard let audioURL = result.audio_url,
              let url = URL(string: client.baseURL + audioURL) else {
            testMessage = "无效的音频地址"
            return
        }
        player.play(url: url, title: testText, bookTitle: preset.name)
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let body = VoicePresetUpdate(
                name: name,
                is_default: nil,
                voice_mode: voiceMode,
                instruct: voiceMode == "design" ? instruct : nil,
                ref_audio_path: nil,
                ref_text: voiceMode == "clone" ? refText : nil,
                num_step: numStep,
                guidance_scale: guidanceScale,
                speed: speed,
                language: voiceMode == "design" && !language.isEmpty ? language : nil
            )
            let _: VoicePresetResponse = try await client.put(APIEndpoints.voicePreset(preset.id), body: body)
            onSave()
            dismiss()
        } catch let e {
            self.error = "保存失败: \(e.localizedDescription)"
        }
    }

    private func modeLabel(_ mode: String) -> String {
        switch mode {
        case "clone": return "语音克隆"
        case "design": return "语音设计"
        case "auto": return "自动语音"
        default: return mode
        }
    }

    private func formatTime(_ seconds: Double) -> String {
        let m = Int(seconds) / 60
        let s = Int(seconds) % 60
        return String(format: "%d:%02d", m, s)
    }
}

private struct TestAudioResult: Codable {
    let success: Bool
    let audio_url: String?
    let duration: Double
    let message: String
}
