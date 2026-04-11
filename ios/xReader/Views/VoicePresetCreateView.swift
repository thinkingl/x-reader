import SwiftUI

struct VoicePresetCreateView: View {
    let client: APIClient
    let onSave: () -> Void

    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var voiceMode = "design"
    @State private var instruct = ""
    @State private var language = ""
    @State private var numStep = 32
    @State private var guidanceScale = 2.0
    @State private var speed = 1.0
    @State private var refText = ""
    @State private var isSaving = false
    @State private var error: String?
    @State private var showingAudioPicker = false
    @State private var refAudioPath: String?

    private let voiceModes = ["design", "clone", "auto"]

    var body: some View {
        NavigationStack {
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
                        Button {
                            showingAudioPicker = true
                        } label: {
                            Label(refAudioPath != nil ? "已选择参考音频" : "上传参考音频", systemImage: "waveform")
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
            }
            .navigationTitle("新建预设")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") { Task { await save() } }
                        .disabled(name.isEmpty || isSaving)
                }
            }
            .sheet(isPresented: $showingAudioPicker) {
                AudioPicker { url in
                    showingAudioPicker = false
                    Task { await uploadReferenceAudio(fileURL: url) }
                }
            }
            .alert("错误", isPresented: .init(
                get: { error != nil },
                set: { if !$0 { error = nil } }
            )) {
                Button("确定") { error = nil }
            } message: {
                Text(error ?? "")
            }
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let body = VoicePresetCreate(
                name: name,
                is_default: false,
                voice_mode: voiceMode,
                instruct: voiceMode == "design" ? instruct : nil,
                ref_audio_path: voiceMode == "clone" ? refAudioPath : nil,
                ref_text: voiceMode == "clone" ? refText : nil,
                num_step: numStep,
                guidance_scale: guidanceScale,
                speed: speed,
                language: voiceMode == "design" && !language.isEmpty ? language : nil
            )
            let _: VoicePresetResponse = try await client.post(APIEndpoints.voicePresets, body: body)
            onSave()
        } catch {
            self.error = "保存失败: \(error.localizedDescription)"
        }
    }

    private func uploadReferenceAudio(fileURL: URL) async {
        do {
            let data = try await client.uploadFile(
                path: APIEndpoints.uploadReference,
                fileURL: fileURL,
                fieldName: "file"
            )
            let result = try JSONDecoder().decode(ReferenceUploadResponse.self, from: data)
            refAudioPath = result.audio_path
            if !result.transcribed_text.isEmpty {
                refText = result.transcribed_text
            }
        } catch {
            self.error = "上传失败: \(error.localizedDescription)"
        }
    }

    private func modeLabel(_ mode: String) -> String {
        switch mode {
        case "design": return "语音设计"
        case "clone": return "语音克隆"
        case "auto": return "自动语音"
        default: return mode
        }
    }
}

private struct ReferenceUploadResponse: Codable {
    let success: Bool
    let audio_path: String
    let audio_url: String
    let transcribed_text: String
    let duration: Double
    let message: String
}
