package com.xreader.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.*
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val isAuthenticated: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun login(authKey: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val challenge = repository.getAuthChallenge()
                val keyHash = sha256(challenge.salt + authKey)
                val response = hmacSha256(keyHash, "${challenge.nonce}${challenge.timestamp}")
                val result = repository.verifyAuth(
                    AuthVerifyRequest(response = response, timestamp = challenge.timestamp)
                )
                if (result.success && result.token != null) {
                    repository.tokenStore.token = result.token
                    _uiState.value = _uiState.value.copy(isLoading = false, isAuthenticated = true)
                    onSuccess()
                } else {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = result.message)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message ?: "登录失败")
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    companion object {
        fun sha256(input: String): String {
            val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray())
            return bytes.joinToString("") { "%02x".format(it) }
        }

        fun hmacSha256(key: String, message: String): String {
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(SecretKeySpec(key.toByteArray(), "HmacSHA256"))
            val bytes = mac.doFinal(message.toByteArray())
            return bytes.joinToString("") { "%02x".format(it) }
        }
    }
}
