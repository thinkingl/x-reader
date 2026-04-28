package com.xreader.app.ui.presets

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xreader.app.data.model.*
import com.xreader.app.data.repository.ApiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PresetsUiState(
    val presets: List<VoicePresetResponse> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

data class PresetEditState(
    val name: String = "",
    val voiceMode: String = "clone",
    val instruct: String = "",
    val language: String = "",
    val numStep: Int = 32,
    val guidanceScale: Double = 2.0,
    val speed: Double = 1.0,
    val refText: String = "",
    val refAudioPath: String? = null,
    val isUploading: Boolean = false,
    val isSaving: Boolean = false,
    val isTesting: Boolean = false,
    val testResult: TestAudioResponse? = null,
    val testText: String = "这是一段测试语音，用于验证当前预设的效果。",
    val error: String? = null,
    val saved: Boolean = false
)

@HiltViewModel
class PresetsViewModel @Inject constructor(
    private val repository: ApiRepository
) : ViewModel() {

    private val _listState = MutableStateFlow(PresetsUiState())
    val listState: StateFlow<PresetsUiState> = _listState.asStateFlow()

    private val _editState = MutableStateFlow(PresetEditState())
    val editState: StateFlow<PresetEditState> = _editState.asStateFlow()

    init {
        loadPresets()
    }

    fun loadPresets() {
        viewModelScope.launch {
            _listState.value = _listState.value.copy(isLoading = true)
            try {
                val result = repository.getVoicePresets()
                _listState.value = _listState.value.copy(
                    presets = result.items,
                    isLoading = false,
                    error = null
                )
            } catch (e: Exception) {
                _listState.value = _listState.value.copy(
                    isLoading = false,
                    error = e.message ?: "加载失败"
                )
            }
        }
    }

    fun deletePreset(id: Int) {
        viewModelScope.launch {
            try {
                repository.deleteVoicePreset(id)
                _listState.value = _listState.value.copy(
                    presets = _listState.value.presets.filter { it.id != id }
                )
            } catch (e: Exception) {
                _listState.value = _listState.value.copy(error = "删除失败: ${e.message}")
            }
        }
    }

    fun initEditForm(preset: VoicePresetResponse? = null) {
        if (preset != null) {
            _editState.value = PresetEditState(
                name = preset.name,
                voiceMode = preset.voiceMode,
                instruct = preset.instruct ?: "",
                language = preset.language ?: "",
                numStep = preset.numStep,
                guidanceScale = preset.guidanceScale,
                speed = preset.speed,
                refText = preset.refText ?: "",
                refAudioPath = preset.refAudioPath
            )
        } else {
            _editState.value = PresetEditState()
        }
    }

    fun updateName(v: String) { _editState.value = _editState.value.copy(name = v) }
    fun updateVoiceMode(v: String) { _editState.value = _editState.value.copy(voiceMode = v) }
    fun updateInstruct(v: String) { _editState.value = _editState.value.copy(instruct = v) }
    fun updateLanguage(v: String) { _editState.value = _editState.value.copy(language = v) }
    fun updateNumStep(v: Int) { _editState.value = _editState.value.copy(numStep = v) }
    fun updateGuidanceScale(v: Double) { _editState.value = _editState.value.copy(guidanceScale = v) }
    fun updateSpeed(v: Double) { _editState.value = _editState.value.copy(speed = v) }
    fun updateRefText(v: String) { _editState.value = _editState.value.copy(refText = v) }
    fun updateTestText(v: String) { _editState.value = _editState.value.copy(testText = v) }

    fun uploadReferenceAudio(uri: Uri) {
        viewModelScope.launch {
            _editState.value = _editState.value.copy(isUploading = true)
            try {
                val result = repository.uploadReferenceAudio(uri)
                _editState.value = _editState.value.copy(
                    refAudioPath = result.audioPath,
                    refText = if (result.transcribedText.isNotEmpty()) result.transcribedText else _editState.value.refText,
                    isUploading = false
                )
            } catch (e: Exception) {
                _editState.value = _editState.value.copy(
                    isUploading = false,
                    error = "上传失败: ${e.message}"
                )
            }
        }
    }

    fun createPreset() {
        val state = _editState.value
        viewModelScope.launch {
            _editState.value = _editState.value.copy(isSaving = true)
            try {
                repository.createVoicePreset(
                    VoicePresetCreate(
                        name = state.name,
                        isDefault = false,
                        voiceMode = state.voiceMode,
                        instruct = if (state.voiceMode == "design") state.instruct else null,
                        refAudioPath = if (state.voiceMode == "clone") state.refAudioPath else null,
                        refText = if (state.voiceMode == "clone") state.refText else null,
                        numStep = state.numStep,
                        guidanceScale = state.guidanceScale,
                        speed = state.speed,
                        language = if (state.voiceMode == "design" && state.language.isNotEmpty()) state.language else null
                    )
                )
                _editState.value = _editState.value.copy(isSaving = false, saved = true)
                loadPresets()
            } catch (e: Exception) {
                _editState.value = _editState.value.copy(
                    isSaving = false,
                    error = "保存失败: ${e.message}"
                )
            }
        }
    }

    fun updatePreset(presetId: Int) {
        val state = _editState.value
        viewModelScope.launch {
            _editState.value = _editState.value.copy(isSaving = true)
            try {
                repository.updateVoicePreset(
                    presetId,
                    VoicePresetUpdate(
                        name = state.name,
                        voiceMode = state.voiceMode,
                        instruct = if (state.voiceMode == "design") state.instruct else null,
                        refText = if (state.voiceMode == "clone") state.refText else null,
                        numStep = state.numStep,
                        guidanceScale = state.guidanceScale,
                        speed = state.speed,
                        language = if (state.voiceMode == "design" && state.language.isNotEmpty()) state.language else null
                    )
                )
                _editState.value = _editState.value.copy(isSaving = false, saved = true)
                loadPresets()
            } catch (e: Exception) {
                _editState.value = _editState.value.copy(
                    isSaving = false,
                    error = "保存失败: ${e.message}"
                )
            }
        }
    }

    fun testPreset(presetId: Int) {
        viewModelScope.launch {
            _editState.value = _editState.value.copy(isTesting = true, testResult = null)
            try {
                val result = repository.testTts(_editState.value.testText, presetId)
                _editState.value = _editState.value.copy(isTesting = false, testResult = result)
            } catch (e: Exception) {
                _editState.value = _editState.value.copy(
                    isTesting = false,
                    error = "测试失败: ${e.message}"
                )
            }
        }
    }

    fun clearEditError() { _editState.value = _editState.value.copy(error = null) }
    fun clearListError() { _listState.value = _listState.value.copy(error = null) }
    fun clearSaved() { _editState.value = _editState.value.copy(saved = false) }
}
