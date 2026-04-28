package com.xreader.app.ui.bookdetail

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.xreader.app.data.model.ChapterResponse
import com.xreader.app.data.model.TaskProgress
import com.xreader.app.service.PlayerState
import com.xreader.app.ui.components.AudioPlayerBar
import com.xreader.app.ui.components.StatusBadge

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookDetailScreen(
    bookId: Int,
    onNavigateBack: () -> Unit,
    onChapterClick: (Int) -> Unit,
    onChapterEdit: (Int) -> Unit,
    playerState: PlayerState,
    onPlayChapter: (Int, String, String) -> Unit,
    onTogglePlayPause: () -> Unit,
    viewModel: BookDetailViewModel
) {
    val uiState by viewModel.uiState.collectAsState()
    var showDeleteChapter by remember { mutableStateOf<Int?>(null) }
    var showEditDialog by remember { mutableStateOf(false) }

    LaunchedEffect(bookId) {
        viewModel.loadBook(bookId)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(uiState.book?.title ?: "图书详情") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    IconButton(onClick = { showEditDialog = true }) {
                        Icon(Icons.Default.Edit, contentDescription = "编辑")
                    }
                    IconButton(onClick = { viewModel.reparseBook() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "重新解析")
                    }
                }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (uiState.isLoading && uiState.book == null) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp)
                ) {
                    uiState.book?.let { book ->
                        item {
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text(book.title, style = MaterialTheme.typography.titleLarge)
                                    book.author?.let {
                                        Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Row {
                                        Text("格式: ${book.format.uppercase()}", style = MaterialTheme.typography.bodySmall)
                                        Spacer(modifier = Modifier.width(16.dp))
                                        Text("章节数: ${book.chapterCount}", style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }
                    }

                    item {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 4.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("转换设置", style = MaterialTheme.typography.titleSmall)
                                Spacer(modifier = Modifier.height(8.dp))
                                var expanded by remember { mutableStateOf(false) }
                                ExposedDropdownMenuBox(
                                    expanded = expanded,
                                    onExpandedChange = { expanded = it }
                                ) {
                                    OutlinedTextField(
                                        value = uiState.presets.find { it.id == uiState.selectedPresetId }?.name ?: "随机",
                                        onValueChange = {},
                                        readOnly = true,
                                        label = { Text("语音预设") },
                                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .menuAnchor()
                                    )
                                    ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                                        DropdownMenuItem(
                                            text = { Text("随机") },
                                            onClick = { viewModel.setSelectedPreset(null); expanded = false }
                                        )
                                        uiState.presets.forEach { preset ->
                                            DropdownMenuItem(
                                                text = { Text(preset.name) },
                                                onClick = { viewModel.setSelectedPreset(preset.id); expanded = false }
                                            )
                                        }
                                    }
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Button(
                                        onClick = { viewModel.convertAllUncompleted() },
                                        enabled = !uiState.isConverting,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text(if (uiState.isConverting) "转换中..." else "转换全部")
                                    }
                                    if (uiState.selectedChapterIds.isNotEmpty()) {
                                        OutlinedButton(
                                            onClick = { viewModel.convertSelected() },
                                            enabled = !uiState.isConverting,
                                            modifier = Modifier.weight(1f)
                                        ) {
                                            Text("转换选中 (${uiState.selectedChapterIds.size})")
                                        }
                                    }
                                }
                            }
                        }
                    }

                    item {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "章节 (${uiState.chapters.size})",
                                style = MaterialTheme.typography.titleSmall
                            )
                            TextButton(onClick = {
                                if (uiState.selectedChapterIds.size == uiState.chapters.size) {
                                    viewModel.clearSelection()
                                } else {
                                    viewModel.selectAllChapters()
                                }
                            }) {
                                Text(if (uiState.selectedChapterIds.size == uiState.chapters.size) "取消全选" else "全选")
                            }
                        }
                    }

                    items(uiState.chapters, key = { it.id }) { chapter ->
                        ChapterRow(
                            chapter = chapter,
                            isSelected = chapter.id in uiState.selectedChapterIds,
                            isConverting = chapter.id in uiState.convertingChapterIds,
                            progress = uiState.taskProgress[chapter.id],
                            hasAudio = chapter.status == "completed",
                            onToggleSelect = { viewModel.toggleChapterSelection(chapter.id) },
                            onPlay = {
                                val bookTitle = uiState.book?.title ?: ""
                                val title = chapter.title ?: "第${chapter.chapterNumber}章"
                                onPlayChapter(chapter.id, title, bookTitle)
                            },
                            onViewContent = { onChapterClick(chapter.id) },
                            onEdit = { onChapterEdit(chapter.id) },
                            onDelete = { showDeleteChapter = chapter.id },
                            onConvert = { viewModel.convertSingleChapter(chapter.id) }
                        )
                    }
                }
            }

            if (playerState.currentTitle.isNotEmpty()) {
                AudioPlayerBar(
                    playerState = playerState,
                    onTogglePlayPause = onTogglePlayPause,
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
            }
        }
    }

    showDeleteChapter?.let { chapterId ->
        AlertDialog(
            onDismissRequest = { showDeleteChapter = null },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteChapter(chapterId)
                    showDeleteChapter = null
                }) { Text("删除", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteChapter = null }) { Text("取消") }
            },
            title = { Text("删除章节") },
            text = { Text("确定要删除这个章节吗？") }
        )
    }

    if (showEditDialog) {
        EditBookDialog(
            title = uiState.editTitle,
            author = uiState.editAuthor,
            onTitleChange = viewModel::updateEditTitle,
            onAuthorChange = viewModel::updateEditAuthor,
            onConfirm = {
                viewModel.saveBookInfo()
                showEditDialog = false
            },
            onDismiss = {
                viewModel.cancelEditing()
                showEditDialog = false
            }
        )
    }

    uiState.error?.let { error ->
        AlertDialog(
            onDismissRequest = viewModel::clearError,
            confirmButton = { TextButton(onClick = viewModel::clearError) { Text("确定") } },
            title = { Text("错误") },
            text = { Text(error) }
        )
    }

    uiState.message?.let { message ->
        AlertDialog(
            onDismissRequest = viewModel::clearMessage,
            confirmButton = { TextButton(onClick = viewModel::clearMessage) { Text("确定") } },
            title = { Text("提示") },
            text = { Text(message) }
        )
    }
}

@Composable
private fun ChapterRow(
    chapter: ChapterResponse,
    isSelected: Boolean,
    isConverting: Boolean,
    progress: TaskProgress?,
    hasAudio: Boolean,
    onToggleSelect: () -> Unit,
    onPlay: () -> Unit,
    onViewContent: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onConvert: () -> Unit
) {
    ListItem(
        headlineContent = {
            Text(
                chapter.title ?: "第${chapter.chapterNumber}章",
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        },
        supportingContent = {
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "${chapter.wordCount} 字",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    chapter.audioDuration?.let {
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            formatDuration(it),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    if (isConverting) {
                        Text("转换中...", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.tertiary)
                    } else {
                        StatusBadge(status = chapter.status)
                    }
                }
                if (progress != null && isConverting) {
                    Spacer(modifier = Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = { progress.progress.toFloat().coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text(
                        progress.message,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        },
        leadingContent = {
            Checkbox(
                checked = isSelected,
                onCheckedChange = { onToggleSelect() }
            )
        },
        trailingContent = {
            Row {
                IconButton(onClick = onViewContent, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Description, contentDescription = "查看", modifier = Modifier.size(18.dp))
                }
                IconButton(onClick = onEdit, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = "编辑", modifier = Modifier.size(18.dp))
                }
                if (hasAudio && !isConverting) {
                    IconButton(onClick = onPlay, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.PlayCircle, contentDescription = "播放", tint = MaterialTheme.colorScheme.primary)
                    }
                }
                IconButton(onClick = onConvert, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Default.Sync, contentDescription = "转换", modifier = Modifier.size(18.dp))
                }
            }
        }
    )
}

@Composable
private fun EditBookDialog(
    title: String,
    author: String,
    onTitleChange: (String) -> Unit,
    onAuthorChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onClick = onConfirm) { Text("保存") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
        title = { Text("编辑图书信息") },
        text = {
            Column {
                OutlinedTextField(
                    value = title,
                    onValueChange = onTitleChange,
                    label = { Text("书名") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = author,
                    onValueChange = onAuthorChange,
                    label = { Text("作者") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    )
}

private fun formatDuration(seconds: Double): String {
    val m = seconds.toInt() / 60
    val s = seconds.toInt() % 60
    return "%d:%02d".format(m, s)
}
