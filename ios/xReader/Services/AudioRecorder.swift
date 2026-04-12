import AVFoundation
import Foundation
import SwiftUI

@MainActor
class AudioRecorder: NSObject, ObservableObject, AVAudioRecorderDelegate {
    @Published var isRecording = false
    @Published var recordingTime: Double = 0
    @Published var recordedURL: URL?

    private var recorder: AVAudioRecorder?
    private var timer: Timer?
    private let maxDuration: Double = 10.0

    override init() {
        super.init()
    }

    func startRecording() {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .default)
            try session.setActive(true)
        } catch {
            return
        }
        #endif

        let url = FileManager.default.temporaryDirectory.appendingPathComponent("recording_\(UUID().uuidString).wav")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]

        do {
            recorder = try AVAudioRecorder(url: url, settings: settings)
            recorder?.delegate = self
            recorder?.record(forDuration: maxDuration)
            isRecording = true
            recordingTime = 0
            recordedURL = nil

            timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.isRecording else { return }
                    self.recordingTime = self.recorder?.currentTime ?? 0
                    if self.recordingTime >= self.maxDuration {
                        self.stopRecording()
                    }
                }
            }
        } catch {
            // Recording failed
        }
    }

    func stopRecording() {
        recorder?.stop()
        timer?.invalidate()
        timer = nil
        isRecording = false
        recordedURL = recorder?.url

        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false)
        #endif
    }

    func cancelRecording() {
        if let url = recorder?.url {
            try? FileManager.default.removeItem(at: url)
        }
        recorder?.stop()
        timer?.invalidate()
        timer = nil
        isRecording = false
        recordingTime = 0
        recordedURL = nil

        #if os(iOS)
        try? AVAudioSession.sharedInstance().setActive(false)
        #endif
    }

    // AVAudioRecorderDelegate
    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        Task { @MainActor in
            self.isRecording = false
            self.timer?.invalidate()
            self.timer = nil
            if flag {
                self.recordedURL = recorder.url
            }
        }
    }
}
