package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class VoicePresetCreate(
    val name: String,
    @SerialName("is_default") val isDefault: Boolean? = null,
    @SerialName("voice_mode") val voiceMode: String? = null,
    val instruct: String? = null,
    @SerialName("ref_audio_path") val refAudioPath: String? = null,
    @SerialName("ref_text") val refText: String? = null,
    @SerialName("num_step") val numStep: Int? = null,
    @SerialName("guidance_scale") val guidanceScale: Double? = null,
    val speed: Double? = null,
    val language: String? = null
)

@Serializable
data class VoicePresetUpdate(
    val name: String? = null,
    @SerialName("is_default") val isDefault: Boolean? = null,
    @SerialName("voice_mode") val voiceMode: String? = null,
    val instruct: String? = null,
    @SerialName("ref_audio_path") val refAudioPath: String? = null,
    @SerialName("ref_text") val refText: String? = null,
    @SerialName("num_step") val numStep: Int? = null,
    @SerialName("guidance_scale") val guidanceScale: Double? = null,
    val speed: Double? = null,
    val language: String? = null
)

@Serializable
data class VoicePresetResponse(
    val id: Int,
    val name: String,
    @SerialName("is_default") val isDefault: Boolean,
    @SerialName("voice_mode") val voiceMode: String,
    val instruct: String? = null,
    @SerialName("ref_audio_path") val refAudioPath: String? = null,
    @SerialName("ref_text") val refText: String? = null,
    @SerialName("num_step") val numStep: Int,
    @SerialName("guidance_scale") val guidanceScale: Double,
    val speed: Double,
    val language: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

@Serializable
data class VoicePresetListResponse(
    val items: List<VoicePresetResponse>,
    val total: Int
)
