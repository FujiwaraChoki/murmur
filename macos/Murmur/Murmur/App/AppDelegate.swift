import AppKit
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        Task { @MainActor in
            await AppState.shared.start()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup handled by AppState
    }
}
