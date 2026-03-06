#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
XCODEPROJ_PATH="$PROJECT_DIR/macos/Murmur/Murmur.xcodeproj"
SCHEME_NAME="Murmur"
CONFIGURATION="Release"
BUILD_ROOT="$PROJECT_DIR/build/macos-release"
DERIVED_DATA_PATH="$BUILD_ROOT/DerivedData"
STAGING_DIR="$BUILD_ROOT/dmg-root"
DIST_DIR="${OUTPUT_DIR:-$PROJECT_DIR/dist}"
APP_NAME="Murmur"
RELEASE_SUFFIX="${MURMUR_RELEASE_SUFFIX:-}"

log() {
  printf '[build-macos-dmg] %s\n' "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

require_command xcodebuild
require_command hdiutil
require_command ditto
require_command /usr/libexec/PlistBuddy

if [[ ! -d "$XCODEPROJ_PATH" ]]; then
  printf 'Xcode project not found at %s\n' "$XCODEPROJ_PATH" >&2
  exit 1
fi

mkdir -p "$DIST_DIR"
rm -rf "$BUILD_ROOT"

log "Building $APP_NAME.app from $XCODEPROJ_PATH"
xcodebuild \
  -project "$XCODEPROJ_PATH" \
  -scheme "$SCHEME_NAME" \
  -configuration "$CONFIGURATION" \
  -derivedDataPath "$DERIVED_DATA_PATH" \
  -destination "platform=macOS" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  build

APP_PATH="$DERIVED_DATA_PATH/Build/Products/$CONFIGURATION/$APP_NAME.app"

if [[ ! -d "$APP_PATH" ]]; then
  printf 'Built app bundle not found at %s\n' "$APP_PATH" >&2
  exit 1
fi

INFO_PLIST_PATH="$APP_PATH/Contents/Info.plist"
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$INFO_PLIST_PATH")"
BUILD_NUMBER="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$INFO_PLIST_PATH")"

DMG_BASENAME="${APP_NAME}-${VERSION}"
if [[ -n "$RELEASE_SUFFIX" ]]; then
  DMG_BASENAME="${DMG_BASENAME}-${RELEASE_SUFFIX}"
fi

DMG_PATH="$DIST_DIR/${DMG_BASENAME}.dmg"

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
ditto "$APP_PATH" "$STAGING_DIR/$APP_NAME.app"
ln -s /Applications "$STAGING_DIR/Applications"
rm -f "$DMG_PATH"

log "Creating DMG at $DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH" \
  >/dev/null

log "Created $DMG_PATH"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    printf 'app_path=%s\n' "$APP_PATH"
    printf 'dmg_path=%s\n' "$DMG_PATH"
    printf 'dmg_name=%s\n' "$(basename "$DMG_PATH")"
    printf 'version=%s\n' "$VERSION"
    printf 'build_number=%s\n' "$BUILD_NUMBER"
  } >>"$GITHUB_OUTPUT"
fi
