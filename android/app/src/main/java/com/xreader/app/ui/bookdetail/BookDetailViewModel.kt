package com.xreader.app.ui.bookdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.*
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BookDetailUiState(
    val book: BookResponse? = null,
    val chapters: List<ChapterResponse> = emptyList(),
    val presets: List<VoicePresetResponse> = emptyList(),
    val selectedPresetId: Int? = null,
    val selectedChapterIds: Set<Int> = emptySet(),
    val isLoading: Boolean = false,
    val isConverting: Boolean = false,
    val convertingChapterIds: Set<Int> = emptySet(),
    val taskProgress: Map<Int, TaskProgress> = emptyMap(),
    val isEditing: Boolean = false,
    val editTitle: String = "",
    val editAuthor: String = "",
    val error: String? = null,
    val message: String? = null
)

@HiltViewModel
class BookDetailViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(BookDetailUiState())
    val uiState: StateFlow<BookDetailUiState> = _uiState.asStateFlow()

    private var pollingJob: Job? = null

    fun loadBook(bookId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val book = repository.getBook(bookId)
                val chapters = repository.getChapters(bookId)
                val presets = repository.getVoicePresets()
                _uiState.value = _uiState.value.copy(
                    book = book,
                    chapters = chapters,
                    presets = presets.items,
                    editTitle = book.title,
                    editAuthor = book.author ?: "",
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

    fun toggleChapterSelection(chapterId: Int) {
        val current = _uiState.value.selectedChapterIds
        _uiState.value = _uiState.value.copy(
            selectedChapterIds = if (chapterId in current) current - chapterId else current + chapterId
        )
    }

    fun selectAllChapters() {
        val all = _uiState.value.chapters.map { it.id }.toSet()
        _uiState.value = _uiState.value.copy(selectedChapterIds = all)
    }

    fun clearSelection() {
        _uiState.value = _uiState.value.copy(selectedChapterIds = emptySet())
    }

    fun setSelectedPreset(presetId: Int?) {
        _uiState.value = _uiState.value.copy(selectedPresetId = presetId)
    }

    fun convertSelected() {
        val ids = _uiState.value.selectedChapterIds
        if (ids.isEmpty()) return
        convertChapters(ids.toList())
    }

    fun convertAllUncompleted() {
        val ids = _uiState.value.chapters
            .filter { it.status != "completed" }
            .map { it.id }
        if (ids.isEmpty()) {
            _uiState.value = _uiState.value.copy(message = "没有需要转换的章节")
            return
        }
        convertChapters(ids)
    }

    fun convertSingleChapter(chapterId: Int) {
        convertChapters(listOf(chapterId))
    }

    private fun convertChapters(chapterIds: List<Int>) {
        val bookId = _uiState.value.book?.id ?: return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isConverting = true,
                convertingChapterIds = chapterIds.toSet(),
                selectedChapterIds = emptySet()
            )
            try {
                repository.createTask(
                    TaskCreate(
                        bookId = bookId,
                        chapterIds = chapterIds,
                        voicePresetId = _uiState.value.selectedPresetId
                    )
                )
                startPolling(bookId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isConverting = false,
                    convertingChapterIds = emptySet(),
                    error = "转换失败: ${e.message}"
                )
            }
        }
    }

    private fun startPolling(bookId: Int) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (isActive) {
                try {
                    val running = repository.getTasks(bookId = bookId, status = "running")
                    val queued = repository.getTasks(bookId = bookId, status = "queued")
                    val pending = repository.getTasks(bookId = bookId, status = "pending")

                    val progressMap = mutableMapOf<Int, TaskProgress>()
                    for (task in running.items) {
                        try {
                            val p = repository.getTaskProgress(task.id)
                            progressMap[task.chapterId] = p
                        } catch (_: Exception) {}
                    }
                    _uiState.value = _uiState.value.copy(taskProgress = progressMap)

                    if (running.items.isEmpty() && queued.items.isEmpty() && pending.items.isEmpty()) {
                        loadBook(bookId)
                        _uiState.value = _uiState.value.copy(
                            isConverting = false,
                            convertingChapterIds = emptySet(),
                            taskProgress = emptyMap()
                        )
                        break
                    }
                } catch (_: Exception) {}
                delay(2000)
            }
        }
    }

    fun reparseBook() {
        val bookId = _uiState.value.book?.id ?: return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                repository.reparseBook(bookId)
                loadBook(bookId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "重新解析失败: ${e.message}"
                )
            }
        }
    }

    fun startEditing() {
        val book = _uiState.value.book ?: return
        _uiState.value = _uiState.value.copy(
            isEditing = true,
            editTitle = book.title,
            editAuthor = book.author ?: ""
        )
    }

    fun updateEditTitle(title: String) {
        _uiState.value = _uiState.value.copy(editTitle = title)
    }

    fun updateEditAuthor(author: String) {
        _uiState.value = _uiState.value.copy(editAuthor = author)
    }

    fun saveBookInfo() {
        val bookId = _uiState.value.book?.id ?: return
        viewModelScope.launch {
            try {
                repository.updateBook(
                    bookId,
                    BookUpdate(
                        title = _uiState.value.editTitle,
                        author = _uiState.value.editAuthor.ifEmpty { null }
                    )
                )
                _uiState.value = _uiState.value.copy(isEditing = false)
                loadBook(bookId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "保存失败: ${e.message}")
            }
        }
    }

    fun cancelEditing() {
        _uiState.value = _uiState.value.copy(isEditing = false)
    }

    fun deleteChapter(chapterId: Int) {
        viewModelScope.launch {
            try {
                repository.deleteChapter(chapterId)
                val bookId = _uiState.value.book?.id ?: return@launch
                loadBook(bookId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "删除章节失败: ${e.message}")
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }

    override fun onCleared() {
        super.onCleared()
        pollingJob?.cancel()
    }
}
