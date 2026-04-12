import SwiftUI
import CommonCrypto

struct LoginView: View {
    let client: APIClient
    let settings: SettingsStore
    let onLoginSuccess: () -> Void

    @State private var authKey = ""
    @State private var isLoading = false
    @State private var showError = false
    @State private var errorMessage = ""

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "lock.circle.fill")
                .font(.system(size: 80))
                .foregroundStyle(.blue)

            Text("x-reader 认证")
                .font(.largeTitle.bold())

            Text("请输入认证密钥")
                .foregroundStyle(.secondary)

            SecureField("认证密钥", text: $authKey)
                .textFieldStyle(.roundedBorder)
                .padding(.horizontal, 40)

            Button {
                Task { await login() }
            } label: {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("登录")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, 40)
            .disabled(authKey.isEmpty || isLoading)

            Spacer()
            Spacer()
        }
        .alert("登录失败", isPresented: $showError) {
            Button("确定") {}
        } message: {
            Text(errorMessage)
        }
    }

    private func login() async {
        isLoading = true
        do {
            let challenge: AuthChallengeResponse = try await client.post("/api/auth/challenge")

            // First compute the key hash (same as stored on server)
            let keyHash = computeSHA256(challenge.salt + authKey)

            // Then compute HMAC response using the key hash
            let response = computeHMAC(key: keyHash, nonce: challenge.nonce, timestamp: challenge.timestamp)

            let verifyRequest = AuthVerifyRequest(response: response, timestamp: challenge.timestamp)
            let result: AuthResponse = try await client.post("/api/auth/verify", body: verifyRequest)

            if result.success, let token = result.token {
                client.authToken = token
                settings.isAuthenticated = true
                onLoginSuccess()
            } else {
                errorMessage = result.message
                showError = true
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
        isLoading = false
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
