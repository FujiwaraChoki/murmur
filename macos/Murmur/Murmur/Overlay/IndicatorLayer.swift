import QuartzCore
import AppKit

final class IndicatorLayer: CALayer {
    @NSManaged private var recordingTransitionProgress: CGFloat

    private var currentState: IndicatorState = .idle
    private var spectrumLevels = Array(repeating: CGFloat(0.08), count: 9)

    override init() {
        super.init()
        setupLayer()
    }

    override init(layer: Any) {
        super.init(layer: layer)
        if let layer = layer as? IndicatorLayer {
            currentState = layer.currentState
            spectrumLevels = layer.spectrumLevels
            recordingTransitionProgress = layer.recordingTransitionProgress
        }
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupLayer()
    }

    private func setupLayer() {
        opacity = 1
        contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        needsDisplayOnBoundsChange = true
        recordingTransitionProgress = 0
        transform = CATransform3DMakeScale(0.96, 0.96, 1)
        setNeedsDisplay()
    }

    override class func needsDisplay(forKey key: String) -> Bool {
        if key == "recordingTransitionProgress" {
            return true
        }
        return super.needsDisplay(forKey: key)
    }

    override func action(forKey event: String) -> CAAction? {
        if event == "recordingTransitionProgress" {
            let animation = CABasicAnimation(keyPath: event)
            animation.fromValue = presentation()?.value(forKey: event)
            animation.duration = CATransaction.animationDuration()
            animation.timingFunction = CATransaction.animationTimingFunction()
                ?? CAMediaTimingFunction(name: .easeInEaseOut)
            return animation
        }

        return super.action(forKey: event)
    }

    func updateState(_ state: IndicatorState) {
        currentState = state
        removeAllAnimations()
        spectrumLevels = Array(repeating: CGFloat(0.08), count: spectrumLevels.count)

        switch state {
        case .idle:
            applyIdleStyle()
        case .recording:
            applyRecordingStyle()
        case .transcribing:
            applyTranscribingStyle()
        case .downloadingModel:
            applyDownloadingStyle()
        case .error:
            applyErrorStyle()
        }
    }

    func updateSpectrum(_ bands: [Float]) {
        guard currentState == .recording else { return }

        for index in spectrumLevels.indices {
            let incoming = CGFloat(bands[safe: index] ?? 0.08)
            spectrumLevels[index] = max(0.06, min(1, (spectrumLevels[index] * 0.45) + (incoming * 0.55)))
        }

        setNeedsDisplay()
    }

    override func draw(in context: CGContext) {
        context.setAllowsAntialiasing(true)
        context.setShouldAntialias(true)

        let pillRect = bounds.insetBy(dx: 0.5, dy: 0.5)
        let cornerRadius = pillRect.height / 2
        let pillPath = CGPath(
            roundedRect: pillRect,
            cornerWidth: cornerRadius,
            cornerHeight: cornerRadius,
            transform: nil
        )

        context.addPath(pillPath)
        context.setFillColor(fillColor(for: currentState, progress: recordingTransitionProgress).cgColor)
        context.fillPath()

        context.addPath(pillPath)
        context.setStrokeColor(strokeColor(for: currentState, progress: recordingTransitionProgress).cgColor)
        context.setLineWidth(1)
        context.strokePath()

        switch currentState {
        case .recording:
            let idleLineOpacity = max(0, 1 - (recordingTransitionProgress * 1.15))
            if idleLineOpacity > 0.02 {
                drawCenterLine(
                    in: context,
                    bounds: pillRect,
                    color: NSColor.white.withAlphaComponent(0.32 * idleLineOpacity)
                )
            }
            drawSpectrum(in: context, bounds: pillRect, revealProgress: recordingTransitionProgress)
        case .idle:
            drawCenterLine(in: context, bounds: pillRect, color: NSColor.white.withAlphaComponent(0.32))
        case .transcribing:
            drawTranscribingGlyph(in: context, bounds: pillRect)
        case .downloadingModel:
            drawCenterLine(in: context, bounds: pillRect, color: NSColor.systemBlue.withAlphaComponent(0.85))
        case .error:
            drawCenterLine(in: context, bounds: pillRect, color: NSColor.systemRed.withAlphaComponent(0.95))
        }
    }

    private func applyIdleStyle() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        opacity = 1
        transform = CATransform3DMakeScale(0.96, 0.96, 1)
        recordingTransitionProgress = 0
        shadowOpacity = 0
        shadowRadius = 0
        CATransaction.commit()
        setNeedsDisplay()
    }

    private func applyRecordingStyle() {
        CATransaction.begin()
        CATransaction.setAnimationDuration(0.22)
        CATransaction.setAnimationTimingFunction(CAMediaTimingFunction(name: .easeInEaseOut))
        opacity = 1
        transform = CATransform3DIdentity
        recordingTransitionProgress = 1
        shadowColor = NSColor.systemRed.withAlphaComponent(0.35).cgColor
        shadowRadius = 12
        shadowOffset = .zero
        shadowOpacity = 0.28
        CATransaction.commit()
        setNeedsDisplay()
    }

    private func applyTranscribingStyle() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        opacity = 0.9
        transform = CATransform3DIdentity
        recordingTransitionProgress = 0
        shadowColor = NSColor.systemOrange.withAlphaComponent(0.2).cgColor
        shadowRadius = 8
        shadowOffset = .zero
        shadowOpacity = 0.18
        CATransaction.commit()

        let opacityAnim = CABasicAnimation(keyPath: "opacity")
        opacityAnim.fromValue = 0.68
        opacityAnim.toValue = 1.0
        opacityAnim.duration = 0.7
        opacityAnim.autoreverses = true
        opacityAnim.repeatCount = .infinity
        opacityAnim.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        add(opacityAnim, forKey: "pulse")
        setNeedsDisplay()
    }

    private func applyDownloadingStyle() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        opacity = 0.85
        transform = CATransform3DIdentity
        recordingTransitionProgress = 0
        shadowColor = NSColor.systemBlue.withAlphaComponent(0.15).cgColor
        shadowRadius = 8
        shadowOffset = .zero
        shadowOpacity = 0.15
        CATransaction.commit()

        let opacityAnim = CABasicAnimation(keyPath: "opacity")
        opacityAnim.fromValue = 0.55
        opacityAnim.toValue = 0.9
        opacityAnim.duration = 1.2
        opacityAnim.autoreverses = true
        opacityAnim.repeatCount = .infinity
        opacityAnim.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        add(opacityAnim, forKey: "downloadPulse")
        setNeedsDisplay()
    }

    private func applyErrorStyle() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        opacity = 0.95
        transform = CATransform3DIdentity
        recordingTransitionProgress = 0
        shadowOpacity = 0
        shadowRadius = 0
        CATransaction.commit()
        setNeedsDisplay()
    }

    private func fillColor(for state: IndicatorState, progress: CGFloat) -> NSColor {
        switch state {
        case .idle:
            return NSColor.black.withAlphaComponent(0.18)
        case .recording:
            return blend(
                from: NSColor.black.withAlphaComponent(0.18),
                to: NSColor.black.withAlphaComponent(0.82),
                progress: progress
            )
        case .transcribing:
            return NSColor.black.withAlphaComponent(0.74)
        case .downloadingModel:
            return NSColor.black.withAlphaComponent(0.68)
        case .error:
            return NSColor.black.withAlphaComponent(0.78)
        }
    }

    private func strokeColor(for state: IndicatorState, progress: CGFloat) -> NSColor {
        switch state {
        case .idle:
            return NSColor.white.withAlphaComponent(0.12)
        case .recording:
            return blend(
                from: NSColor.white.withAlphaComponent(0.12),
                to: NSColor.systemRed.withAlphaComponent(0.45),
                progress: progress
            )
        case .transcribing:
            return NSColor.systemOrange.withAlphaComponent(0.4)
        case .downloadingModel:
            return NSColor.systemBlue.withAlphaComponent(0.35)
        case .error:
            return NSColor.systemRed.withAlphaComponent(0.55)
        }
    }

    private func drawSpectrum(in context: CGContext, bounds: CGRect, revealProgress: CGFloat) {
        let reveal = max(0, min(1, revealProgress))
        guard reveal > 0.01 else { return }

        let contentRect = bounds.insetBy(dx: 11, dy: 4)
        let barCount = spectrumLevels.count
        let spacing: CGFloat = 4
        let totalSpacing = spacing * CGFloat(barCount - 1)
        let barWidth = max(3, (contentRect.width - totalSpacing) / CGFloat(barCount))
        let baselineY = contentRect.midY
        let maxBarHeight = contentRect.height

        for index in 0..<barCount {
            let level = max(0.08, min(1, spectrumLevels[index]))
            let targetHeight = maxBarHeight * (0.2 + (level * 0.8))
            let height = max(2, 2 + ((targetHeight - 2) * reveal))
            let x = contentRect.minX + CGFloat(index) * (barWidth + spacing)
            let barRect = CGRect(
                x: x,
                y: baselineY - (height / 2),
                width: barWidth,
                height: height
            )
            let progress = CGFloat(index) / CGFloat(max(barCount - 1, 1))
            let color = NSColor(
                calibratedRed: 1,
                green: 0.34 + (0.24 * progress),
                blue: 0.28,
                alpha: 0.95 * reveal
            )

            context.addPath(CGPath(
                roundedRect: barRect,
                cornerWidth: barWidth / 2,
                cornerHeight: barWidth / 2,
                transform: nil
            ))
            context.setFillColor(color.cgColor)
            context.fillPath()
        }
    }

    private func blend(from: NSColor, to: NSColor, progress: CGFloat) -> NSColor {
        let start = from.usingColorSpace(.deviceRGB) ?? from
        let end = to.usingColorSpace(.deviceRGB) ?? to
        let clamped = max(0, min(1, progress))

        return NSColor(
            calibratedRed: start.redComponent + ((end.redComponent - start.redComponent) * clamped),
            green: start.greenComponent + ((end.greenComponent - start.greenComponent) * clamped),
            blue: start.blueComponent + ((end.blueComponent - start.blueComponent) * clamped),
            alpha: start.alphaComponent + ((end.alphaComponent - start.alphaComponent) * clamped)
        )
    }

    private func drawCenterLine(in context: CGContext, bounds: CGRect, color: NSColor) {
        let lineWidth = bounds.width * 0.36
        let rect = CGRect(
            x: bounds.midX - (lineWidth / 2),
            y: bounds.midY - 1,
            width: lineWidth,
            height: 2
        )

        context.addPath(CGPath(roundedRect: rect, cornerWidth: 1, cornerHeight: 1, transform: nil))
        context.setFillColor(color.cgColor)
        context.fillPath()
    }

    private func drawTranscribingGlyph(in context: CGContext, bounds: CGRect) {
        let contentRect = bounds.insetBy(dx: 25, dy: 7)
        let widths: [CGFloat] = [10, 16, 10]
        let spacing: CGFloat = 4
        var x = contentRect.minX

        for (index, width) in widths.enumerated() {
            let height: CGFloat = index == 1 ? 4 : 2.5
            let rect = CGRect(
                x: x,
                y: contentRect.midY - (height / 2),
                width: width,
                height: height
            )
            context.addPath(CGPath(roundedRect: rect, cornerWidth: height / 2, cornerHeight: height / 2, transform: nil))
            context.setFillColor(NSColor.systemOrange.withAlphaComponent(index == 1 ? 0.92 : 0.65).cgColor)
            context.fillPath()
            x += width + spacing
        }
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
