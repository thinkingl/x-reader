package com.xreader.app.service

import android.content.Context
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AudioPlayerManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val _playerState = MutableStateFlow(PlayerState())
    val playerState: StateFlow<PlayerState> = _playerState.asStateFlow()

    val exoPlayer: ExoPlayer = ExoPlayer.Builder(context).build().apply {
        addListener(object : Player.Listener {
            override fun onIsPlayingChanged(isPlaying: Boolean) {
                updateState { it.copy(isPlaying = isPlaying) }
            }
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_READY -> {
                        updateState { it.copy(isBuffering = false, duration = exoPlayer.duration.coerceAtLeast(0)) }
                    }
                    Player.STATE_BUFFERING -> {
                        updateState { it.copy(isBuffering = true) }
                    }
                    Player.STATE_ENDED -> {
                        updateState { it.copy(isPlaying = false) }
                    }
                }
            }
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                updateState {
                    it.copy(
                        currentTitle = mediaItem?.mediaMetadata?.title?.toString() ?: "",
                        currentBookTitle = mediaItem?.mediaMetadata?.artist?.toString() ?: ""
                    )
                }
            }
            override fun onPlayerError(error: PlaybackException) {
                updateState { it.copy(error = error.message) }
            }
        })
    }

    fun play(url: String, title: String, bookTitle: String) {
        val mediaItem = MediaItem.Builder()
            .setUri(url)
            .setMediaMetadata(
                MediaMetadata.Builder()
                    .setTitle(title)
                    .setArtist(bookTitle)
                    .build()
            )
            .build()
        exoPlayer.setMediaItem(mediaItem)
        exoPlayer.prepare()
        exoPlayer.play()
        updateState {
            it.copy(
                currentTitle = title,
                currentBookTitle = bookTitle,
                error = null
            )
        }
    }

    fun togglePlayPause() {
        if (exoPlayer.isPlaying) {
            exoPlayer.pause()
        } else {
            exoPlayer.play()
        }
    }

    fun seekTo(positionMs: Long) {
        exoPlayer.seekTo(positionMs)
    }

    fun stop() {
        exoPlayer.stop()
        updateState { PlayerState() }
    }

    fun clearError() {
        updateState { it.copy(error = null) }
    }

    fun updatePosition() {
        updateState {
            it.copy(
                currentPosition = exoPlayer.currentPosition.coerceAtLeast(0),
                duration = exoPlayer.duration.coerceAtLeast(0)
            )
        }
    }

    private fun updateState(transform: (PlayerState) -> PlayerState) {
        _playerState.value = transform(_playerState.value)
    }

    fun release() {
        exoPlayer.release()
    }
}

data class PlayerState(
    val isPlaying: Boolean = false,
    val isBuffering: Boolean = false,
    val currentTitle: String = "",
    val currentBookTitle: String = "",
    val currentPosition: Long = 0,
    val duration: Long = 0,
    val error: String? = null
)
