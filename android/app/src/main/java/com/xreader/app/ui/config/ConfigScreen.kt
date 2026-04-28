package com.xreader.app.ui.config

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.xreader.app.data.model.ConfigResponse

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfigScreen(
    onLogout: () -> Unit,
    viewModel: ConfigViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("配置") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
        ) {
            Card(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("认证设置", style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("状态")
                        Spacer(modifier = Modifier.weight(1f))
                        Text(
                            if (uiState.authEnabled) "已启用" else "未启用",
                            color = if (uiState.authEnabled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))

                    if (uiState.authEnabled) {
                        OutlinedTextField(
                            value = uiState.authKey,
                            onValueChange = viewModel::updateAuthKey,
                            label = { Text("当前认证密钥") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = { viewModel.disableAuth() },
                            enabled = uiState.authKey.isNotBlank() && !uiState.authLoading,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            if (uiState.authLoading) {
                                CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(8.dp))
                            }
                            Icon(Icons.Default.LockOpen, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("停用认证")
                        }
                    } else {
                        OutlinedTextField(
                            value = uiState.newAuthKey,
                            onValueChange = viewModel::updateNewAuthKey,
                            label = { Text("设置认证密钥") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = { viewModel.enableAuth() },
                            enabled = uiState.newAuthKey.isNotBlank() && !uiState.authLoading,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            if (uiState.authLoading) {
                                CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(8.dp))
                            }
                            Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("启用认证")
                        }
                    }

                    uiState.authMessage?.let {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("服务器地址", style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = uiState.serverUrl,
                        onValueChange = viewModel::updateServerUrl,
                        label = { Text("服务器 URL") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        OutlinedButton(onClick = { viewModel.testConnection() }, enabled = !uiState.isLoading) {
                            Text("测试连接")
                        }
                        if (uiState.isConnected) {
                            Spacer(modifier = Modifier.width(8.dp))
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }

            uiState.config?.let { config ->
                ConfigInfoSection("TTS 引擎") {
                    ConfigItem("模式", ttsModeLabel(config.ttsMode))
                    ConfigItem("设备", config.device)
                    ConfigItem("精度", config.precision)
                    ConfigItem("并发数", "${config.concurrency}")
                }

                ConfigInfoSection("在线 TTS (MiMo)") {
                    ConfigItem("API 地址", config.mimoBaseUrl)
                    ConfigItem("模型", config.mimoModel)
                    ConfigItem("默认语音", config.mimoDefaultVoice)
                    ConfigItem("API Key", if (config.mimoApiKey.isEmpty()) "未配置" else "已配置")
                }

                ConfigInfoSection("文本分段") {
                    ConfigItem("本地分段", "${config.localChunkSize} 字符")
                    ConfigItem("在线分段", "${config.onlineChunkSize} 字符")
                    ConfigItem("本地间隔", "%.1f s".format(config.localChunkGap))
                    ConfigItem("在线间隔", "%.1f s".format(config.onlineChunkGap))
                }

                ConfigInfoSection("音频输出") {
                    ConfigItem("格式", config.audioFormat.uppercase())
                    ConfigItem("采样率", "${config.sampleRate} Hz")
                }

                ConfigInfoSection("路径") {
                    ConfigItem("图书目录", config.bookDir)
                    ConfigItem("音频目录", config.audioDir)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedButton(
                onClick = onLogout,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
            ) {
                Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("断开连接")
            }

            Spacer(modifier = Modifier.height(16.dp))
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
private fun ConfigInfoSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Spacer(modifier = Modifier.height(8.dp))
            content()
        }
    }
}

@Composable
private fun ConfigItem(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun ttsModeLabel(mode: String): String = when (mode) {
    "local" -> "仅本地"
    "online" -> "仅在线"
    "online_first" -> "在线优先"
    else -> mode
}
