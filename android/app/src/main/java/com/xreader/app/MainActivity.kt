package com.xreader.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.windowsizeclass.ExperimentalMaterial3WindowSizeClassApi
import androidx.compose.material3.windowsizeclass.calculateWindowSizeClass
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.rememberNavController
import com.xreader.app.data.local.SettingsStore
import com.xreader.app.data.repository.ApiRepository
import com.xreader.app.service.AudioPlayerManager
import com.xreader.app.ui.navigation.AppNavGraph
import com.xreader.app.ui.navigation.Screen
import com.xreader.app.ui.theme.XReaderTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var repository: ApiRepository
    @Inject lateinit var audioPlayerManager: AudioPlayerManager
    @Inject lateinit var settingsStore: SettingsStore

    @OptIn(ExperimentalMaterial3WindowSizeClassApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            val windowSizeClass = calculateWindowSizeClass(this)
            val navController = rememberNavController()
            val playerState by audioPlayerManager.playerState.collectAsStateWithLifecycle()

            LaunchedEffect(Unit) {
                while (true) {
                    audioPlayerManager.updatePosition()
                    kotlinx.coroutines.delay(250)
                }
            }

            XReaderTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val startDestination = determineStartDestination()

                    AppNavGraph(
                        navController = navController,
                        windowSizeClass = windowSizeClass,
                        playerState = playerState,
                        audioPlayerManager = audioPlayerManager,
                        repository = repository,
                        startDestination = startDestination
                    )
                }
            }
        }
    }

    private fun determineStartDestination(): String {
        val serverUrl = runBlocking { settingsStore.serverUrl.first() }
        if (serverUrl == SettingsStore.DEFAULT_SERVER_URL) {
            return Screen.Setup.route
        }
        val hasToken = repository.tokenStore.token != null
        return if (hasToken) Screen.Main.route else Screen.Setup.route
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isFinishing) {
            audioPlayerManager.release()
        }
    }
}
