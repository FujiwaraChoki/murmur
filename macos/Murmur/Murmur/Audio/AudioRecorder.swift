import AVFoundation
import Foundation

final class AudioRecorder {
    var onSpectrumUpdate: (([Float]) -> Void)?

    private var engine: AVAudioEngine?
    private var buffer: [Float] = []
    private let bufferLock = NSLock()
    private var isRecording = false
    private var smoothedSpectrum = Array(repeating: Float(0.08), count: AudioRecorder.analysisBandCount)

    private static let targetSampleRate: Double = 16000
    private static let targetChannels: AVAudioChannelCount = 1
    private static let analysisBandCount = 9
    private static let analysisWindowSize = 128

    func startRecording(deviceID: String? = nil) throws {
        guard !isRecording else { return }

        let engine = AVAudioEngine()

        if let deviceID = deviceID {
            setInputDevice(deviceID, on: engine)
        }

        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)

        guard let targetFormat = AVAudioFormat(
            commonFormat: .pcmFormatFloat32,
            sampleRate: Self.targetSampleRate,
            channels: Self.targetChannels,
            interleaved: false
        ) else {
            throw AudioRecorderError.formatCreationFailed
        }

        guard let converter = AVAudioConverter(from: inputFormat, to: targetFormat) else {
            throw AudioRecorderError.converterCreationFailed
        }

        bufferLock.lock()
        buffer.removeAll()
        smoothedSpectrum = Array(repeating: Float(0.08), count: Self.analysisBandCount)
        bufferLock.unlock()

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] pcmBuffer, _ in
            self?.processAudioBuffer(pcmBuffer, converter: converter, targetFormat: targetFormat)
        }

        try engine.start()
        self.engine = engine
        isRecording = true
    }

    func stopRecording() -> [Float] {
        guard isRecording else { return [] }

        engine?.inputNode.removeTap(onBus: 0)
        engine?.stop()
        engine = nil
        isRecording = false

        bufferLock.lock()
        let samples = buffer
        buffer.removeAll()
        smoothedSpectrum = Array(repeating: Float(0.08), count: Self.analysisBandCount)
        bufferLock.unlock()

        DispatchQueue.main.async { [weak self] in
            self?.onSpectrumUpdate?(Array(repeating: 0.08, count: Self.analysisBandCount))
        }

        return samples
    }

    private func processAudioBuffer(
        _ pcmBuffer: AVAudioPCMBuffer,
        converter: AVAudioConverter,
        targetFormat: AVAudioFormat
    ) {
        let frameCount = AVAudioFrameCount(
            Double(pcmBuffer.frameLength) * Self.targetSampleRate / pcmBuffer.format.sampleRate
        )
        guard frameCount > 0 else { return }

        guard let convertedBuffer = AVAudioPCMBuffer(
            pcmFormat: targetFormat,
            frameCapacity: frameCount
        ) else { return }

        var error: NSError?
        let status = converter.convert(to: convertedBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return pcmBuffer
        }

        guard status != .error, error == nil else { return }

        if let channelData = convertedBuffer.floatChannelData {
            let samples = Array(UnsafeBufferPointer(
                start: channelData[0],
                count: Int(convertedBuffer.frameLength)
            ))

            bufferLock.lock()
            buffer.append(contentsOf: samples)
            bufferLock.unlock()

            let spectrum = analyzeFrequencyBands(from: samples)
            DispatchQueue.main.async { [weak self] in
                self?.onSpectrumUpdate?(spectrum)
            }
        }
    }

    private func analyzeFrequencyBands(from samples: [Float]) -> [Float] {
        let sampleCount = min(samples.count, Self.analysisWindowSize)
        guard sampleCount >= 32 else {
            return smoothedSpectrum
        }

        let recentSamples = Array(samples.suffix(sampleCount))
        let halfCount = recentSamples.count / 2
        guard halfCount > 1 else {
            return smoothedSpectrum
        }

        var windowed = [Float](repeating: 0, count: recentSamples.count)
        let denominator = Float(max(recentSamples.count - 1, 1))

        for index in recentSamples.indices {
            let window = 0.5 - 0.5 * cos((2 * .pi * Float(index)) / denominator)
            windowed[index] = recentSamples[index] * window
        }

        var magnitudes = [Float](repeating: 0, count: halfCount)
        let normalization = 1 / Float(recentSamples.count)

        for frequencyBin in 1..<halfCount {
            var real: Float = 0
            var imaginary: Float = 0

            for sampleIndex in recentSamples.indices {
                let angle = (2 * .pi * Float(frequencyBin * sampleIndex)) / Float(recentSamples.count)
                let sample = windowed[sampleIndex]
                real += sample * cos(angle)
                imaginary -= sample * sin(angle)
            }

            magnitudes[frequencyBin] = sqrt(real * real + imaginary * imaginary) * normalization
        }

        let bandEdges = [1, 2, 3, 5, 8, 12, 18, 27, 40, halfCount]
        let rms = sqrt(recentSamples.reduce(into: Float(0)) { partial, sample in
            partial += sample * sample
        } / Float(recentSamples.count))

        for bandIndex in 0..<Self.analysisBandCount {
            let start = min(bandEdges[bandIndex], halfCount - 1)
            let end = min(max(bandEdges[bandIndex + 1], start + 1), halfCount)
            guard start < end else { continue }

            let bandSlice = magnitudes[start..<end]
            let averageMagnitude = bandSlice.reduce(0, +) / Float(bandSlice.count)
            let boostedMagnitude = sqrt(averageMagnitude * 14)
            let combinedLevel = min(max((boostedMagnitude * 0.8) + (rms * 3.5), 0.05), 1)

            let previousLevel = smoothedSpectrum[bandIndex]
            let smoothedLevel: Float
            if combinedLevel > previousLevel {
                smoothedLevel = (previousLevel * 0.4) + (combinedLevel * 0.6)
            } else {
                smoothedLevel = (previousLevel * 0.82) + (combinedLevel * 0.18)
            }

            smoothedSpectrum[bandIndex] = min(max(smoothedLevel, 0.05), 1)
        }

        return smoothedSpectrum
    }

    private func setInputDevice(_ deviceID: String, on engine: AVAudioEngine) {
        if let audioDeviceID = AudioDeviceID(deviceID) {
            var id = audioDeviceID
            let unit = engine.inputNode.audioUnit!
            AudioUnitSetProperty(
                unit,
                kAudioOutputUnitProperty_CurrentDevice,
                kAudioUnitScope_Global,
                0,
                &id,
                UInt32(MemoryLayout<AudioDeviceID>.size)
            )
        }
    }
}

enum AudioRecorderError: LocalizedError {
    case formatCreationFailed
    case converterCreationFailed

    var errorDescription: String? {
        switch self {
        case .formatCreationFailed:
            return "Failed to create target audio format"
        case .converterCreationFailed:
            return "Failed to create audio converter"
        }
    }
}
