import SwiftUI
import AppKit
import Carbon.HIToolbox

struct HotkeyRecorderView: View {
    let modifiers: CGEventFlags
    let keyCode: UInt16
    let onRecord: (CGEventFlags, UInt16) -> Void

    @State private var isRecording = false

    var body: some View {
        HStack {
            Text(displayString)
                .frame(minWidth: 120)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(isRecording ? Color.accentColor.opacity(0.2) : Color.secondary.opacity(0.1))
                .cornerRadius(6)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(isRecording ? Color.accentColor : Color.clear, lineWidth: 1)
                )

            Button(isRecording ? "Cancel" : "Record") {
                isRecording.toggle()
            }
            .buttonStyle(.bordered)
        }
        .background(
            HotkeyRecorderNSView(isRecording: $isRecording, onRecord: onRecord)
                .frame(width: 0, height: 0)
        )
    }

    private var displayString: String {
        if isRecording {
            return "Press hotkey..."
        }
        return KeyCodeMap.displayString(modifiers: modifiers, keyCode: keyCode)
    }
}

struct HotkeyRecorderNSView: NSViewRepresentable {
    @Binding var isRecording: Bool
    let onRecord: (CGEventFlags, UInt16) -> Void

    func makeNSView(context: Context) -> KeyCaptureView {
        let view = KeyCaptureView()
        view.delegate = context.coordinator
        return view
    }

    func updateNSView(_ nsView: KeyCaptureView, context: Context) {
        nsView.isCapturing = isRecording
        if isRecording {
            nsView.window?.makeFirstResponder(nsView)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    final class Coordinator: NSObject, KeyCaptureDelegate {
        let parent: HotkeyRecorderNSView

        init(_ parent: HotkeyRecorderNSView) {
            self.parent = parent
        }

        func didCaptureHotkey(modifiers: CGEventFlags, keyCode: UInt16) {
            parent.isRecording = false
            parent.onRecord(modifiers, keyCode)
        }
    }
}

protocol KeyCaptureDelegate: AnyObject {
    func didCaptureHotkey(modifiers: CGEventFlags, keyCode: UInt16)
}

final class KeyCaptureView: NSView {
    weak var delegate: KeyCaptureDelegate?
    var isCapturing = false

    override var acceptsFirstResponder: Bool { true }

    override func keyDown(with event: NSEvent) {
        guard isCapturing else {
            super.keyDown(with: event)
            return
        }

        if event.keyCode == UInt16(kVK_Escape) {
            isCapturing = false
            return
        }

        let modifiers = cgEventFlags(from: event.modifierFlags)
        delegate?.didCaptureHotkey(modifiers: modifiers, keyCode: event.keyCode)
    }

    override func flagsChanged(with event: NSEvent) {
        guard isCapturing else {
            super.flagsChanged(with: event)
            return
        }

        let modifiers = cgEventFlags(from: event.modifierFlags)
        let relevantModifiers: NSEvent.ModifierFlags = [.command, .shift, .option, .control]
        let hasModifiers = !event.modifierFlags.intersection(relevantModifiers).isEmpty

        // Record modifier-only hotkey when at least 2 modifiers are held
        if hasModifiers {
            let modCount = [
                event.modifierFlags.contains(.command),
                event.modifierFlags.contains(.shift),
                event.modifierFlags.contains(.option),
                event.modifierFlags.contains(.control),
            ].filter { $0 }.count

            if modCount >= 2 {
                delegate?.didCaptureHotkey(modifiers: modifiers, keyCode: 0xFFFF)
            }
        }
    }

    private func cgEventFlags(from nsFlags: NSEvent.ModifierFlags) -> CGEventFlags {
        var flags: CGEventFlags = []
        if nsFlags.contains(.command) { flags.insert(.maskCommand) }
        if nsFlags.contains(.shift) { flags.insert(.maskShift) }
        if nsFlags.contains(.option) { flags.insert(.maskAlternate) }
        if nsFlags.contains(.control) { flags.insert(.maskControl) }
        return flags
    }
}
