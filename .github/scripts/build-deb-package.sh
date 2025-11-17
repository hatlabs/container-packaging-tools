#!/bin/bash
# Build Debian package (.deb) in devtools container
# Container has all build dependencies pre-installed

set -e

echo "Building Debian package in Debian trixie container..."

# Build the package inside devtools container
# dpkg-buildpackage writes to .. by convention, so we move files back after
docker run --rm \
  -v "$(pwd):/workspace" \
  -w /workspace \
  devtools:latest \
  bash -c "dpkg-buildpackage -b -uc -us && mv ../*.deb ../*.buildinfo ../*.changes ./ 2>/dev/null || true"

# List generated packages
echo "📦 Generated packages:"
ls -lh *.deb

echo "✅ Package build complete"
