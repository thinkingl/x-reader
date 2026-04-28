package com.xreader.app.data.remote

import com.xreader.app.data.model.MessageResponse
import kotlinx.serialization.json.Json
import okhttp3.ResponseBody
import retrofit2.HttpException

class ApiException(
    val statusCode: Int,
    override val message: String
) : Exception(message)

suspend fun <T> safeApiCall(block: suspend () -> T): T {
    return try {
        block()
    } catch (e: HttpException) {
        val errorBody = e.response()?.errorBody()?.string()
        val message = try {
            if (errorBody != null) {
                val json = Json { ignoreUnknownKeys = true }
                val parsed = json.decodeFromString<MessageResponse>(errorBody)
                parsed.detail ?: parsed.message ?: "HTTP ${e.code()}"
            } else {
                "HTTP ${e.code()}"
            }
        } catch (_: Exception) {
            "HTTP ${e.code()}"
        }
        throw ApiException(e.code(), message)
    }
}
