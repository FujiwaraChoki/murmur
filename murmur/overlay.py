"""Overlay window module for the recording indicator bar."""

from __future__ import annotations

import math
from enum import Enum

import AppKit
import objc
import Quartz
from Foundation import NSTimer


class IndicatorState(Enum):
    """States for the indicator bar."""

    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"

class ClickableWindow(AppKit.NSWindow):
    """Custom NSWindow subclass that accepts mouse events when borderless."""

    def canBecomeKeyWindow(self):
        """Allow borderless window to become key and receive mouse events."""
        return True


class IndicatorView(AppKit.NSView):
    """Custom view for the animated indicator bar."""

    _baseline_level = 0.06
    _waveform_count = 11

    def initWithFrame_(self, frame):
        self = objc.super(IndicatorView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._state = IndicatorState.IDLE
        self._prev_state = None
        self._transition = 1.0
        self._animation_phase = 0.0
        self._animation_timer = None
        self._animation_speed = 0.0
        self._on_click = None
        self._waveform_levels = [self._baseline_level] * self._waveform_count

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

    def _draw_state(self, context, bounds, state):
        """Draw a specific state."""
        if state == IndicatorState.IDLE:
            self._draw_shell(context, bounds, fill=(0.0, 0.0, 0.0, 0.54), stroke=(1, 1, 1, 0.1))
            self._draw_idle_line(context, bounds)
        elif state == IndicatorState.RECORDING:
            self._draw_recording_waveform(context, bounds)
        elif state == IndicatorState.TRANSCRIBING:
            self._draw_transcribing_pulse(context, bounds)

    def drawRect_(self, rect):
        """Draw the indicator bar with animation."""
        context = AppKit.NSGraphicsContext.currentContext().CGContext()
        bounds = self.bounds()
        Quartz.CGContextSetShouldAntialias(context, True)

        if self._transition < 1.0 and self._prev_state is not None:
            t = self._ease_out(self._transition)
            Quartz.CGContextSaveGState(context)
            Quartz.CGContextSetAlpha(context, 1.0 - t)
            self._draw_state(context, bounds, self._prev_state)
            Quartz.CGContextRestoreGState(context)

            Quartz.CGContextSaveGState(context)
            Quartz.CGContextSetAlpha(context, t)
            self._draw_state(context, bounds, self._state)
            Quartz.CGContextRestoreGState(context)
        else:
            self._draw_state(context, bounds, self._state)

    def _ease_out(self, t):
        """Ease-out cubic for smooth deceleration."""
        return 1.0 - (1.0 - t) ** 3

    def _draw_shell(self, context, bounds, fill, stroke):
        """Draw the base capsule shared across states."""
        Quartz.CGContextSetRGBFillColor(context, *fill)
        self._create_rounded_rect_path(context, bounds)
        Quartz.CGContextFillPath(context)

        Quartz.CGContextSetRGBStrokeColor(context, *stroke)
        Quartz.CGContextSetLineWidth(context, 1)
        inset_bounds = Quartz.CGRectInset(bounds, 0.5, 0.5)
        self._create_rounded_rect_path(context, inset_bounds)
        Quartz.CGContextStrokePath(context)

    def _draw_idle_line(self, context, bounds):
        """Draw the minimal idle baseline."""
        inset = 18
        line_rect = Quartz.CGRectMake(
            inset,
            bounds.size.height / 2 - 1,
            bounds.size.width - (inset * 2),
            2,
        )
        Quartz.CGContextSetRGBFillColor(context, 1.0, 1.0, 1.0, 0.3)
        Quartz.CGContextFillRect(context, line_rect)

    def _draw_recording_waveform(self, context, bounds):
        """Draw a center-weighted waveform as vertical bars."""
        self._draw_shell(
            context,
            bounds,
            fill=(0.0, 0.0, 0.0, 0.92),
            stroke=(1.0, 1.0, 1.0, 0.4),
        )

        Quartz.CGContextSaveGState(context)
        self._create_rounded_rect_path(context, bounds)
        Quartz.CGContextClip(context)

        inset_x = 10
        inset_y = 8
        area_x = bounds.origin.x + inset_x
        area_width = bounds.size.width - (inset_x * 2)
        center_y = bounds.origin.y + bounds.size.height / 2
        max_half_height = (bounds.size.height / 2) - inset_y

        count = len(self._waveform_levels)
        bar_width = 2.5
        total_bars_width = count * bar_width
        gap = max(1.5, (area_width - total_bars_width) / max(count - 1, 1))

        Quartz.CGContextSetLineCap(context, Quartz.kCGLineCapRound)
        Quartz.CGContextSetLineWidth(context, bar_width)

        for i, level in enumerate(self._waveform_levels):
            amplified = min(1.0, level ** 0.3)
            t = (2.0 * i / max(count - 1, 1)) - 1.0
            envelope = 0.55 + 0.45 * math.cos(t * math.pi / 2)
            half_h = max(1.0, amplified * envelope * max_half_height)
            x = area_x + i * (bar_width + gap) + bar_width / 2

            Quartz.CGContextSetRGBStrokeColor(context, 1.0, 1.0, 1.0, 0.9)
            Quartz.CGContextBeginPath(context)
            Quartz.CGContextMoveToPoint(context, x, center_y - half_h)
            Quartz.CGContextAddLineToPoint(context, x, center_y + half_h)
            Quartz.CGContextStrokePath(context)

        Quartz.CGContextRestoreGState(context)

    def _draw_transcribing_pulse(self, context, bounds):
        """Draw three pulsing dots for the transcribing state."""
        self._draw_shell(
            context,
            bounds,
            fill=(0.0, 0.0, 0.0, 0.88),
            stroke=(1.0, 1.0, 1.0, 0.15),
        )

        center_y = bounds.origin.y + bounds.size.height / 2
        center_x = bounds.origin.x + bounds.size.width / 2
        dot_radius = 2.5
        dot_spacing = 10.0
        num_dots = 3

        for i in range(num_dots):
            offset = (i - (num_dots - 1) / 2) * dot_spacing
            x = center_x + offset
            phase = (self._animation_phase * 2 * math.pi) - (i * 0.8)
            scale = (math.sin(phase) + 1) / 2
            r = dot_radius * (0.5 + scale * 0.5)
            alpha = 0.3 + (scale * 0.7)

            Quartz.CGContextSetRGBFillColor(context, 1.0, 1.0, 1.0, alpha)
            dot_rect = Quartz.CGRectMake(x - r, center_y - r, r * 2, r * 2)
            Quartz.CGContextFillEllipseInRect(context, dot_rect)

    def setWaveform_(self, levels):
        """Update the waveform levels while recording."""
        if self._state != IndicatorState.RECORDING:
            return

        sanitized = []
        for value in list(levels)[: self._waveform_count]:
            sanitized.append(max(self._baseline_level, min(float(value), 1.0)))

        if not sanitized:
            sanitized = [self._baseline_level] * self._waveform_count

        if len(sanitized) < self._waveform_count:
            sanitized.extend([sanitized[-1]] * (self._waveform_count - len(sanitized)))

        self._waveform_levels = sanitized
        self.setNeedsDisplay_(True)

    def setState_(self, state: IndicatorState):
        """Set the indicator state with animated transition."""
        if state == self._state:
            return
        self._prev_state = self._state
        self._state = state
        self._transition = 0.0
        self._waveform_levels = [self._baseline_level] * self._waveform_count
        if state == IndicatorState.RECORDING:
            self._start_animation(speed=0.022)
        elif state == IndicatorState.TRANSCRIBING:
            self._start_animation(speed=0.015)
        else:
            self._start_animation(speed=0.022)
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

        if self._transition < 1.0:
            self._transition = min(1.0, self._transition + 0.04)

        if self._state == IndicatorState.RECORDING:
            self._waveform_levels = [
                max(self._baseline_level, level * 0.96) for level in self._waveform_levels
            ]

        if self._transition >= 1.0 and self._state == IndicatorState.IDLE:
            self._prev_state = None
            self._stop_animation()
            return

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

    def __init__(self, width: int = 80, height: int = 28, on_click: callable = None):
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

    def update_waveform(self, levels: list[float]):
        """Push waveform levels into the indicator on the main thread."""
        if self._view is not None:
            self._view.performSelectorOnMainThread_withObject_waitUntilDone_(
                "setWaveform:", levels, False
            )

    @property
    def state(self) -> IndicatorState:
        """Get the current indicator state."""
        return self._state
