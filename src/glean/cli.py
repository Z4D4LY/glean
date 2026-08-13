"""CLI entry point."""

import sys

from dotenv import load_dotenv

from .app import Glean


def main():
    load_dotenv()
    try:
        app = Glean()
        app.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
