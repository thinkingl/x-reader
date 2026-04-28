package com.xreader.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class TaskStatus {
    @SerialName("pending") PENDING,
    @SerialName("queued") QUEUED,
    @SerialName("running") RUNNING,
    @SerialName("completed") COMPLETED,
    @SerialName("failed") FAILED,
    @SerialName("skipped") SKIPPED
}

@Serializable
data class TaskCreate(
    @SerialName("book_id") val bookId: Int,
    @SerialName("chapter_ids") val chapterIds: List<Int>? = null,
    @SerialName("voice_preset_id") val voicePresetId: Int? = null,
    val force: Boolean? = null
)

@Serializable
data class TaskResponse(
    val id: Int,
    @SerialName("book_id") val bookId: Int,
    @SerialName("chapter_id") val chapterId: Int,
    @SerialName("voice_preset_id") val voicePresetId: Int? = null,
    val status: TaskStatus,
    @SerialName("error_message") val errorMessage: String? = null,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("finished_at") val finishedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

@Serializable
data class TaskListResponse(
    val items: List<TaskResponse>,
    val total: Int
)

@Serializable
data class TaskProgress(
    @SerialName("task_id") val taskId: Int,
    val status: String,
    val message: String,
    val elapsed: Double,
    val progress: Double
)
