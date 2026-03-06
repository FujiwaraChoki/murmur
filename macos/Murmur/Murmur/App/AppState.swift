import Foundation
import SwiftUI

enum AppStateValue: Equatable {
    case launching
    case downloadingModel(Double)
    case loading
    case idle
    case recording
    case transcribing
    case error(String)

    static func == (lhs: AppStateValue, rhs: AppStateValue) -> Bool {
        switch (lhs, rhs) {
        case (.launching, .launching),
             (.loading, .loading),
             (.idle, .idle),
             (.recording, .recording),
             (.transcribing, .transcribing):
            return true
        case (.downloadingModel(let a), .downloadingModel(let b)):
            return a == b
        case (.error(let a), .error(let b)):
            return a == b
        default:
            return false
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()

    @Published private(set) var state: AppStateValue = .launching {
        didSet { log("State -> \(state)") }
    }

    private let audioRecorder = AudioRecorder()
    private let transcriptionManager = TranscriptionManager()
    private let hotkeyManager = HotkeyManager()
    private let pasteManager = PasteManager()
    private let permissionManager = PermissionManager()
    private var indicatorWindow: IndicatorWindow?

    // CGEventFlags: .maskCommand=0x100000, .maskShift=0x020000
    @AppStorage("hotkeyModifiers") var hotkeyModifiers: Int = 0x120000 // cmd+shift
    @AppStorage("hotkeyKeyCode") var hotkeyKeyCode: Int = 49 // space
    @AppStorage("selectedMicrophoneID") var selectedMicrophoneID: String = ""

    nonisolated func log(_ msg: String) {
        let entry = "\(Date()): \(msg)\n"
        let path = "/tmp/murmur_debug.log"
        if let handle = FileHandle(forWritingAtPath: path) {
            handle.seekToEndOfFile()
            handle.write(entry.data(using: .utf8)!)
            handle.closeFile()
        } else {
            FileManager.default.createFile(atPath: path, contents: entry.data(using: .utf8))
        }
    }

    func start() async {
        log("start() called")
        state = .launching

        setupOverlay()

        let permissions = await permissionManager.checkAllPermissions()
        log("Permissions: mic=\(permissions.microphone) accessibility=\(permissions.accessibility) inputMonitoring=\(permissions.inputMonitoring)")

        if !permissions.microphone {
            await permissionManager.requestMicrophoneAccess()
        }
        if !permissions.inputMonitoring {
            permissionManager.requestInputMonitoring()
        }
        if !permissions.accessibility {
            permissionManager.requestAccessibility()
        }

        setupHotkey()
        await loadModel()
    }

    func retryModelLoad() async {
        await loadModel()
    }

    private func loadModel() async {
        state = .loading
        indicatorWindow?.updateState(.downloadingModel)

        do {
            try await transcriptionManager.loadModel()
            log("Model loaded, state -> idle")
            state = .idle
            indicatorWindow?.updateState(.idle)
        } catch {
            log("Model load FAILED: \(error.localizedDescription)")
            state = .error("Model load failed: \(error.localizedDescription)")
            indicatorWindow?.updateState(.error)
        }
    }

    private func setupOverlay() {
        indicatorWindow = IndicatorWindow()
        indicatorWindow?.show()
        audioRecorder.onSpectrumUpdate = { [weak self] bands in
            self?.indicatorWindow?.updateSpectrum(bands)
        }
    }

    private func setupHotkey() {
        log("setupHotkey: modifiers=\(hotkeyModifiers) keyCode=\(hotkeyKeyCode)")
        hotkeyManager.configure(
            modifiers: CGEventFlags(rawValue: UInt64(hotkeyModifiers)),
            keyCode: UInt16(hotkeyKeyCode)
        )

        hotkeyManager.onPress = { [weak self] in
            AppState.shared.log("Hotkey PRESSED")
            Task { @MainActor in
                await self?.startRecording()
            }
        }

        hotkeyManager.onRelease = { [weak self] in
            AppState.shared.log("Hotkey RELEASED")
            Task { @MainActor in
                await self?.stopRecordingAndTranscribe()
            }
        }

        hotkeyManager.start()
    }

    private func startRecording() async {
        log("startRecording called, state=\(state)")
        guard state == .idle else { return }
        state = .recording
        indicatorWindow?.updateState(.recording)

        let micID = selectedMicrophoneID.isEmpty ? nil : selectedMicrophoneID
        do {
            try audioRecorder.startRecording(deviceID: micID)
        } catch {
            state = .error("Recording failed: \(error.localizedDescription)")
            indicatorWindow?.updateState(.error)
        }
    }

    private func stopRecordingAndTranscribe() async {
        guard state == .recording else { return }

        let samples = audioRecorder.stopRecording()
        guard !samples.isEmpty else {
            state = .idle
            indicatorWindow?.updateState(.idle)
            return
        }

        state = .transcribing
        indicatorWindow?.updateState(.transcribing)

        do {
            let text = try await transcriptionManager.transcribe(samples: samples)
            if !text.isEmpty {
                pasteManager.paste(text: text)
            }
            state = .idle
            indicatorWindow?.updateState(.idle)
        } catch {
            state = .error("Transcription failed: \(error.localizedDescription)")
            indicatorWindow?.updateState(.error)
            // Auto-recover to idle after 3 seconds
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            if case .error = state {
                state = .idle
                indicatorWindow?.updateState(.idle)
            }
        }
    }

    func updateHotkey(modifiers: CGEventFlags, keyCode: UInt16) {
        hotkeyModifiers = Int(modifiers.rawValue)
        hotkeyKeyCode = Int(keyCode)
        hotkeyManager.configure(modifiers: modifiers, keyCode: keyCode)
        hotkeyManager.stop()
        hotkeyManager.start()
    }
}
