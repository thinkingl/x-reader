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
    var isAuthenticated: Bool = false
    var isAuthEnabled: Bool = false
    var isCheckingAuth: Bool = false

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

    @MainActor
    func checkAuthStatus() async {
        isCheckingAuth = true
        let client = makeAPIClient()
        do {
            let status: AuthStatusResponse = try await client.get("/api/auth/status")
            isAuthEnabled = status.enabled
            isAuthenticated = client.authToken != nil
        } catch {
            isAuthEnabled = false
            isAuthenticated = false
        }
        isCheckingAuth = false
    }

    func logout() {
        let client = makeAPIClient()
        client.authToken = nil
        isAuthenticated = false
    }
}
