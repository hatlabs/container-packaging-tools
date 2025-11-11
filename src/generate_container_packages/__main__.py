"""Entry point for generate-container-packages command."""

import sys


def main():
    """Main entry point for CLI."""
    print("Container Packaging Tools")
    print(f"Version: {__package__.__version__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
