package com.xreader.app.ui.books

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.BookListResponse
import com.xreader.app.data.model.BookResponse
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BooksUiState(
    val books: List<BookResponse> = emptyList(),
    val total: Int = 0,
    val isLoading: Boolean = false,
    val isUploading: Boolean = false,
    val searchQuery: String = "",
    val error: String? = null
)

@HiltViewModel
class BooksViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(BooksUiState())
    val uiState: StateFlow<BooksUiState> = _uiState.asStateFlow()

    private var searchJob: Job? = null

    init {
        loadBooks()
    }

    fun loadBooks() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val search = _uiState.value.searchQuery.ifEmpty { null }
                val result = repository.getBooks(search = search)
                _uiState.value = _uiState.value.copy(
                    books = result.items,
                    total = result.total,
                    isLoading = false,
                    error = null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "加载失败"
                )
            }
        }
    }

    fun updateSearch(query: String) {
        _uiState.value = _uiState.value.copy(searchQuery = query)
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(300)
            loadBooks()
        }
    }

    fun uploadBook(uri: Uri) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isUploading = true)
            try {
                val book = repository.uploadBook(uri)
                _uiState.value = _uiState.value.copy(
                    books = listOf(book) + _uiState.value.books,
                    total = _uiState.value.total + 1,
                    isUploading = false
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isUploading = false,
                    error = "上传失败: ${e.message}"
                )
            }
        }
    }

    fun deleteBook(id: Int) {
        viewModelScope.launch {
            try {
                repository.deleteBook(id)
                _uiState.value = _uiState.value.copy(
                    books = _uiState.value.books.filter { it.id != id },
                    total = _uiState.value.total - 1
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "删除失败: ${e.message}")
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
