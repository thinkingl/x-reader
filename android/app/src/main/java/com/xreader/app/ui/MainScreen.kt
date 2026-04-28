package com.xreader.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState
import com.xreader.app.service.PlayerState
import com.xreader.app.ui.bookdetail.BookDetailScreen
import com.xreader.app.ui.bookdetail.BookDetailViewModel
import com.xreader.app.ui.books.BooksScreen
import com.xreader.app.ui.books.BooksViewModel
import com.xreader.app.ui.components.AudioPlayerBar
import com.xreader.app.ui.config.ConfigScreen
import com.xreader.app.ui.config.ConfigViewModel
import com.xreader.app.ui.navigation.BottomNavItem
import com.xreader.app.ui.presets.PresetsScreen
import com.xreader.app.ui.presets.PresetsViewModel
import com.xreader.app.ui.tasks.TasksScreen
import com.xreader.app.ui.tasks.TasksViewModel

@Composable
fun MainScreen(
    navController: NavHostController,
    isCompact: Boolean,
    playerState: PlayerState,
    onPlayChapter: (bookId: Int, chapterId: Int, title: String, bookTitle: String) -> Unit,
    onTogglePlayPause: () -> Unit,
    onNavigateToBookDetail: (Int) -> Unit,
    onNavigateToChapter: (Int) -> Unit,
    onNavigateToChapterEdit: (Int) -> Unit,
    onNavigateToPresetCreate: () -> Unit,
    onNavigateToPresetEdit: (Int) -> Unit,
    onLogout: () -> Unit,
    booksViewModel: BooksViewModel,
    tasksViewModel: TasksViewModel,
    presetsViewModel: PresetsViewModel,
    configViewModel: ConfigViewModel
) {
    if (isCompact) {
        CompactLayout(
            navController = navController,
            playerState = playerState,
            onPlayChapter = onPlayChapter,
            onTogglePlayPause = onTogglePlayPause,
            onNavigateToBookDetail = onNavigateToBookDetail,
            onNavigateToPresetCreate = onNavigateToPresetCreate,
            onNavigateToPresetEdit = onNavigateToPresetEdit,
            onLogout = onLogout,
            booksViewModel = booksViewModel,
            tasksViewModel = tasksViewModel,
            presetsViewModel = presetsViewModel,
            configViewModel = configViewModel
        )
    } else {
        ExpandedLayout(
            navController = navController,
            playerState = playerState,
            onPlayChapter = onPlayChapter,
            onTogglePlayPause = onTogglePlayPause,
            onNavigateToBookDetail = onNavigateToBookDetail,
            onNavigateToChapter = onNavigateToChapter,
            onNavigateToChapterEdit = onNavigateToChapterEdit,
            onNavigateToPresetCreate = onNavigateToPresetCreate,
            onNavigateToPresetEdit = onNavigateToPresetEdit,
            onLogout = onLogout,
            booksViewModel = booksViewModel,
            tasksViewModel = tasksViewModel,
            presetsViewModel = presetsViewModel,
            configViewModel = configViewModel
        )
    }
}

@Composable
private fun CompactLayout(
    navController: NavHostController,
    playerState: PlayerState,
    onPlayChapter: (bookId: Int, chapterId: Int, title: String, bookTitle: String) -> Unit,
    onTogglePlayPause: () -> Unit,
    onNavigateToBookDetail: (Int) -> Unit,
    onNavigateToPresetCreate: () -> Unit,
    onNavigateToPresetEdit: (Int) -> Unit,
    onLogout: () -> Unit,
    booksViewModel: BooksViewModel,
    tasksViewModel: TasksViewModel,
    presetsViewModel: PresetsViewModel,
    configViewModel: ConfigViewModel
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    val showBottomBar = currentRoute in listOf(
        BottomNavItem.Books.route,
        BottomNavItem.Tasks.route,
        BottomNavItem.Presets.route,
        BottomNavItem.Config.route
    )

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                Column {
                    if (playerState.currentTitle.isNotEmpty()) {
                        AudioPlayerBar(
                            playerState = playerState,
                            onTogglePlayPause = onTogglePlayPause
                        )
                    }
                    NavigationBar {
                        listOf(BottomNavItem.Books, BottomNavItem.Tasks, BottomNavItem.Presets, BottomNavItem.Config).forEach { item ->
                            NavigationBarItem(
                                icon = { Icon(item.icon, contentDescription = item.label) },
                                label = { Text(item.label) },
                                selected = currentRoute == item.route,
                                onClick = {
                                    navController.navigate(item.route) {
                                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            when (currentRoute) {
                BottomNavItem.Books.route -> {
                    BooksScreen(
                        onBookClick = onNavigateToBookDetail,
                        viewModel = booksViewModel
                    )
                }
                BottomNavItem.Tasks.route -> {
                    TasksScreen(viewModel = tasksViewModel)
                }
                BottomNavItem.Presets.route -> {
                    PresetsScreen(
                        onCreateClick = onNavigateToPresetCreate,
                        onEditClick = onNavigateToPresetEdit,
                        viewModel = presetsViewModel
                    )
                }
                BottomNavItem.Config.route -> {
                    ConfigScreen(
                        onLogout = onLogout,
                        viewModel = configViewModel
                    )
                }
            }
        }
    }
}

@Composable
private fun ExpandedLayout(
    navController: NavHostController,
    playerState: PlayerState,
    onPlayChapter: (bookId: Int, chapterId: Int, title: String, bookTitle: String) -> Unit,
    onTogglePlayPause: () -> Unit,
    onNavigateToBookDetail: (Int) -> Unit,
    onNavigateToChapter: (Int) -> Unit,
    onNavigateToChapterEdit: (Int) -> Unit,
    onNavigateToPresetCreate: () -> Unit,
    onNavigateToPresetEdit: (Int) -> Unit,
    onLogout: () -> Unit,
    booksViewModel: BooksViewModel,
    tasksViewModel: TasksViewModel,
    presetsViewModel: PresetsViewModel,
    configViewModel: ConfigViewModel
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    val showNavRail = currentRoute in listOf(
        BottomNavItem.Books.route,
        BottomNavItem.Tasks.route,
        BottomNavItem.Presets.route,
        BottomNavItem.Config.route
    )

    var selectedBookId by remember { mutableIntStateOf(0) }
    val bookDetailViewModel: BookDetailViewModel = hiltViewModel()

    Row(modifier = Modifier.fillMaxSize()) {
        if (showNavRail) {
            NavigationRail {
                Spacer(modifier = Modifier.weight(0.3f))
                listOf(BottomNavItem.Books, BottomNavItem.Tasks, BottomNavItem.Presets, BottomNavItem.Config).forEach { item ->
                    NavigationRailItem(
                        icon = { Icon(item.icon, contentDescription = item.label) },
                        label = { Text(item.label) },
                        selected = currentRoute == item.route,
                        onClick = {
                            navController.navigate(item.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
                Spacer(modifier = Modifier.weight(0.7f))
            }
        }

        Column(modifier = Modifier.weight(1f)) {
            when (currentRoute) {
                BottomNavItem.Books.route -> {
                    Row(modifier = Modifier.fillMaxSize().weight(1f)) {
                        Box(modifier = Modifier.weight(0.4f)) {
                            BooksScreen(
                                onBookClick = { bookId ->
                                    selectedBookId = bookId
                                    bookDetailViewModel.loadBook(bookId)
                                },
                                viewModel = booksViewModel
                            )
                        }
                        HorizontalDivider(modifier = Modifier.fillMaxHeight().width(1.dp))
                        Box(modifier = Modifier.weight(0.6f)) {
                            if (selectedBookId > 0) {
                                BookDetailScreen(
                                    bookId = selectedBookId,
                                    onNavigateBack = { selectedBookId = 0 },
                                    onChapterClick = onNavigateToChapter,
                                    onChapterEdit = onNavigateToChapterEdit,
                                    playerState = playerState,
                                    onPlayChapter = { chapterId, title, bookTitle ->
                                        onPlayChapter(selectedBookId, chapterId, title, bookTitle)
                                    },
                                    onTogglePlayPause = onTogglePlayPause,
                                    viewModel = bookDetailViewModel
                                )
                            }
                        }
                    }
                }
                BottomNavItem.Tasks.route -> {
                    TasksScreen(viewModel = tasksViewModel, modifier = Modifier.weight(1f))
                }
                BottomNavItem.Presets.route -> {
                    PresetsScreen(
                        onCreateClick = onNavigateToPresetCreate,
                        onEditClick = onNavigateToPresetEdit,
                        viewModel = presetsViewModel,
                        modifier = Modifier.weight(1f)
                    )
                }
                BottomNavItem.Config.route -> {
                    ConfigScreen(
                        onLogout = onLogout,
                        viewModel = configViewModel
                    )
                }
            }

            if (playerState.currentTitle.isNotEmpty()) {
                AudioPlayerBar(
                    playerState = playerState,
                    onTogglePlayPause = onTogglePlayPause
                )
            }
        }
    }
}
