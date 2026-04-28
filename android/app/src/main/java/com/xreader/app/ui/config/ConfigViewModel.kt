package com.xreader.app.ui.config

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.*
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ConfigUiState(
    val config: ConfigResponse? = null,
    val isLoading: Boolean = false,
    val serverUrl: String = "",
    val isConnected: Boolean = false,
    val authEnabled: Boolean = false,
    val authKey: String = "",
    val newAuthKey: String = "",
    val authMessage: String? = null,
    val authLoading: Boolean = false,
    val error: String? = null,
    val message: String? = null
)

@HiltViewModel
class ConfigViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ConfigUiState())
    val uiState: StateFlow<ConfigUiState> = _uiState.asStateFlow()

    init {
        loadConfig()
    }

    fun loadConfig() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val url = repository.getServerUrl()
                val config = repository.getConfig()
                val authStatus = repository.getAuthStatus()
                _uiState.value = _uiState.value.copy(
                    config = config,
                    serverUrl = url,
                    isConnected = true,
                    authEnabled = authStatus.enabled,
                    isLoading = false,
                    error = null
                )
            } catch (e: Exception) {
                val url = try { repository.getServerUrl() } catch (_: Exception) { "" }
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    serverUrl = url,
                    isConnected = false,
                    error = e.message
                )
            }
        }
    }

    fun updateServerUrl(url: String) {
        _uiState.value = _uiState.value.copy(serverUrl = url)
    }

    fun testConnection() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                repository.setServerUrl(_uiState.value.serverUrl)
                loadConfig()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isConnected = false,
                    error = "连接失败: ${e.message}"
                )
            }
        }
    }

    fun updateAuthKey(key: String) { _uiState.value = _uiState.value.copy(authKey = key) }
    fun updateNewAuthKey(key: String) { _uiState.value = _uiState.value.copy(newAuthKey = key) }

    fun enableAuth() {
        val key = _uiState.value.newAuthKey
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(authLoading = true, authMessage = null)
            try {
                val salt = (1..16).map { "%02x".format((0..255).random()) }.joinToString("")
                val keyHash = com.xreader.app.ui.auth.AuthViewModel.sha256(salt + key)
                val result = repository.enableAuth(AuthEnableRequest(keyHash = keyHash, keySalt = salt))
                _uiState.value = _uiState.value.copy(
                    authLoading = false,
                    authMessage = if (result.success) "认证已启用" else result.message,
                    newAuthKey = if (result.success) "" else _uiState.value.newAuthKey
                )
                if (result.success) {
                    val authStatus = repository.getAuthStatus()
                    _uiState.value = _uiState.value.copy(authEnabled = authStatus.enabled)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    authLoading = false,
                    authMessage = "启用失败: ${e.message}"
                )
            }
        }
    }

    fun disableAuth() {
        val key = _uiState.value.authKey
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(authLoading = true, authMessage = null)
            try {
                val challenge = repository.getAuthChallenge()
                val keyHash = com.xreader.app.ui.auth.AuthViewModel.sha256(challenge.salt + key)
                val response = com.xreader.app.ui.auth.AuthViewModel.hmacSha256(keyHash, "${challenge.nonce}${challenge.timestamp}")
                val result = repository.disableAuth(AuthDisableRequest(response = response, timestamp = challenge.timestamp))
                if (result.success) {
                    repository.tokenStore.clear()
                    _uiState.value = _uiState.value.copy(
                        authLoading = false,
                        authMessage = "认证已停用",
                        authKey = "",
                        authEnabled = false
                    )
                } else {
                    _uiState.value = _uiState.value.copy(authLoading = false, authMessage = result.message)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    authLoading = false,
                    authMessage = "停用失败: ${e.message}"
                )
            }
        }
    }

    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
    fun clearMessage() { _uiState.value = _uiState.value.copy(message = null, authMessage = null) }
}
