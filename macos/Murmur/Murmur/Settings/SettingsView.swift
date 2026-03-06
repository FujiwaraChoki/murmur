import SwiftUI
import AVFoundation

struct SettingsView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        TabView {
            GeneralSettingsView()
                .environmentObject(appState)
                .tabItem {
                    Label("General", systemImage: "gear")
                }

            AboutView()
                .tabItem {
                    Label("About", systemImage: "info.circle")
                }
        }
        .frame(width: 400, height: 250)
    }
}

struct GeneralSettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var availableDevices: [AudioDevice] = []
    @AppStorage("selectedMicrophoneID") private var selectedMicrophoneID: String = ""

    var body: some View {
        Form {
            Section("Hotkey") {
                HotkeyRecorderView(
                    modifiers: CGEventFlags(rawValue: UInt64(appState.hotkeyModifiers)),
                    keyCode: UInt16(appState.hotkeyKeyCode)
                ) { modifiers, keyCode in
                    appState.updateHotkey(modifiers: modifiers, keyCode: keyCode)
                }
            }

            Section("Microphone") {
                Picker("Input Device", selection: $selectedMicrophoneID) {
                    Text("System Default").tag("")
                    ForEach(availableDevices, id: \.id) { device in
                        Text(device.name).tag(device.id)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            availableDevices = AudioDevice.availableInputDevices()
        }
    }
}

struct AboutView: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "mic.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(.blue)

            Text("Murmur")
                .font(.title)
                .fontWeight(.bold)

            Text("Voice Dictation for macOS")
                .foregroundStyle(.secondary)

            Text("Version 1.0.0")
                .font(.caption)
                .foregroundStyle(.tertiary)

            Text("Powered by FluidAudio (CoreML)")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct AudioDevice: Identifiable {
    let id: String
    let name: String

    static func availableInputDevices() -> [AudioDevice] {
        let discoverySession = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone],
            mediaType: .audio,
            position: .unspecified
        )

        return discoverySession.devices.map { device in
            AudioDevice(id: device.uniqueID, name: device.localizedName)
        }
    }
}
