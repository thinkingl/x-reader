package com.xreader.app.ui.presets

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.unit.dp
import com.xreader.app.data.model.VoicePresetResponse
import com.xreader.app.service.AudioPlayerManager
import com.xreader.app.service.PlayerState
import com.xreader.app.ui.components.EmptyPlaceholder

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PresetsScreen(
    onCreateClick: () -> Unit,
    onEditClick: (Int) -> Unit,
    viewModel: PresetsViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.listState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("语音预设") },
                actions = {
                    IconButton(onClick = onCreateClick) {
                        Icon(Icons.Default.Add, contentDescription = "新建")
                    }
                }
            )
        },
        modifier = modifier
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (uiState.isLoading && uiState.presets.isEmpty()) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (uiState.presets.isEmpty()) {
                EmptyPlaceholder(
                    title = "暂无预设",
                    icon = Icons.Default.RecordVoiceOver,
                    description = "点击 + 创建语音预设"
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(vertical = 4.dp)
                ) {
                    items(uiState.presets, key = { it.id }) { preset ->
                        PresetRow(
                            preset = preset,
                            onClick = { onEditClick(preset.id) },
                            onDelete = { viewModel.deletePreset(preset.id) }
                        )
                    }
                }
            }
        }
    }

    uiState.error?.let { error ->
        AlertDialog(
            onDismissRequest = viewModel::clearListError,
            confirmButton = { TextButton(onClick = viewModel::clearListError) { Text("确定") } },
            title = { Text("错误") },
            text = { Text(error) }
        )
    }
}

@Composable
private fun PresetRow(
    preset: VoicePresetResponse,
    onClick: () -> Unit,
    onDelete: () -> Unit
) {
    var showDeleteDialog by remember { mutableStateOf(false) }

    ListItem(
        headlineContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(preset.name)
                if (preset.isDefault) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        "默认",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }
        },
        supportingContent = {
            Row {
                Text(
                    preset.voiceMode.replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                preset.instruct?.let {
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                }
            }
        },
        trailingContent = {
            IconButton(onClick = { showDeleteDialog = true }) {
                Icon(Icons.Default.Delete, contentDescription = "删除", tint = MaterialTheme.colorScheme.error)
            }
        },
        modifier = Modifier.clickable(onClick = onClick)
    )

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            confirmButton = {
                TextButton(onClick = { onDelete(); showDeleteDialog = false }) {
                    Text("删除", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { showDeleteDialog = false }) { Text("取消") } },
            title = { Text("删除预设") },
            text = { Text("确定要删除预设 \"${preset.name}\" 吗？") }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PresetEditScreen(
    presetId: Int? = null,
    onNavigateBack: () -> Unit,
    viewModel: PresetsViewModel,
    playerState: PlayerState,
    onPlayAudio: (String, String, String) -> Unit,
    onTogglePlayPause: () -> Unit
) {
    val editState by viewModel.editState.collectAsState()
    var isInitialized by remember { mutableStateOf(false) }

    LaunchedEffect(presetId) {
        if (presetId != null && !isInitialized) {
            val preset = viewModel.listState.value.presets.find { it.id == presetId }
            if (preset != null) {
                viewModel.initEditForm(preset)
            }
            isInitialized = true
        } else if (presetId == null && !isInitialized) {
            viewModel.initEditForm()
            isInitialized = true
        }
    }

    if (editState.saved) {
        LaunchedEffect(Unit) {
            viewModel.clearSaved()
            onNavigateBack()
        }
    }

    val audioFilePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let { viewModel.uploadReferenceAudio(it) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (presetId != null) "编辑预设" else "新建预设") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    TextButton(
                        onClick = {
                            if (presetId != null) viewModel.updatePreset(presetId)
                            else viewModel.createPreset()
                        },
                        enabled = editState.name.isNotBlank() && !editState.isSaving
                    ) {
                        Text("保存")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Text("基本信息", style = MaterialTheme.typography.titleSmall)
                Spacer(modifier = Modifier.height(4.dp))
                OutlinedTextField(
                    value = editState.name,
                    onValueChange = viewModel::updateName,
                    label = { Text("预设名称") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text("语音模式", style = MaterialTheme.typography.bodyMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("clone" to "语音克隆", "design" to "语音设计", "auto" to "自动语音").forEach { (value, label) ->
                        FilterChip(
                            selected = editState.voiceMode == value,
                            onClick = { viewModel.updateVoiceMode(value) },
                            label = { Text(label) }
                        )
                    }
                }
            }

            if (editState.voiceMode == "design") {
                item {
                    Text("语音设计", style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = editState.instruct,
                        onValueChange = viewModel::updateInstruct,
                        label = { Text("指令（如：female, young adult）") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2,
                        maxLines = 4
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = editState.language,
                        onValueChange = viewModel::updateLanguage,
                        label = { Text("语言（如：zh）") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            if (editState.voiceMode == "clone") {
                item {
                    Text("语音克隆", style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(
                            onClick = { audioFilePicker.launch(arrayOf("audio/*")) },
                            modifier = Modifier.weight(1f),
                            enabled = !editState.isUploading
                        ) {
                            Icon(Icons.Default.AttachFile, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("选择文件")
                        }
                    }
                    if (editState.isUploading) {
                        Spacer(modifier = Modifier.height(8.dp))
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                        Text("上传中...", style = MaterialTheme.typography.bodySmall)
                    }
                    editState.refAudioPath?.let {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("参考音频已上传", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = editState.refText,
                        onValueChange = viewModel::updateRefText,
                        label = { Text("参考文本") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3,
                        maxLines = 6
                    )
                }
            }

            item {
                Text("生成参数", style = MaterialTheme.typography.titleSmall)
                Spacer(modifier = Modifier.height(4.dp))
                Text("解码步数: ${editState.numStep}", style = MaterialTheme.typography.bodyMedium)
                Slider(
                    value = editState.numStep.toFloat(),
                    onValueChange = { viewModel.updateNumStep(it.toInt()) },
                    valueRange = 1f..64f,
                    steps = 62
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("引导强度", modifier = Modifier.width(72.dp))
                    Slider(
                        value = editState.guidanceScale.toFloat(),
                        onValueChange = { viewModel.updateGuidanceScale(it.toDouble()) },
                        valueRange = 1f..3f,
                        modifier = Modifier.weight(1f)
                    )
                    Text("%.1f".format(editState.guidanceScale), modifier = Modifier.width(36.dp))
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("语速", modifier = Modifier.width(72.dp))
                    Slider(
                        value = editState.speed.toFloat(),
                        onValueChange = { viewModel.updateSpeed(it.toDouble()) },
                        valueRange = 0.5f..2f,
                        modifier = Modifier.weight(1f)
                    )
                    Text("%.1f".format(editState.speed), modifier = Modifier.width(36.dp))
                }
            }

            if (presetId != null) {
                item {
                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                    Text("测试预设效果", style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = editState.testText,
                        onValueChange = viewModel::updateTestText,
                        label = { Text("测试文本") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2,
                        maxLines = 4
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(
                        onClick = { viewModel.testPreset(presetId) },
                        enabled = editState.testText.isNotBlank() && !editState.isTesting,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        if (editState.isTesting) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text(if (editState.isTesting) "生成中..." else "生成语音")
                    }
                    editState.testResult?.let { result ->
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                "时长: %.1f 秒".format(result.duration),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.weight(1f))
                            if (result.audioUrl != null) {
                                OutlinedButton(
                                    onClick = {
                                        onPlayAudio(result.audioUrl, editState.testText, "测试")
                                    }
                                ) {
                                    Icon(
                                        if (playerState.isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                                        contentDescription = null,
                                        modifier = Modifier.size(18.dp)
                                    )
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(if (playerState.isPlaying) "播放中" else "播放")
                                }
                            }
                        }
                        Text(result.message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }

    editState.error?.let { error ->
        AlertDialog(
            onDismissRequest = viewModel::clearEditError,
            confirmButton = { TextButton(onClick = viewModel::clearEditError) { Text("确定") } },
            title = { Text("错误") },
            text = { Text(error) }
        )
    }
}
