package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ChapterResponse(
    val id: Int,
    @SerialName("book_id") val bookId: Int,
    @SerialName("chapter_number") val chapterNumber: Int,
    val title: String? = null,
    @SerialName("text_content") val textContent: String? = null,
    @SerialName("word_count") val wordCount: Int,
    @SerialName("audio_path") val audioPath: String? = null,
    @SerialName("audio_duration") val audioDuration: Double? = null,
    val status: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)
