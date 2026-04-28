package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class BookResponse(
    val id: Int,
    val title: String,
    val author: String? = null,
    val format: String,
    @SerialName("file_path") val filePath: String,
    @SerialName("cover_path") val coverPath: String? = null,
    @SerialName("chapter_count") val chapterCount: Int,
    val status: String,
    @SerialName("publish_year") val publishYear: Int? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

@Serializable
data class BookListResponse(
    val items: List<BookResponse>,
    val total: Int
)

@Serializable
data class BookUpdate(
    val title: String? = null,
    val author: String? = null
)

@Serializable
data class ReparseResponse(
    val message: String,
    @SerialName("chapter_count") val chapterCount: Int
)
