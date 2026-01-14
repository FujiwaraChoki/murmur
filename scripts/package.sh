#!/bin/bash
#
# Package Murmur as a macOS .app bundle and .dmg installer
#
# Usage: ./scripts/package.sh [--skip-dmg]
#
# Requirements:
#   - Python 3.10+
#   - PyInstaller (pip install pyinstaller)
#   - create-dmg (brew install create-dmg) - optional, for DMG creation
#
set -euo pipefail

# Configuration
APP_NAME="Murmur"
BUNDLE_ID="com.murmur.app"
VERSION=$(grep -m1 'version = ' pyproject.toml | cut -d'"' -f2)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
ASSETS_DIR="$PROJECT_DIR/assets"
ICON_PATH="$BUILD_DIR/Murmur.icns"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
SKIP_DMG=false
for arg in "$@"; do
    case $arg in
        --skip-dmg)
            SKIP_DMG=true
            ;;
    esac
done

# Check we're in the project directory
cd "$PROJECT_DIR"

if [[ ! -f "pyproject.toml" ]]; then
    log_error "Must run from project root (where pyproject.toml is located)"
    exit 1
fi

log_info "Packaging $APP_NAME v$VERSION"

# Check for required tools
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed."
        echo "  Install with: $2"
        exit 1
    fi
}

check_command python3 "brew install python"
check_command pip3 "comes with python3"

# Check/install PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    log_warn "PyInstaller not found, installing..."
    pip3 install pyinstaller --quiet
fi

# Create build directory
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Generate .icns icon from SVG
generate_icon() {
    log_info "Generating app icon..."

    local svg_path="$ASSETS_DIR/logo.svg"
    local iconset_dir="$BUILD_DIR/Murmur.iconset"

    if [[ ! -f "$svg_path" ]]; then
        log_warn "No logo.svg found, using default icon"
        return 1
    fi

    # Check for rsvg-convert or use sips as fallback
    if command -v rsvg-convert &> /dev/null; then
        mkdir -p "$iconset_dir"

        # Generate all required icon sizes
        local sizes=(16 32 64 128 256 512 1024)
        for size in "${sizes[@]}"; do
            rsvg-convert -w "$size" -h "$size" "$svg_path" -o "$iconset_dir/icon_${size}x${size}.png" 2>/dev/null || true
        done

        # Create @2x versions
        cp "$iconset_dir/icon_32x32.png" "$iconset_dir/icon_16x16@2x.png" 2>/dev/null || true
        cp "$iconset_dir/icon_64x64.png" "$iconset_dir/icon_32x32@2x.png" 2>/dev/null || true
        cp "$iconset_dir/icon_256x256.png" "$iconset_dir/icon_128x128@2x.png" 2>/dev/null || true
        cp "$iconset_dir/icon_512x512.png" "$iconset_dir/icon_256x256@2x.png" 2>/dev/null || true
        cp "$iconset_dir/icon_1024x1024.png" "$iconset_dir/icon_512x512@2x.png" 2>/dev/null || true

        # Remove non-standard sizes
        rm -f "$iconset_dir/icon_64x64.png" "$iconset_dir/icon_1024x1024.png"

        # Convert iconset to icns
        iconutil -c icns "$iconset_dir" -o "$ICON_PATH"
        rm -rf "$iconset_dir"

        log_info "Icon generated at $ICON_PATH"
        return 0
    else
        log_warn "rsvg-convert not found (install with: brew install librsvg)"
        log_warn "Skipping icon generation"
        return 1
    fi
}

# Try to generate icon (non-fatal if it fails)
generate_icon || true

# Create PyInstaller spec file
log_info "Creating PyInstaller spec..."

ICON_OPTION=""
if [[ -f "$ICON_PATH" ]]; then
    ICON_OPTION="icon='$ICON_PATH',"
fi

cat > "$BUILD_DIR/murmur.spec" << EOF
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path('$PROJECT_DIR')

a = Analysis(
    ['$PROJECT_DIR/murmur/main.py'],
    pathex=['$PROJECT_DIR'],
    binaries=[],
    datas=[
        ('$ASSETS_DIR', 'assets'),
    ],
    hiddenimports=[
        'murmur',
        'murmur.app',
        'murmur.audio',
        'murmur.hotkey',
        'murmur.overlay',
        'murmur.paste',
        'murmur.settings',
        'murmur.transcribe',
        'murmur.updater',
        'AppKit',
        'Foundation',
        'Quartz',
        'objc',
        'sounddevice',
        'soundfile',
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._darwin',
        'pyperclip',
        'parakeet_mlx',
        'mlx',
        'mlx.core',
        'mlx.nn',
        'numpy',
        'huggingface_hub',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='murmur',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='murmur',
)

app = BUNDLE(
    coll,
    name='$APP_NAME.app',
    $ICON_OPTION
    bundle_identifier='$BUNDLE_ID',
    info_plist={
        'CFBundleName': '$APP_NAME',
        'CFBundleDisplayName': '$APP_NAME',
        'CFBundleVersion': '$VERSION',
        'CFBundleShortVersionString': '$VERSION',
        'CFBundleIdentifier': '$BUNDLE_ID',
        'NSMicrophoneUsageDescription': 'Murmur needs microphone access for voice dictation.',
        'NSAppleEventsUsageDescription': 'Murmur needs accessibility access to paste transcribed text.',
        'LSMinimumSystemVersion': '12.0',
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
    },
)
EOF

# Build the app
log_info "Building $APP_NAME.app with PyInstaller..."
python3 -m PyInstaller \
    --clean \
    --noconfirm \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR/pyinstaller" \
    "$BUILD_DIR/murmur.spec"

APP_PATH="$DIST_DIR/$APP_NAME.app"

if [[ ! -d "$APP_PATH" ]]; then
    log_error "Failed to create $APP_NAME.app"
    exit 1
fi

log_info "Created $APP_PATH"

# Create DMG
if [[ "$SKIP_DMG" == true ]]; then
    log_info "Skipping DMG creation (--skip-dmg)"
else
    DMG_PATH="$DIST_DIR/${APP_NAME}-${VERSION}.dmg"

    # Remove old DMG if exists
    rm -f "$DMG_PATH"

    if command -v create-dmg &> /dev/null; then
        log_info "Creating DMG with create-dmg..."

        create-dmg \
            --volname "$APP_NAME" \
            --volicon "$ICON_PATH" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "$APP_NAME.app" 150 185 \
            --hide-extension "$APP_NAME.app" \
            --app-drop-link 450 185 \
            --no-internet-enable \
            "$DMG_PATH" \
            "$APP_PATH" \
            2>/dev/null || {
                # Fallback if create-dmg fails (e.g., no icon)
                log_warn "create-dmg failed, using hdiutil fallback..."
                hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
            }
    else
        log_warn "create-dmg not found, using hdiutil..."
        log_warn "  For a nicer DMG, install: brew install create-dmg"

        hdiutil create \
            -volname "$APP_NAME" \
            -srcfolder "$APP_PATH" \
            -ov \
            -format UDZO \
            "$DMG_PATH"
    fi

    if [[ -f "$DMG_PATH" ]]; then
        log_info "Created $DMG_PATH"

        # Show DMG size
        DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
        log_info "DMG size: $DMG_SIZE"
    else
        log_error "Failed to create DMG"
        exit 1
    fi
fi

# Summary
echo ""
log_info "Build complete!"
echo "  App: $APP_PATH"
if [[ "$SKIP_DMG" != true ]] && [[ -f "$DMG_PATH" ]]; then
    echo "  DMG: $DMG_PATH"
fi
echo ""
echo "To test the app:"
echo "  open \"$APP_PATH\""
echo ""
echo "Note: On first run, you may need to grant permissions:"
echo "  - Microphone access (System Settings > Privacy & Security > Microphone)"
echo "  - Accessibility (System Settings > Privacy & Security > Accessibility)"
echo "  - Input Monitoring (System Settings > Privacy & Security > Input Monitoring)"
