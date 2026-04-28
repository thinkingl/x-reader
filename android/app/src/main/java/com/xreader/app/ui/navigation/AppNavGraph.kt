package com.xreader.app.ui.navigation

import androidx.compose.material3.windowsizeclass.WindowSizeClass
import androidx.compose.material3.windowsizeclass.WindowWidthSizeClass
import androidx.compose.runtime.*
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.xreader.app.data.repository.ApiRepository
import com.xreader.app.service.AudioPlayerManager
import com.xreader.app.service.PlayerState
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import com.xreader.app.ui.MainScreen
import com.xreader.app.ui.auth.LoginScreen
import com.xreader.app.ui.bookdetail.BookDetailScreen
import com.xreader.app.ui.bookdetail.BookDetailViewModel
import com.xreader.app.ui.books.BooksViewModel
import com.xreader.app.ui.chapter.ChapterContentScreen
import com.xreader.app.ui.config.ConfigViewModel
import com.xreader.app.ui.presets.PresetEditScreen
import com.xreader.app.ui.presets.PresetsViewModel
import com.xreader.app.ui.setup.SetupScreen
import com.xreader.app.ui.setup.SetupViewModel
import com.xreader.app.ui.tasks.TasksViewModel

@Composable
fun AppNavGraph(
    navController: NavHostController,
    windowSizeClass: WindowSizeClass,
    playerState: PlayerState,
    audioPlayerManager: AudioPlayerManager,
    repository: ApiRepository,
    startDestination: String
) {
    val isCompact = windowSizeClass.widthSizeClass == WindowWidthSizeClass.Compact

    val booksViewModel: BooksViewModel = hiltViewModel()
    val tasksViewModel: TasksViewModel = hiltViewModel()
    val presetsViewModel: PresetsViewModel = hiltViewModel()
    val configViewModel: ConfigViewModel = hiltViewModel()

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Screen.Setup.route) {
            val setupViewModel: SetupViewModel = hiltViewModel()
            SetupScreen(
                onNavigateToLogin = {
                    navController.navigate(Screen.Login.route) {
                        popUpTo(Screen.Setup.route) { inclusive = true }
                    }
                },
                onNavigateToMain = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Setup.route) { inclusive = true }
                    }
                },
                viewModel = setupViewModel
            )
        }

        composable(Screen.Login.route) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Login.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Main.route) {
            MainScreen(
                navController = navController,
                isCompact = isCompact,
                playerState = playerState,
                onPlayChapter = { bookId, chapterId, title, bookTitle ->
                    val url = repository.getAudioStreamUrl(bookId, chapterId)
                    audioPlayerManager.play(url, title, bookTitle)
                },
                onTogglePlayPause = { audioPlayerManager.togglePlayPause() },
                onNavigateToBookDetail = { bookId ->
                    navController.navigate(Screen.BookDetail.createRoute(bookId))
                },
                onNavigateToChapter = { chapterId ->
                    navController.navigate(Screen.ChapterContent.createRoute(chapterId))
                },
                onNavigateToChapterEdit = { chapterId ->
                    navController.navigate(Screen.ChapterContent.createRoute(chapterId))
                },
                onNavigateToPresetCreate = {
                    navController.navigate(Screen.VoicePresetCreate.route)
                },
                onNavigateToPresetEdit = { presetId ->
                    navController.navigate(Screen.VoicePresetEdit.createRoute(presetId))
                },
                onLogout = {
                    repository.logout()
                    navController.navigate(Screen.Setup.route) {
                        popUpTo(0) { inclusive = true }
                    }
                },
                booksViewModel = booksViewModel,
                tasksViewModel = tasksViewModel,
                presetsViewModel = presetsViewModel,
                configViewModel = configViewModel
            )
        }

        composable(Screen.BookDetail.route) { backStackEntry ->
            val bookId = backStackEntry.arguments?.getString("bookId")?.toIntOrNull() ?: return@composable
            val bookDetailViewModel: BookDetailViewModel = hiltViewModel()
            BookDetailScreen(
                bookId = bookId,
                onNavigateBack = { navController.popBackStack() },
                onChapterClick = { chapterId ->
                    navController.navigate(Screen.ChapterContent.createRoute(chapterId))
                },
                onChapterEdit = { chapterId ->
                    navController.navigate(Screen.ChapterContent.createRoute(chapterId))
                },
                playerState = playerState,
                onPlayChapter = { chapterId, title, bookTitle ->
                    val url = repository.getAudioStreamUrl(bookId, chapterId)
                    audioPlayerManager.play(url, title, bookTitle)
                },
                onTogglePlayPause = { audioPlayerManager.togglePlayPause() },
                viewModel = bookDetailViewModel
            )
        }

        composable(Screen.ChapterContent.route) { backStackEntry ->
            val chapterId = backStackEntry.arguments?.getString("chapterId")?.toIntOrNull() ?: return@composable
            ChapterContentScreen(
                chapterId = chapterId,
                onNavigateBack = { navController.popBackStack() }
            )
        }

        composable(Screen.VoicePresetCreate.route) {
            PresetEditScreen(
                presetId = null,
                onNavigateBack = { navController.popBackStack() },
                viewModel = presetsViewModel,
                playerState = playerState,
                onPlayAudio = { relativeUrl, title, bookTitle ->
                    val serverUrl = runBlocking { repository.getServerUrl() }
                    val url = serverUrl.trimEnd('/') + relativeUrl
                    audioPlayerManager.play(url, title, bookTitle)
                },
                onTogglePlayPause = { audioPlayerManager.togglePlayPause() }
            )
        }

        composable(Screen.VoicePresetEdit.route) { backStackEntry ->
            val presetId = backStackEntry.arguments?.getString("presetId")?.toIntOrNull() ?: return@composable
            PresetEditScreen(
                presetId = presetId,
                onNavigateBack = { navController.popBackStack() },
                viewModel = presetsViewModel,
                playerState = playerState,
                onPlayAudio = { relativeUrl, title, bookTitle ->
                    val serverUrl = runBlocking { repository.getServerUrl() }
                    val url = serverUrl.trimEnd('/') + relativeUrl
                    audioPlayerManager.play(url, title, bookTitle)
                },
                onTogglePlayPause = { audioPlayerManager.togglePlayPause() }
            )
        }
    }
}
