#!/usr/bin/env bash
# Start an Android emulator and run the demo app on it (macOS, Linux).
#
# Usage: tools/run_emulator.sh [--avd NAME] [--fresh]
#   --avd NAME  emulator to start (default: the first one `emulator -list-avds` prints)
#   --fresh     clear the app's data first, so it starts with no model installed
#
# Finds the Android SDK (ANDROID_HOME, ANDROID_SDK_ROOT, or the Android Studio default) and Flutter (on PATH),
# waits for the emulator to boot, then runs the app from app/ with --no-enable-impeller (Flutter's Impeller
# renderer can hang on emulators without a graphics card).
set -euo pipefail
APP_ID="io.github.kurtvalcorza.trapcounter"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AVD=""; FRESH=0
while [ $# -gt 0 ]; do
  case "$1" in
    --avd) AVD="$2"; shift 2 ;;
    --fresh) FRESH=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

SDK=""
for c in "${ANDROID_HOME:-}" "${ANDROID_SDK_ROOT:-}" "$HOME/Library/Android/sdk" "$HOME/Android/Sdk"; do
  if [ -n "$c" ] && [ -x "$c/platform-tools/adb" ]; then SDK="$c"; break; fi
done
[ -n "$SDK" ] || { echo "Android SDK not found. Set ANDROID_HOME, or install it with Android Studio (see docs/setup.md)." >&2; exit 1; }
ADB="$SDK/platform-tools/adb"; EMULATOR="$SDK/emulator/emulator"
[ -x "$EMULATOR" ] || { echo "The Android Emulator is not installed. Add it in Android Studio's SDK Manager." >&2; exit 1; }
command -v flutter >/dev/null || { echo "Flutter not found on PATH (see docs/setup.md)." >&2; exit 1; }

if [ -z "$AVD" ]; then
  AVD="$("$EMULATOR" -list-avds | head -n 1)"
  [ -n "$AVD" ] || { echo "No emulator found. Create one in Android Studio's Device Manager." >&2; exit 1; }
fi
if "$ADB" devices | grep -Eq '^emulator-[0-9]+[[:space:]]+device'; then
  echo "An emulator is already running; using it."
else
  echo "Starting emulator $AVD ..."
  "$EMULATOR" -avd "$AVD" >/dev/null 2>&1 &
  "$ADB" wait-for-device
  for _ in $(seq 1 100); do
    [ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ] && break
    sleep 3
  done
  [ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ] || { echo "The emulator did not finish booting within 5 minutes." >&2; exit 1; }
  echo "Emulator booted."
fi
DEVICE="$("$ADB" devices | grep -Eo '^emulator-[0-9]+' | head -n 1)"

if [ "$FRESH" = 1 ]; then
  echo "Clearing the app's data (no model installed) ..."
  "$ADB" -s "$DEVICE" shell pm clear "$APP_ID" >/dev/null 2>&1 || true
fi

cd "$ROOT/app"
exec flutter run --no-enable-impeller -d "$DEVICE"
