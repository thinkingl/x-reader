package com.xreader.app.ui.chapter

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.ChapterResponse
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChapterUiState(
    val chapter: ChapterResponse? = null,
    val isLoading: Boolean = false,
    val isEditing: Boolean = false,
    val editTitle: String = "",
    val editContent: String = "",
    val isSaving: Boolean = false,
    val error: String? = null,
    val saved: Boolean = false
)

@HiltViewModel
class ChapterViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChapterUiState())
    val uiState: StateFlow<ChapterUiState> = _uiState.asStateFlow()

    fun loadChapter(chapterId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val chapter = repository.getChapter(chapterId)
                _uiState.value = _uiState.value.copy(
                    chapter = chapter,
                    editTitle = chapter.title ?: "",
                    editContent = chapter.textContent ?: "",
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

    fun startEditing() {
        _uiState.value = _uiState.value.copy(isEditing = true)
    }

    fun updateTitle(title: String) {
        _uiState.value = _uiState.value.copy(editTitle = title)
    }

    fun updateContent(content: String) {
        _uiState.value = _uiState.value.copy(editContent = content)
    }

    fun save(chapterId: Int) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true)
            try {
                repository.updateChapter(chapterId, _uiState.value.editTitle, _uiState.value.editContent)
                _uiState.value = _uiState.value.copy(isSaving = false, isEditing = false, saved = true)
                loadChapter(chapterId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    error = "保存失败: ${e.message}"
                )
            }
        }
    }

    fun cancelEditing() {
        val chapter = _uiState.value.chapter
        _uiState.value = _uiState.value.copy(
            isEditing = false,
            editTitle = chapter?.title ?: "",
            editContent = chapter?.textContent ?: ""
        )
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
