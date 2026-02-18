"""Overlay window module for the recording indicator bar."""

from __future__ import annotations

import logging
import math
from enum import Enum

import AppKit
import objc
import Quartz
from Foundation import NSTimer

logger = logging.getLogger("murmur.overlay")


class IndicatorState(Enum):
    """States for the indicator bar."""

    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


# Colors for different states (r, g, b)
COLORS = {
    IndicatorState.IDLE: (0.75, 0.75, 0.78),          # Soft silver
    IndicatorState.RECORDING: (1.0, 0.28, 0.35),      # Vibrant coral-red
    IndicatorState.TRANSCRIBING: (0.35, 0.55, 1.0),   # Clean blue
}


class ClickableWindow(AppKit.NSWindow):
    """Custom NSWindow subclass that accepts mouse events when borderless."""

    def canBecomeKeyWindow(self):
        """Allow borderless window to become key and receive mouse events."""
        return True


class IndicatorView(AppKit.NSView):
    """Custom view for the animated indicator bar."""

    def initWithFrame_(self, frame):
        self = objc.super(IndicatorView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._state = IndicatorState.IDLE
        self._animation_phase = 0.0
        self._animation_timer = None
        self._on_click = None

        return self

    def setOnClick_(self, callback):
        """Set the click callback."""
        self._on_click = callback

    def acceptsFirstMouse_(self, event):
        """Accept clicks even when window is not key window."""
        return True

    def hitTest_(self, point):
        """Override hit testing to capture clicks on transparent areas."""
        if AppKit.NSPointInRect(point, self.frame()):
            return self
        return None

    def mouseDown_(self, event):
        """Handle mouse down event."""
        if self._on_click:
            self._on_click()

    def _create_rounded_rect_path(self, context, bounds):
        """Create a rounded rectangle path."""
        radius = bounds.size.height / 2
        Quartz.CGContextBeginPath(context)
        Quartz.CGContextMoveToPoint(context, radius, 0)
        Quartz.CGContextAddLineToPoint(context, bounds.size.width - radius, 0)
        Quartz.CGContextAddArc(
            context,
            bounds.size.width - radius,
            radius,
            radius,
            -math.pi / 2,
            math.pi / 2,
            0,
        )
        Quartz.CGContextAddLineToPoint(context, radius, bounds.size.height)
        Quartz.CGContextAddArc(context, radius, radius, radius, math.pi / 2, -math.pi / 2, 0)
        Quartz.CGContextClosePath(context)

    def drawRect_(self, rect):
        """Draw the indicator bar with animation."""
        context = AppKit.NSGraphicsContext.currentContext().CGContext()
        bounds = self.bounds()
        r, g, b = COLORS[self._state]

        if self._state == IndicatorState.IDLE:
            # Subtle pill with slight translucency
            Quartz.CGContextSetRGBFillColor(context, r, g, b, 0.35)
            self._create_rounded_rect_path(context, bounds)
            Quartz.CGContextFillPath(context)

        elif self._state == IndicatorState.RECORDING:
            self._draw_recording_glow(context, bounds, r, g, b)

        elif self._state == IndicatorState.TRANSCRIBING:
            self._draw_transcribing_pulse(context, bounds, r, g, b)

    def _draw_recording_glow(self, context, bounds, r, g, b):
        """Draw a smooth glowing/breathing animation for recording."""
        # Smooth sine wave for breathing effect
        breath = (math.sin(self._animation_phase * math.pi * 2) + 1) / 2  # 0 to 1

        # Soft outer glow
        glow_alpha = 0.12 + 0.12 * breath
        glow_expand = 2 + 1.5 * breath

        Quartz.CGContextSaveGState(context)

        glow_bounds = Quartz.CGRectMake(
            -glow_expand,
            -glow_expand / 2,
            bounds.size.width + glow_expand * 2,
            bounds.size.height + glow_expand,
        )
        Quartz.CGContextSetRGBFillColor(context, r, g, b, glow_alpha)
        glow_radius = (bounds.size.height + glow_expand) / 2
        Quartz.CGContextBeginPath(context)
        Quartz.CGContextMoveToPoint(context, glow_radius, -glow_expand / 2)
        Quartz.CGContextAddLineToPoint(
            context, glow_bounds.size.width - glow_radius, -glow_expand / 2
        )
        Quartz.CGContextAddArc(
            context,
            glow_bounds.size.width - glow_radius - glow_expand,
            bounds.size.height / 2,
            glow_radius,
            -math.pi / 2,
            math.pi / 2,
            0,
        )
        Quartz.CGContextAddLineToPoint(context, glow_radius, bounds.size.height + glow_expand / 2)
        Quartz.CGContextAddArc(
            context,
            glow_radius,
            bounds.size.height / 2,
            glow_radius,
            math.pi / 2,
            -math.pi / 2,
            0,
        )
        Quartz.CGContextClosePath(context)
        Quartz.CGContextFillPath(context)

        Quartz.CGContextRestoreGState(context)

        # Main bar with breathing opacity
        main_alpha = 0.7 + 0.25 * breath
        Quartz.CGContextSetRGBFillColor(context, r, g, b, main_alpha)
        self._create_rounded_rect_path(context, bounds)
        Quartz.CGContextFillPath(context)

    def _draw_transcribing_pulse(self, context, bounds, r, g, b):
        """Draw a gentle pulsing animation for transcribing."""
        # Smooth pulse
        pulse = (math.sin(self._animation_phase * math.pi * 2) + 1) / 2
        alpha = 0.55 + 0.35 * pulse

        Quartz.CGContextSetRGBFillColor(context, r, g, b, alpha)
        self._create_rounded_rect_path(context, bounds)
        Quartz.CGContextFillPath(context)

    def setState_(self, state: IndicatorState):
        """Set the indicator state and update animation."""
        self._state = state
        if state == IndicatorState.RECORDING:
            self._start_animation(speed=0.02)
        elif state == IndicatorState.TRANSCRIBING:
            self._start_animation(speed=0.015)
        else:
            self._stop_animation()
        self.setNeedsDisplay_(True)

    def _start_animation(self, speed=0.02):
        """Start the animation."""
        if self._animation_timer is not None:
            self._animation_timer.invalidate()

        self._animation_phase = 0.0
        self._animation_speed = speed

        self._animation_timer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0 / 60.0,
                self,
                "animationTick:",
                None,
                True,  # 60fps
            )
        )

    def animationTick_(self, timer):
        """Animation timer callback."""
        self._animation_phase += self._animation_speed
        if self._animation_phase > 1.0:
            self._animation_phase -= 1.0
        self.setNeedsDisplay_(True)

    def _stop_animation(self):
        """Stop the animation."""
        if self._animation_timer is not None:
            self._animation_timer.invalidate()
            self._animation_timer = None
        self._animation_phase = 0.0
        self.setNeedsDisplay_(True)


class IndicatorWindow:
    """Floating indicator window at the bottom of the screen."""

    def __init__(self, width: int = 300, height: int = 20, on_click: callable = None):
        """Initialize the indicator window.

        Args:
            width: Width of the indicator bar in pixels.
            height: Height of the indicator bar in pixels.
            on_click: Callback when the indicator is clicked.
        """
        self.width = width
        self.height = height
        self._window = None
        self._view = None
        self._state = IndicatorState.IDLE
        self._on_click = on_click

    def show(self):
        """Show the indicator window."""
        if self._window is not None:
            return

        # Get the primary screen (the one with the menu bar)
        # screens()[0] is always the primary display
        screens = AppKit.NSScreen.screens()
        screen = screens[0] if screens else AppKit.NSScreen.mainScreen()
        screen_frame = screen.frame()

        # Calculate position (centered at bottom with padding)
        # Account for screen origin in multi-monitor setups
        padding_bottom = 20
        x = screen_frame.origin.x + (screen_frame.size.width - self.width) / 2
        y = screen_frame.origin.y + padding_bottom

        # Create window frame
        window_rect = AppKit.NSMakeRect(x, y, self.width, self.height)

        # Create a borderless, floating window
        self._window = ClickableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )

        # Configure window properties
        self._window.setLevel_(AppKit.NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self._window.setIgnoresMouseEvents_(False)  # Allow clicks
        self._window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
        )

        # Create and set the indicator view
        view_rect = AppKit.NSMakeRect(0, 0, self.width, self.height)
        self._view = IndicatorView.alloc().initWithFrame_(view_rect)
        if self._on_click:
            self._view.setOnClick_(self._on_click)
        self._window.setContentView_(self._view)

        # Show the window
        self._window.orderFront_(None)

    def hide(self):
        """Hide the indicator window."""
        if self._window is not None:
            self._window.orderOut_(None)
            self._window = None
            self._view = None

    def set_state(self, state: IndicatorState):
        """Set the indicator state.

        Args:
            state: The new indicator state.
        """
        self._state = state
        if self._view is not None:
            # Must update UI on main thread
            self._view.performSelectorOnMainThread_withObject_waitUntilDone_(
                "setState:", state, False
            )

    @property
    def state(self) -> IndicatorState:
        """Get the current indicator state."""
        return self._state
