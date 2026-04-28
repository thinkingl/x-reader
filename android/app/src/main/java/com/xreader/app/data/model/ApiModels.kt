package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ReferenceUploadResponse(
    val success: Boolean,
    @SerialName("audio_path") val audioPath: String,
    @SerialName("audio_url") val audioUrl: String,
    @SerialName("transcribed_text") val transcribedText: String,
    val duration: Double,
    val message: String
)

@Serializable
data class TestAudioResponse(
    val success: Boolean,
    @SerialName("audio_url") val audioUrl: String? = null,
    val duration: Double,
    val message: String
)

@Serializable
data class MessageResponse(
    val detail: String? = null,
    val message: String? = null
)
