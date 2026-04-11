import Foundation
import SwiftUI

@Observable
class SettingsStore {
    static let serverURLKey = "serverURL"

    var serverURL: String {
        didSet {
            UserDefaults.standard.set(serverURL, forKey: Self.serverURLKey)
        }
    }

    init() {
        self.serverURL = UserDefaults.standard.string(forKey: Self.serverURLKey) ?? "http://localhost:8000"
    }

    func makeAPIClient() -> APIClient {
        APIClient(baseURL: serverURL)
    }

    var isConnected: Bool = false
    var isCheckingConnection: Bool = false

    @MainActor
    func checkConnection() async {
        isCheckingConnection = true
        let client = makeAPIClient()
        do {
            let _: ConfigResponse = try await client.get(APIEndpoints.config)
            isConnected = true
        } catch {
            isConnected = false
        }
        isCheckingConnection = false
    }
}
