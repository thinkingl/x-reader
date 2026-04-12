import SwiftUI

struct VoicePresetListView: View {
    let client: APIClient

    @State private var presets: [VoicePresetResponse] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var showingCreate = false

    var body: some View {
        List {
            ForEach(presets) { preset in
                NavigationLink(destination: VoicePresetEditView(client: client, preset: preset, onSave: { Task { await loadPresets() } })) {
                    VoicePresetRow(preset: preset)
                }
            }
            .onDelete { indexSet in
                let preset = presets[indexSet.first!]
                Task { await deletePreset(preset) }
            }
        }
        .navigationTitle("语音预设")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { showingCreate = true } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingCreate) {
            VoicePresetCreateView(client: client, onSave: {
                showingCreate = false
                Task { await loadPresets() }
            })
        }
        .overlay {
            if presets.isEmpty && !isLoading {
                EmptyPlaceholderView(title: "暂无预设", systemImage: "waveform", description: "点击 + 创建语音预设")
            }
        }
        .task { await loadPresets() }
        .refreshable { await loadPresets() }
        .alert("错误", isPresented: .init(
            get: { error != nil },
            set: { if !$0 { error = nil } }
        )) {
            Button("确定") { error = nil }
        } message: {
            Text(error ?? "")
        }
    }

    private func loadPresets() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let result: VoicePresetList = try await client.get(APIEndpoints.voicePresets)
            presets = result.items
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func deletePreset(_ preset: VoicePresetResponse) async {
        do {
            let _: [String: String] = try await client.delete(APIEndpoints.voicePreset(preset.id))
            presets.removeAll { $0.id == preset.id }
        } catch {
            self.error = "删除失败: \(error.localizedDescription)"
        }
    }
}

struct VoicePresetRow: View {
    let preset: VoicePresetResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(preset.name)
                    .font(.headline)
                if preset.is_default {
                    Text("默认")
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.blue.opacity(0.15))
                        .foregroundStyle(.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
                Spacer()
            }
            HStack {
                Text(preset.voice_mode.capitalized)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if let instruct = preset.instruct {
                    Text(instruct)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
