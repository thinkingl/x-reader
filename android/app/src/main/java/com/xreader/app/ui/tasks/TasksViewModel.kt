package com.xreader.app.ui.tasks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.TaskResponse
import com.xreader.app.data.model.TaskStatus
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TasksUiState(
    val tasks: List<TaskResponse> = emptyList(),
    val total: Int = 0,
    val isLoading: Boolean = false,
    val statusFilter: String? = null,
    val error: String? = null
)

@HiltViewModel
class TasksViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(TasksUiState())
    val uiState: StateFlow<TasksUiState> = _uiState.asStateFlow()

    init {
        loadTasks()
    }

    fun loadTasks() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val result = repository.getTasks(status = _uiState.value.statusFilter)
                _uiState.value = _uiState.value.copy(
                    tasks = result.items,
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

    fun setStatusFilter(status: String?) {
        _uiState.value = _uiState.value.copy(statusFilter = status)
        loadTasks()
    }

    fun retryTask(taskId: Int) {
        viewModelScope.launch {
            try {
                repository.retryTask(taskId)
                loadTasks()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "重试失败: ${e.message}")
            }
        }
    }

    fun cancelTask(taskId: Int) {
        viewModelScope.launch {
            try {
                repository.cancelTask(taskId)
                loadTasks()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "取消失败: ${e.message}")
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
