package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ConfigResponse(
    @SerialName("tts_mode") val ttsMode: String,
    @SerialName("model_path") val modelPath: String,
    val device: String,
    val precision: String,
    @SerialName("asr_model_path") val asrModelPath: String,
    @SerialName("mimo_api_key") val mimoApiKey: String,
    @SerialName("mimo_base_url") val mimoBaseUrl: String,
    @SerialName("mimo_model") val mimoModel: String,
    @SerialName("mimo_default_voice") val mimoDefaultVoice: String,
    @SerialName("audio_format") val audioFormat: String,
    @SerialName("sample_rate") val sampleRate: Int,
    val concurrency: Int,
    @SerialName("local_chunk_size") val localChunkSize: Int,
    @SerialName("local_chunk_gap") val localChunkGap: Double,
    @SerialName("online_chunk_size") val onlineChunkSize: Int,
    @SerialName("online_chunk_gap") val onlineChunkGap: Double,
    @SerialName("book_dir") val bookDir: String,
    @SerialName("audio_dir") val audioDir: String
)

@Serializable
data class ConfigUpdate(
    @SerialName("tts_mode") val ttsMode: String? = null,
    @SerialName("model_path") val modelPath: String? = null,
    val device: String? = null,
    val precision: String? = null,
    @SerialName("asr_model_path") val asrModelPath: String? = null,
    @SerialName("mimo_api_key") val mimoApiKey: String? = null,
    @SerialName("mimo_base_url") val mimoBaseUrl: String? = null,
    @SerialName("mimo_model") val mimoModel: String? = null,
    @SerialName("mimo_default_voice") val mimoDefaultVoice: String? = null,
    @SerialName("audio_format") val audioFormat: String? = null,
    @SerialName("sample_rate") val sampleRate: Int? = null,
    val concurrency: Int? = null,
    @SerialName("local_chunk_size") val localChunkSize: Int? = null,
    @SerialName("local_chunk_gap") val localChunkGap: Double? = null,
    @SerialName("online_chunk_size") val onlineChunkSize: Int? = null,
    @SerialName("online_chunk_gap") val onlineChunkGap: Double? = null,
    @SerialName("book_dir") val bookDir: String? = null,
    @SerialName("audio_dir") val audioDir: String? = null
)
