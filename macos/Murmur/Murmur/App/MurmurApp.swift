import SwiftUI

@main
struct MurmurApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Image(systemName: menuBarIcon)
                .symbolRenderingMode(.hierarchical)
        }
    }

    private var menuBarIcon: String {
        switch appState.state {
        case .recording:
            return "mic.fill"
        case .transcribing:
            return "text.bubble"
        case .error:
            return "exclamationmark.triangle"
        default:
            return "mic"
        }
    }
}

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Murmur")
                .font(.headline)

            Divider()

            switch appState.state {
            case .launching:
                Label("Starting...", systemImage: "hourglass")
            case .downloadingModel(let progress):
                Label("Downloading model: \(Int(progress * 100))%", systemImage: "arrow.down.circle")
            case .loading:
                Label("Loading model...", systemImage: "brain")
            case .idle:
                Label("Ready", systemImage: "checkmark.circle")
                    .foregroundColor(.green)
            case .recording:
                Label("Recording...", systemImage: "mic.fill")
                    .foregroundColor(.red)
            case .transcribing:
                Label("Transcribing...", systemImage: "text.bubble")
                    .foregroundColor(.orange)
            case .error(let message):
                Label(message, systemImage: "exclamationmark.triangle")
                    .foregroundColor(.red)
                Button("Retry") {
                    Task { await appState.retryModelLoad() }
                }
            }

            Divider()

            Button("Settings...") {
                SettingsWindowController.shared.showWindow()
            }

            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
            .keyboardShortcut("q")
        }
        .padding(8)
    }
}
