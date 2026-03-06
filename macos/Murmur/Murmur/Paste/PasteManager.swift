import AppKit
import CoreGraphics

final class PasteManager {
    private static let restoreDelay: TimeInterval = 0.15

    func paste(text: String) {
        let pasteboard = NSPasteboard.general
        let savedContents = savePasteboard(pasteboard)

        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)

        simulateCmdV()

        DispatchQueue.main.asyncAfter(deadline: .now() + Self.restoreDelay) {
            self.restorePasteboard(pasteboard, contents: savedContents)
        }
    }

    private func simulateCmdV() {
        let vKeyCode: UInt16 = 9

        let source = CGEventSource(stateID: .hidSystemState)

        guard let keyDown = CGEvent(keyboardEventSource: source, virtualKey: vKeyCode, keyDown: true),
              let keyUp = CGEvent(keyboardEventSource: source, virtualKey: vKeyCode, keyDown: false)
        else { return }

        keyDown.flags = .maskCommand
        keyUp.flags = .maskCommand

        keyDown.post(tap: .cghidEventTap)
        keyUp.post(tap: .cghidEventTap)
    }

    private func savePasteboard(_ pasteboard: NSPasteboard) -> [NSPasteboardItem] {
        guard let items = pasteboard.pasteboardItems else { return [] }

        return items.compactMap { item -> NSPasteboardItem? in
            let newItem = NSPasteboardItem()
            for type in item.types {
                if let data = item.data(forType: type) {
                    newItem.setData(data, forType: type)
                }
            }
            return newItem
        }
    }

    private func restorePasteboard(_ pasteboard: NSPasteboard, contents: [NSPasteboardItem]) {
        pasteboard.clearContents()
        if !contents.isEmpty {
            pasteboard.writeObjects(contents)
        }
    }
}
