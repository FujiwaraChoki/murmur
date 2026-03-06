import Foundation
import CoreGraphics

final class HotkeyManager {
    var onPress: (() -> Void)?
    var onRelease: (() -> Void)?

    private var targetModifiers: CGEventFlags = [.maskCommand, .maskShift]
    private var targetKeyCode: UInt16 = 49 // space
    private var useKeyCode: Bool = true

    fileprivate var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?
    private var hotkeyThread: Thread?
    private var threadRunLoop: CFRunLoop?
    private var isPressed = false

    func configure(modifiers: CGEventFlags, keyCode: UInt16) {
        targetModifiers = modifiers
        targetKeyCode = keyCode
        useKeyCode = keyCode != 0xFFFF
    }

    func start() {
        let thread = Thread { [weak self] in
            self?.runEventTapLoop()
        }
        thread.name = "com.murmur.hotkey"
        thread.qualityOfService = .userInteractive
        hotkeyThread = thread
        thread.start()
    }

    func stop() {
        if let runLoop = threadRunLoop {
            CFRunLoopStop(runLoop)
        }
        if let tap = eventTap {
            CGEvent.tapEnable(tap: tap, enable: false)
            eventTap = nil
        }
        runLoopSource = nil
        hotkeyThread = nil
        threadRunLoop = nil
        isPressed = false
    }

    private func runEventTapLoop() {
        let eventMask: CGEventMask = (1 << CGEventType.keyDown.rawValue)
            | (1 << CGEventType.keyUp.rawValue)
            | (1 << CGEventType.flagsChanged.rawValue)

        let selfPtr = Unmanaged.passUnretained(self).toOpaque()

        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .listenOnly,
            eventsOfInterest: eventMask,
            callback: hotkeyCallback,
            userInfo: selfPtr
        ) else {
            AppState.shared.log("ERROR: Failed to create CGEventTap - Input Monitoring permission missing")
            return
        }

        AppState.shared.log("CGEventTap created successfully")
        eventTap = tap
        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        runLoopSource = source

        threadRunLoop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
        CFRunLoopRun()
    }

    fileprivate func handleEvent(_ type: CGEventType, _ event: CGEvent) {
        let keyCode = UInt16(event.getIntegerValueField(.keyboardEventKeycode))
        let flags = event.flags

        let relevantFlags: CGEventFlags = [.maskCommand, .maskShift, .maskAlternate, .maskControl]
        let currentModifiers = flags.intersection(relevantFlags)
        let targetMods = targetModifiers.intersection(relevantFlags)
        let modifiersMatch = currentModifiers == targetMods

        AppState.shared.log("handleEvent: type=\(type.rawValue) keyCode=\(keyCode) currentMods=\(currentModifiers.rawValue) targetMods=\(targetMods.rawValue) match=\(modifiersMatch) useKeyCode=\(useKeyCode) targetKey=\(targetKeyCode)")

        switch type {
        case .flagsChanged:
            if !useKeyCode {
                if modifiersMatch && !isPressed {
                    isPressed = true
                    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                        self?.onPress?()
                    }
                } else if !modifiersMatch && isPressed {
                    isPressed = false
                    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                        self?.onRelease?()
                    }
                }
            }

        case .keyDown:
            if useKeyCode && keyCode == targetKeyCode && modifiersMatch && !isPressed {
                AppState.shared.log("HOTKEY MATCH - keyDown detected!")
                isPressed = true
                DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                    self?.onPress?()
                }
            }

        case .keyUp:
            if useKeyCode && keyCode == targetKeyCode && isPressed {
                AppState.shared.log("HOTKEY MATCH - keyUp detected!")
                isPressed = false
                DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                    self?.onRelease?()
                }
            }

        default:
            break
        }
    }
}

private func hotkeyCallback(
    proxy: CGEventTapProxy,
    type: CGEventType,
    event: CGEvent,
    userInfo: UnsafeMutableRawPointer?
) -> Unmanaged<CGEvent>? {
    guard let userInfo = userInfo else { return Unmanaged.passUnretained(event) }
    let manager = Unmanaged<HotkeyManager>.fromOpaque(userInfo).takeUnretainedValue()

    // Re-enable the tap if the system disabled it
    if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
        if let tap = manager.eventTap {
            CGEvent.tapEnable(tap: tap, enable: true)
            AppState.shared.log("Event tap re-enabled after disable (type=\(type.rawValue))")
        }
        return Unmanaged.passUnretained(event)
    }

    manager.handleEvent(type, event)
    return Unmanaged.passUnretained(event)
}
