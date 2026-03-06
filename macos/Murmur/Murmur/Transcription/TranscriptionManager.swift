import Foundation
import FluidAudio

actor TranscriptionManager {
    private var asrManager: AsrManager?
    private var isLoaded = false

    func loadModel() async throws {
        let models = try await AsrModels.downloadAndLoad(version: .v3)

        let asrManager = AsrManager(config: .default)
        try await asrManager.initialize(models: models)
        self.asrManager = asrManager
        isLoaded = true
    }

    func transcribe(samples: [Float]) async throws -> String {
        guard let asrManager = asrManager else {
            throw TranscriptionError.modelNotLoaded
        }

        let result = try await asrManager.transcribe(samples, source: .microphone)
        return result.text.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var modelLoaded: Bool {
        isLoaded
    }
}

enum TranscriptionError: LocalizedError {
    case modelNotLoaded

    var errorDescription: String? {
        switch self {
        case .modelNotLoaded:
            return "Transcription model is not loaded"
        }
    }
}
