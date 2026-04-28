package com.xreader.app.ui.tasks

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.xreader.app.data.model.TaskResponse
import com.xreader.app.data.model.TaskStatus
import com.xreader.app.ui.components.EmptyPlaceholder
import com.xreader.app.ui.components.StatusBadge

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TasksScreen(
    viewModel: TasksViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    var showFilterMenu by remember { mutableStateOf(false) }

    val statusOptions = listOf(
        null to "全部",
        "pending" to "待处理",
        "queued" to "排队中",
        "running" to "进行中",
        "completed" to "已完成",
        "failed" to "失败"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("任务") },
                actions = {
                    Box {
                        IconButton(onClick = { showFilterMenu = true }) {
                            Icon(Icons.Default.FilterList, contentDescription = "筛选")
                        }
                        DropdownMenu(
                            expanded = showFilterMenu,
                            onDismissRequest = { showFilterMenu = false }
                        ) {
                            statusOptions.forEach { (value, label) ->
                                DropdownMenuItem(
                                    text = {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            if (uiState.statusFilter == value) {
                                                Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                                                Spacer(modifier = Modifier.width(8.dp))
                                            }
                                            Text(label)
                                        }
                                    },
                                    onClick = {
                                        viewModel.setStatusFilter(value)
                                        showFilterMenu = false
                                    }
                                )
                            }
                        }
                    }
                }
            )
        },
        modifier = modifier
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (uiState.isLoading && uiState.tasks.isEmpty()) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (uiState.tasks.isEmpty()) {
                EmptyPlaceholder(
                    title = "暂无任务",
                    icon = Icons.Default.Assignment,
                    description = "转换任务将在这里显示"
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(vertical = 4.dp)
                ) {
                    items(uiState.tasks, key = { it.id }) { task ->
                        TaskRow(
                            task = task,
                            onRetry = { viewModel.retryTask(task.id) },
                            onCancel = { viewModel.cancelTask(task.id) }
                        )
                    }
                }
            }
        }
    }

    uiState.error?.let { error ->
        AlertDialog(
            onDismissRequest = viewModel::clearError,
            confirmButton = { TextButton(onClick = viewModel::clearError) { Text("确定") } },
            title = { Text("错误") },
            text = { Text(error) }
        )
    }
}

@Composable
private fun TaskRow(
    task: TaskResponse,
    onRetry: () -> Unit,
    onCancel: () -> Unit
) {
    ListItem(
        headlineContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                StatusBadge(status = task.status.name.lowercase())
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    "图书 #${task.bookId} · 章节 #${task.chapterId}",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        },
        supportingContent = {
            Column {
                task.errorMessage?.let { msg ->
                    Text(
                        text = msg,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                        maxLines = 2
                    )
                }
            }
        },
        trailingContent = {
            Row {
                if (task.status == TaskStatus.FAILED || task.status == TaskStatus.SKIPPED) {
                    TextButton(onClick = onRetry) { Text("重试") }
                }
                if (task.status == TaskStatus.PENDING || task.status == TaskStatus.QUEUED) {
                    TextButton(onClick = onCancel) { Text("取消", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    )
}
