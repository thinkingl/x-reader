package com.xreader.app.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Task
import androidx.compose.material.icons.filled.RecordVoiceOver
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Screen(val route: String) {
    data object Setup : Screen("setup")
    data object Login : Screen("login")
    data object Main : Screen("main")
    data object BookDetail : Screen("book/{bookId}") {
        fun createRoute(bookId: Int) = "book/$bookId"
    }
    data object ChapterContent : Screen("chapter/{chapterId}") {
        fun createRoute(chapterId: Int) = "chapter/$chapterId"
    }
    data object ChapterEdit : Screen("chapter/{chapterId}/edit") {
        fun createRoute(chapterId: Int) = "chapter/$chapterId/edit"
    }
    data object VoicePresetCreate : Screen("preset/create")
    data object VoicePresetEdit : Screen("preset/{presetId}/edit") {
        fun createRoute(presetId: Int) = "preset/$presetId/edit"
    }
}

sealed class BottomNavItem(val route: String, val label: String, val icon: ImageVector) {
    data object Books : BottomNavItem("books", "图书", Icons.Default.Book)
    data object Tasks : BottomNavItem("tasks", "任务", Icons.Default.Task)
    data object Presets : BottomNavItem("presets", "预设", Icons.Default.RecordVoiceOver)
    data object Config : BottomNavItem("config", "配置", Icons.Default.Settings)
}
