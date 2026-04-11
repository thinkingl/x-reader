import SwiftUI

@main
struct XReaderApp: App {
    @State private var settings = SettingsStore()
    @State private var player = AudioPlayerService()

    var body: some Scene {
        WindowGroup {
            if settings.isConnected {
                MainTabView(client: settings.makeAPIClient(), player: player, settings: settings)
            } else {
                ConnectionSetupView(settings: settings)
            }
        }
    }
}

struct ConnectionSetupView: View {
    let settings: SettingsStore

    @State private var url = ""
    @State private var showError = false

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "book.circle.fill")
                .font(.system(size: 80))
                .foregroundStyle(.blue)

            Text("x-reader")
                .font(.largeTitle.bold())

            Text("请输入后端服务器地址")
                .foregroundStyle(.secondary)

            TextField("http://192.168.1.100:8000", text: $url)
                .textFieldStyle(.roundedBorder)
                .autocorrectionDisabled()
                #if os(iOS)
                .keyboardType(.URL)
                .textInputAutocapitalization(.never)
                #endif
                .padding(.horizontal, 40)

            Button {
                Task { await connect() }
            } label: {
                if settings.isCheckingConnection {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("连接")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, 40)
            .disabled(url.isEmpty || settings.isCheckingConnection)

            Spacer()
            Spacer()
        }
        .alert("连接失败", isPresented: $showError) {
            Button("确定") {}
        } message: {
            Text("请检查服务器地址是否正确，后端是否已启动")
        }
        .onAppear {
            url = settings.serverURL
        }
    }

    private func connect() async {
        settings.serverURL = url
        await settings.checkConnection()
        if !settings.isConnected {
            showError = true
        }
    }
}

struct MainTabView: View {
    let client: APIClient
    let player: AudioPlayerService
    let settings: SettingsStore

    var body: some View {
        TabView {
            NavigationStack {
                BookListView(client: client, player: player)
            }
            .tabItem {
                Label("图书", systemImage: "book.fill")
            }

            NavigationStack {
                TaskListView(client: client, player: player)
            }
            .tabItem {
                Label("任务", systemImage: "list.bullet.rectangle")
            }

            NavigationStack {
                VoicePresetListView(client: client)
            }
            .tabItem {
                Label("预设", systemImage: "waveform")
            }

            NavigationStack {
                ConfigView(client: client, settings: settings)
            }
            .tabItem {
                Label("配置", systemImage: "gear")
            }
        }
    }
}
