import AppKit
import QuartzCore

enum IndicatorState {
    case idle
    case recording
    case transcribing
    case downloadingModel
    case error
}

final class IndicatorWindow: NSWindow {
    private static let indicatorWidth: CGFloat = 88
    private static let indicatorHeight: CGFloat = 24
    private static let topMargin: CGFloat = 10

    private let indicatorLayer = IndicatorLayer()

    init() {
        guard let screen = NSScreen.main else {
            super.init(
                contentRect: .zero,
                styleMask: .borderless,
                backing: .buffered,
                defer: false
            )
            return
        }

        let screenFrame = screen.visibleFrame
        let x = screenFrame.midX - Self.indicatorWidth / 2
        let y = screenFrame.maxY - Self.topMargin - Self.indicatorHeight

        let frame = NSRect(
            x: x, y: y,
            width: Self.indicatorWidth, height: Self.indicatorHeight
        )

        super.init(
            contentRect: frame,
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )

        level = .floating
        isOpaque = false
        backgroundColor = .clear
        ignoresMouseEvents = true
        collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        hasShadow = false

        let contentView = NSView(frame: NSRect(origin: .zero, size: frame.size))
        contentView.wantsLayer = true
        contentView.layer?.cornerRadius = Self.indicatorHeight / 2
        contentView.layer?.masksToBounds = false

        indicatorLayer.frame = CGRect(origin: .zero, size: frame.size)
        indicatorLayer.cornerRadius = Self.indicatorHeight / 2
        contentView.layer?.addSublayer(indicatorLayer)

        self.contentView = contentView

        updateState(.idle)
    }

    func show() {
        orderFrontRegardless()
    }

    func updateState(_ state: IndicatorState) {
        indicatorLayer.updateState(state)
    }

    func updateSpectrum(_ bands: [Float]) {
        indicatorLayer.updateSpectrum(bands)
    }
}
