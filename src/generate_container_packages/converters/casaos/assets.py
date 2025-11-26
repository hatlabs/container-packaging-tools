"""Asset manager for CasaOS to HaLOS conversion.

Downloads and validates icons and screenshots from URLs specified in
CasaOS metadata. Implements retry logic, parallel downloads, and format
validation.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from .models import ConversionContext


class AssetManager:
    """Manages asset downloads for CasaOS apps.

    Downloads icons and screenshots with:
    - Retry logic with exponential backoff (1s, 2s, 4s)
    - Size validation (icons ≤5MB, screenshots ≤10MB, total ≤50MB)
    - Format validation (PNG, JPG, SVG)
    - Parallel screenshot downloads
    - Graceful error handling with warnings

    No caching layer - downloads directly to output directory structure.
    """

    # Size limits in MB
    MAX_ICON_SIZE_MB = 5
    MAX_SCREENSHOT_SIZE_MB = 10
    MAX_TOTAL_SIZE_MB = 50

    # Download configuration
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 4  # Initial attempt + 3 retries
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff delays in seconds
    MAX_PARALLEL_DOWNLOADS = 5

    def __init__(self, output_dir: Path) -> None:
        """Initialize asset manager.

        Args:
            output_dir: Directory to save downloaded assets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _download_file(
        self, url: str, dest_path: Path, timeout: int, max_size_mb: int
    ) -> bool:
        """Download file with retry logic and size validation.

        Args:
            url: URL to download from
            dest_path: Destination file path
            timeout: Request timeout in seconds
            max_size_mb: Maximum file size in MB

        Returns:
            True if download successful, False otherwise
        """
        max_size_bytes = max_size_mb * 1024 * 1024

        for attempt in range(self.MAX_RETRIES):
            try:
                # Make request with timeout
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()

                # Check Content-Length header if available
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_size_bytes:
                    return False

                # Get content and check size
                content = response.content
                if len(content) > max_size_bytes:
                    return False

                # Write to file
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(content)
                return True

            except (requests.RequestException, OSError):
                # Clean up partial file if it exists
                dest_path.unlink(missing_ok=True)

                # Retry with exponential backoff (except on last attempt)
                if attempt < len(self.RETRY_DELAYS):
                    time.sleep(self.RETRY_DELAYS[attempt])
                    continue
                return False

        return False

    def _validate_image(self, path: Path, max_size_mb: int) -> bool:
        """Validate image format and size.

        Args:
            path: Path to image file
            max_size_mb: Maximum file size in MB

        Returns:
            True if valid, False otherwise
        """
        # Check file exists
        if not path.exists():
            return False

        # Check size
        size_bytes = path.stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        if size_bytes > max_size_bytes:
            return False

        # Check format - allow SVG without Pillow validation
        if path.suffix.lower() == ".svg":
            # Basic SVG validation - check for SVG marker
            try:
                with open(path, "rb") as f:
                    content = f.read(1024)
                    return b"<svg" in content or b"<?xml" in content
            except OSError:
                return False

        # Validate raster images (PNG, JPG, etc.) with Pillow
        try:
            with Image.open(path) as img:
                # Just opening and checking format is sufficient
                # verify() and load() may fail on minimal valid images
                _ = img.format
            return True
        except Exception:
            return False

    def download_icon(
        self, url: str, app_id: str, context: ConversionContext
    ) -> Path | None:
        """Download application icon.

        Args:
            url: Icon URL
            app_id: Application identifier
            context: Conversion context for warnings

        Returns:
            Path to downloaded icon, or None on failure
        """
        # Determine file extension from URL
        url_path = Path(url)
        ext = url_path.suffix.lower()
        if not ext or ext not in [".png", ".jpg", ".jpeg", ".svg"]:
            ext = ".png"  # Default to PNG if unknown

        # Create destination path and ensure app directory exists
        app_dir = self.output_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        dest_path = app_dir / f"icon{ext}"

        # Download with retry
        success = self._download_file(
            url, dest_path, self.TIMEOUT_SECONDS, self.MAX_ICON_SIZE_MB
        )

        if not success:
            context.warnings.append(f"Failed to download icon from {url}")
            return None

        # Validate image
        if not self._validate_image(dest_path, self.MAX_ICON_SIZE_MB):
            context.warnings.append(f"Icon validation failed: {dest_path}")
            dest_path.unlink(missing_ok=True)
            return None

        # Track download
        context.downloaded_assets.append(str(dest_path))
        return dest_path

    def download_screenshots(
        self, urls: list[str], app_id: str, context: ConversionContext
    ) -> list[Path]:
        """Download screenshots in parallel.

        Args:
            urls: List of screenshot URLs
            app_id: Application identifier
            context: Conversion context for warnings

        Returns:
            List of successfully downloaded screenshot paths
        """
        if not urls:
            return []

        screenshots_dir = self.output_dir / app_id / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        def download_screenshot(index_url: tuple[int, str]) -> Path | None:
            """Download single screenshot."""
            index, url = index_url

            # Determine file extension
            url_path = Path(url)
            ext = url_path.suffix.lower()
            if not ext or ext not in [".png", ".jpg", ".jpeg"]:
                ext = ".png"

            # Create destination path
            dest_path = screenshots_dir / f"screenshot-{index + 1}{ext}"

            # Download
            success = self._download_file(
                url, dest_path, self.TIMEOUT_SECONDS, self.MAX_SCREENSHOT_SIZE_MB
            )

            if not success:
                context.warnings.append(f"Failed to download screenshot from {url}")
                return None

            # Validate
            if not self._validate_image(dest_path, self.MAX_SCREENSHOT_SIZE_MB):
                context.warnings.append(f"Screenshot validation failed: {dest_path}")
                dest_path.unlink(missing_ok=True)
                return None

            # Track download
            context.downloaded_assets.append(str(dest_path))
            return dest_path

        # Download in parallel
        results: list[Path] = []
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_DOWNLOADS) as executor:
            futures = executor.map(download_screenshot, enumerate(urls))
            results = [path for path in futures if path is not None]

        return results

    def download_all_assets(
        self,
        icon_url: str | None,
        screenshot_urls: list[str],
        app_id: str,
        context: ConversionContext,
    ) -> dict[str, Any]:
        """Download all assets for an app.

        Downloads icon and screenshots, checking total size limit.

        Args:
            icon_url: Icon URL (optional)
            screenshot_urls: List of screenshot URLs
            app_id: Application identifier
            context: Conversion context for warnings

        Returns:
            Dictionary with:
                - icon: Path | None
                - screenshots: list[Path]
        """
        icon_path: Path | None = None
        screenshot_paths: list[Path] = []

        # Download icon first
        if icon_url:
            icon_path = self.download_icon(icon_url, app_id, context)

        # Download screenshots
        screenshot_paths = self.download_screenshots(screenshot_urls, app_id, context)

        # Check total size (only if files exist)
        total_size = 0
        all_paths = []
        if icon_path:
            all_paths.append(icon_path)
        all_paths.extend(screenshot_paths)

        for path in all_paths:
            if path.exists():
                total_size += path.stat().st_size

        max_total_bytes = self.MAX_TOTAL_SIZE_MB * 1024 * 1024
        if total_size > max_total_bytes:
            context.warnings.append(
                f"Total asset size ({total_size / 1024 / 1024:.1f}MB) "
                f"exceeds limit ({self.MAX_TOTAL_SIZE_MB}MB)"
            )

        return {"icon": icon_path, "screenshots": screenshot_paths}
