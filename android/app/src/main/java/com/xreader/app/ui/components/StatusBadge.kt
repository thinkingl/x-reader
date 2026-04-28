package com.xreader.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.xreader.app.data.model.TaskStatus

@Composable
fun StatusBadge(status: String, modifier: Modifier = Modifier) {
    val (label, color) = when (status) {
        "pending" -> "待转换" to Color(0xFF9E9E9E)
        "queued" -> "排队中" to Color(0xFFFFA726)
        "running", "converting" -> "转换中" to Color(0xFFFF9800)
        "completed" -> "已完成" to Color(0xFF4CAF50)
        "failed" -> "失败" to Color(0xFFF44336)
        "skipped" -> "跳过" to Color(0xFF9E9E9E)
        "parsed" -> "已解析" to Color(0xFF2196F3)
        else -> status to Color(0xFF9E9E9E)
    }
    Text(
        text = label,
        style = MaterialTheme.typography.labelSmall,
        color = color,
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .background(color.copy(alpha = 0.12f))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    )
}
