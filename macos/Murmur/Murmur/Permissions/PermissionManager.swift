import AVFoundation
import AppKit
import CoreGraphics

struct PermissionStatus {
    var microphone: Bool
    var accessibility: Bool
    var inputMonitoring: Bool
}

final class PermissionManager {
    func checkAllPermissions() async -> PermissionStatus {
        let mic = await checkMicrophoneAccess()
        let accessibility = checkAccessibility()
        let inputMonitoring = checkInputMonitoring()

        return PermissionStatus(
            microphone: mic,
            accessibility: accessibility,
            inputMonitoring: inputMonitoring
        )
    }

    func checkMicrophoneAccess() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .audio)
        default:
            return false
        }
    }

    func requestMicrophoneAccess() async {
        let granted = await AVCaptureDevice.requestAccess(for: .audio)
        if !granted {
            showPermissionAlert(
                title: "Microphone Access Required",
                message: "Murmur needs microphone access to record audio for transcription.",
                settingsPane: "Privacy_Microphone"
            )
        }
    }

    func checkAccessibility() -> Bool {
        AXIsProcessTrusted()
    }

    func requestAccessibility() {
        let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue(): true] as CFDictionary
        let trusted = AXIsProcessTrustedWithOptions(options)
        if !trusted {
            showPermissionAlert(
                title: "Accessibility Access Required",
                message: "Murmur needs Accessibility access to paste transcribed text.",
                settingsPane: "Privacy_Accessibility"
            )
        }
    }

    func checkInputMonitoring() -> Bool {
        CGPreflightListenEventAccess()
    }

    func requestInputMonitoring() {
        if !CGPreflightListenEventAccess() {
            CGRequestListenEventAccess()
            showPermissionAlert(
                title: "Input Monitoring Required",
                message: "Murmur needs Input Monitoring access to detect the global hotkey.",
                settingsPane: "Privacy_ListenEvent"
            )
        }
    }

    private func showPermissionAlert(title: String, message: String, settingsPane: String) {
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)

            let alert = NSAlert()
            alert.messageText = title
            alert.informativeText = message + "\n\nAfter granting permission, please restart Murmur."
            alert.alertStyle = .warning
            alert.addButton(withTitle: "Open System Settings")
            alert.addButton(withTitle: "Later")

            if alert.runModal() == .alertFirstButtonReturn {
                let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?\(settingsPane)")!
                NSWorkspace.shared.open(url)
            }
        }
    }
}
