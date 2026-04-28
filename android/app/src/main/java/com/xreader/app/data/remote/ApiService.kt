package com.xreader.app.data.remote

import com.xreader.app.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    // Auth
    @GET("/api/auth/status")
    suspend fun getAuthStatus(): AuthStatusResponse

    @POST("/api/auth/challenge")
    suspend fun getAuthChallenge(): AuthChallengeResponse

    @POST("/api/auth/verify")
    suspend fun verifyAuth(@Body request: AuthVerifyRequest): AuthResponse

    @POST("/api/auth/enable")
    suspend fun enableAuth(@Body request: AuthEnableRequest): AuthResponse

    @POST("/api/auth/disable")
    suspend fun disableAuth(@Body request: AuthDisableRequest): AuthResponse

    // Books
    @GET("/api/books")
    suspend fun getBooks(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("search") search: String? = null
    ): BookListResponse

    @GET("/api/books/{id}")
    suspend fun getBook(@Path("id") id: Int): BookResponse

    @Multipart
    @POST("/api/books/upload")
    suspend fun uploadBook(@Part file: MultipartBody.Part): BookResponse

    @PATCH("/api/books/{id}")
    suspend fun updateBook(@Path("id") id: Int, @Body update: BookUpdate): BookResponse

    @DELETE("/api/books/{id}")
    suspend fun deleteBook(@Path("id") id: Int): MessageResponse

    @POST("/api/books/{id}/reparse")
    suspend fun reparseBook(@Path("id") id: Int): ReparseResponse

    // Chapters
    @GET("/api/books/{id}/chapters")
    suspend fun getChapters(@Path("id") bookId: Int): List<ChapterResponse>

    @GET("/api/chapters/{id}")
    suspend fun getChapter(@Path("id") id: Int): ChapterResponse

    @PATCH("/api/chapters/{id}")
    suspend fun updateChapter(
        @Path("id") id: Int,
        @Body update: Map<String, String?>
    ): ChapterResponse

    @DELETE("/api/chapters/{id}")
    suspend fun deleteChapter(@Path("id") id: Int): MessageResponse

    // Tasks
    @GET("/api/tasks")
    suspend fun getTasks(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("status") status: String? = null,
        @Query("book_id") bookId: Int? = null
    ): TaskListResponse

    @POST("/api/tasks")
    suspend fun createTask(@Body request: TaskCreate): TaskResponse

    @GET("/api/tasks/{id}/progress")
    suspend fun getTaskProgress(@Path("id") id: Int): TaskProgress

    @POST("/api/tasks/{id}/retry")
    suspend fun retryTask(@Path("id") id: Int): TaskResponse

    @DELETE("/api/tasks/{id}")
    suspend fun cancelTask(@Path("id") id: Int): MessageResponse

    // Voice Presets
    @GET("/api/voice-presets")
    suspend fun getVoicePresets(): VoicePresetListResponse

    @POST("/api/voice-presets")
    suspend fun createVoicePreset(@Body request: VoicePresetCreate): VoicePresetResponse

    @GET("/api/voice-presets/{id}")
    suspend fun getVoicePreset(@Path("id") id: Int): VoicePresetResponse

    @PUT("/api/voice-presets/{id}")
    suspend fun updateVoicePreset(
        @Path("id") id: Int,
        @Body update: VoicePresetUpdate
    ): VoicePresetResponse

    @DELETE("/api/voice-presets/{id}")
    suspend fun deleteVoicePreset(@Path("id") id: Int): MessageResponse

    // Config
    @GET("/api/config")
    suspend fun getConfig(): ConfigResponse

    @PUT("/api/config")
    suspend fun updateConfig(@Body update: ConfigUpdate): ConfigResponse

    @Multipart
    @POST("/api/config/test")
    suspend fun testTts(
        @Part("text") text: RequestBody,
        @Part("voice_preset_id") presetId: RequestBody? = null
    ): TestAudioResponse

    // Reference audio upload
    @Multipart
    @POST("/api/voice-presets/upload-reference")
    suspend fun uploadReferenceAudio(@Part file: MultipartBody.Part): ReferenceUploadResponse
}
