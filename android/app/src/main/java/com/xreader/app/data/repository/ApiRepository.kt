package com.xreader.app.data.repository

import android.content.Context
import android.net.Uri
import com.xreader.app.data.local.SettingsStore
import com.xreader.app.data.local.TokenStore
import com.xreader.app.data.model.*
import com.xreader.app.data.remote.ApiService
import com.xreader.app.data.remote.safeApiCall
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ApiRepository @Inject constructor(
    private val apiService: ApiService,
    private val settingsStore: SettingsStore,
    val tokenStore: TokenStore,
    @ApplicationContext private val context: Context
) {
    suspend fun getServerUrl(): String = settingsStore.serverUrl.first()

    suspend fun setServerUrl(url: String) = settingsStore.setServerUrl(url)

    suspend fun getAuthStatus() = safeApiCall { apiService.getAuthStatus() }

    suspend fun getAuthChallenge() = safeApiCall { apiService.getAuthChallenge() }

    suspend fun verifyAuth(request: AuthVerifyRequest) = safeApiCall {
        apiService.verifyAuth(request)
    }

    suspend fun enableAuth(request: AuthEnableRequest) = safeApiCall {
        apiService.enableAuth(request)
    }

    suspend fun disableAuth(request: AuthDisableRequest) = safeApiCall {
        apiService.disableAuth(request)
    }

    fun logout() {
        tokenStore.clear()
    }

    suspend fun getBooks(page: Int = 1, pageSize: Int = 20, search: String? = null) = safeApiCall {
        apiService.getBooks(page, pageSize, search)
    }

    suspend fun getBook(id: Int) = safeApiCall { apiService.getBook(id) }

    suspend fun uploadBook(uri: Uri): BookResponse = withContext(Dispatchers.IO) {
        safeApiCall {
            val file = copyUriToTempFile(uri)
            val requestFile = file.asRequestBody("application/octet-stream".toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", file.name, requestFile)
            val result = apiService.uploadBook(part)
            file.delete()
            result
        }
    }

    suspend fun updateBook(id: Int, update: BookUpdate) = safeApiCall {
        apiService.updateBook(id, update)
    }

    suspend fun deleteBook(id: Int) = safeApiCall { apiService.deleteBook(id) }

    suspend fun reparseBook(id: Int) = safeApiCall { apiService.reparseBook(id) }

    suspend fun getChapters(bookId: Int) = safeApiCall { apiService.getChapters(bookId) }

    suspend fun getChapter(id: Int) = safeApiCall { apiService.getChapter(id) }

    suspend fun updateChapter(id: Int, title: String?, content: String?) = safeApiCall {
        apiService.updateChapter(id, buildMap {
            title?.let { put("title", it) }
            content?.let { put("text_content", it) }
        })
    }

    suspend fun deleteChapter(id: Int) = safeApiCall { apiService.deleteChapter(id) }

    suspend fun getTasks(page: Int = 1, pageSize: Int = 20, status: String? = null, bookId: Int? = null) = safeApiCall {
        apiService.getTasks(page, pageSize, status, bookId)
    }

    suspend fun createTask(request: TaskCreate) = safeApiCall { apiService.createTask(request) }

    suspend fun getTaskProgress(id: Int) = safeApiCall { apiService.getTaskProgress(id) }

    suspend fun retryTask(id: Int) = safeApiCall { apiService.retryTask(id) }

    suspend fun cancelTask(id: Int) = safeApiCall { apiService.cancelTask(id) }

    suspend fun getVoicePresets() = safeApiCall { apiService.getVoicePresets() }

    suspend fun createVoicePreset(request: VoicePresetCreate) = safeApiCall {
        apiService.createVoicePreset(request)
    }

    suspend fun updateVoicePreset(id: Int, update: VoicePresetUpdate) = safeApiCall {
        apiService.updateVoicePreset(id, update)
    }

    suspend fun deleteVoicePreset(id: Int) = safeApiCall { apiService.deleteVoicePreset(id) }

    suspend fun getConfig() = safeApiCall { apiService.getConfig() }

    suspend fun updateConfig(update: ConfigUpdate) = safeApiCall {
        apiService.updateConfig(update)
    }

    suspend fun testTts(text: String, presetId: Int? = null) = withContext(Dispatchers.IO) {
        safeApiCall {
            val textBody = text.toRequestBody("text/plain".toMediaTypeOrNull())
            val presetBody = presetId?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull())
            apiService.testTts(textBody, presetBody)
        }
    }

    suspend fun uploadReferenceAudio(uri: Uri): ReferenceUploadResponse = withContext(Dispatchers.IO) {
        safeApiCall {
            val file = copyUriToTempFile(uri)
            val requestFile = file.asRequestBody("application/octet-stream".toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", file.name, requestFile)
            val result = apiService.uploadReferenceAudio(part)
            file.delete()
            result
        }
    }

    fun getAudioStreamUrl(bookId: Int, chapterId: Int): String {
        return "${getServerUrlBlocking()}/api/audio/$bookId/$chapterId/stream"
    }

    fun getAudioDownloadUrl(bookId: Int, chapterId: Int): String {
        return "${getServerUrlBlocking()}/api/audio/$bookId/$chapterId"
    }

    fun getAudioZipUrl(bookId: Int): String {
        return "${getServerUrlBlocking()}/api/audio/$bookId/zip"
    }

    private fun getServerUrlBlocking(): String {
        return runBlocking { settingsStore.serverUrl.first() }
    }

    private fun copyUriToTempFile(uri: Uri): File {
        val inputStream = context.contentResolver.openInputStream(uri)
            ?: throw Exception("无法读取文件")
        val fileName = getFileName(uri) ?: "upload_${System.currentTimeMillis()}"
        val tempFile = File(context.cacheDir, fileName)
        tempFile.outputStream().use { output ->
            inputStream.copyTo(output)
        }
        inputStream.close()
        return tempFile
    }

    private fun getFileName(uri: Uri): String? {
        val cursor = context.contentResolver.query(uri, null, null, null, null)
        return cursor?.use {
            val nameIndex = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            it.moveToFirst()
            it.getString(nameIndex)
        }
    }
}
