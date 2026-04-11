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

    private let voiceModes = ["design", "clone", "auto"]

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
        }
        .navigationTitle("编辑预设")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("保存") { Task { await save() } }
                    .disabled(name.isEmpty || isSaving)
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
        } catch {
            self.error = "保存失败: \(error.localizedDescription)"
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
