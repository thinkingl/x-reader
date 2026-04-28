package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AuthStatusResponse(
    val enabled: Boolean,
    @SerialName("has_key") val hasKey: Boolean
)

@Serializable
data class AuthChallengeResponse(
    val nonce: String,
    val timestamp: Long,
    val salt: String
)

@Serializable
data class AuthVerifyRequest(
    val response: String,
    val timestamp: Long
)

@Serializable
data class AuthEnableRequest(
    @SerialName("key_hash") val keyHash: String,
    @SerialName("key_salt") val keySalt: String
)

@Serializable
data class AuthDisableRequest(
    val response: String,
    val timestamp: Long
)

@Serializable
data class AuthResponse(
    val success: Boolean,
    val message: String,
    val token: String? = null,
    @SerialName("expires_in") val expiresIn: Int? = null
)
