#!/usr/bin/env bash
set -e

# Build official .deb Debian Package for Writing Assistant
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="/tmp/writing-assistant-deb-pkg"
DIST_DIR="${PROJECT_ROOT}/dist"
PKG_VERSION="0.1.0"
PKG_NAME="writing-assistant_${PKG_VERSION}_all.deb"

echo "=== Building Writing Assistant Debian Package (${PKG_NAME}) ==="

# Clean previous build artifacts
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${BUILD_DIR}/usr/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com"
mkdir -p "${BUILD_DIR}/usr/lib/python3/dist-packages/writing_companion"
mkdir -p "${DIST_DIR}"

# 1. Install Control Files
cp "${PROJECT_ROOT}/packaging/debian/control" "${BUILD_DIR}/DEBIAN/control"
cp "${PROJECT_ROOT}/packaging/debian/postinst" "${BUILD_DIR}/DEBIAN/postinst"
cp "${PROJECT_ROOT}/packaging/debian/prerm" "${BUILD_DIR}/DEBIAN/prerm"
chmod 755 "${BUILD_DIR}/DEBIAN/postinst" "${BUILD_DIR}/DEBIAN/prerm"

# 2. Install Desktop Entry & Icons
cp "${PROJECT_ROOT}/packaging/org.sajjad.WritingAssistant.desktop" "${BUILD_DIR}/usr/share/applications/"
cp "${PROJECT_ROOT}/packaging/icons/org.sajjad.WritingAssistant.svg" "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/"

# 3. Install Executable Launcher
cat << 'EOF' > "${BUILD_DIR}/usr/bin/writing-assistant"
#!/usr/bin/env bash
exec /usr/bin/python3 -m writing_companion.ui.app "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/writing-assistant"

# 4. Install GNOME Shell Extension
cp "${PROJECT_ROOT}/extension/"*.js "${BUILD_DIR}/usr/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com/"
cp "${PROJECT_ROOT}/extension/"*.json "${BUILD_DIR}/usr/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com/"
cp "${PROJECT_ROOT}/extension/"*.css "${BUILD_DIR}/usr/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com/"
if [ -d "${PROJECT_ROOT}/extension/schemas" ]; then
    cp -r "${PROJECT_ROOT}/extension/schemas" "${BUILD_DIR}/usr/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com/"
fi

# 5. Install Python Backend Package
cp -r "${PROJECT_ROOT}/src/writing_companion/"* "${BUILD_DIR}/usr/lib/python3/dist-packages/writing_companion/"

# 6. Build the .deb Package
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${DIST_DIR}/${PKG_NAME}"

echo "=== Package Build Successful! ==="
echo "Artifact: ${DIST_DIR}/${PKG_NAME}"
dpkg -I "${DIST_DIR}/${PKG_NAME}"
echo ""
echo "Contents:"
dpkg -c "${DIST_DIR}/${PKG_NAME}"
