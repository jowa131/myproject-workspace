#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/scorer-cli-test"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/classes"

JDK_HOME="${JDK_HOME:-}"
if [[ -z "$JDK_HOME" ]]; then
  for candidate in "/c/Program Files/Android/Android Studio/jbr" "$HOME/.antigravity/extensions/redhat.java-1.54.0-win32-x64/jre/21.0.10-win32-x86_64"; do
    if [[ -x "$candidate/bin/javac.exe" ]]; then
      JDK_HOME="$candidate"
      break
    fi
  done
fi

if [[ -z "$JDK_HOME" ]]; then
  echo "No JDK with javac found. Set JDK_HOME." >&2
  exit 2
fi

mapfile -t MAIN_SOURCES < <(
  {
    find "$ROOT_DIR/app/src/main/java/com/ibscare/android/session" -name '*.java' 2>/dev/null
    find "$ROOT_DIR/app/src/main/java/com/ibscare/android/ui" -name 'UiCopy.java' 2>/dev/null
  } | sort
)
mapfile -t TEST_SOURCES < <(find "$ROOT_DIR/app/src/test/java" -name '*.java' | sort)

"$JDK_HOME/bin/javac.exe" -encoding UTF-8 -d "$BUILD_DIR/classes" "${MAIN_SOURCES[@]}" "${TEST_SOURCES[@]}"
"$JDK_HOME/bin/java.exe" -cp "$BUILD_DIR/classes" com.ibscare.android.session.BowelSessionScorerCliTest
