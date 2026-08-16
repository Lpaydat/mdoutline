"""Markdown outline extractor.

Extracts ATX-style headings from Markdown content and renders them as an outline.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable


def extract_headings(lines: Iterable[str]) -> list[tuple[int, str]]:
    """Extract ATX headings from Markdown lines.

    Args:
        lines: An iterable of strings representing Markdown content.

    Returns:
        A list of (depth, text) tuples where depth is 1-6 and text is the
        heading content without the # markers.
    """
    headings: list[tuple[int, str]] = []
    in_fence = False
    fence_char = ""

    for line in lines:
        # Check if we're entering or exiting a fence
        stripped = line.lstrip(" ")
        leading_spaces = len(line) - len(stripped)

        if not in_fence and leading_spaces <= 3:
            # Check if this line opens a fence (up to 3 leading spaces)
            if stripped.startswith("```") or stripped.startswith("~~~"):
                # Count the fence characters
                fence_candidate = stripped[0]
                count = 0
                for ch in stripped:
                    if ch == fence_candidate:
                        count += 1
                    else:
                        break
                if count >= 3:
                    in_fence = True
                    fence_char = fence_candidate
                    continue
        else:
            # Check if this line closes the current fence
            if leading_spaces <= 3 and (
                (fence_char == "`" and stripped.startswith("```"))
                or (fence_char == "~" and stripped.startswith("~~~"))
            ):
                # Verify it's the same fence character
                closing_char = stripped[0]
                count = 0
                for ch in stripped:
                    if ch == closing_char:
                        count += 1
                    else:
                        break
                if count >= 3 and closing_char == fence_char:
                    in_fence = False
                    fence_char = ""
                    continue
            # Inside fence - skip heading detection
            continue

        # Not in a fence - check for heading
        # At most 3 leading spaces
        if leading_spaces > 3:
            continue

        # Count consecutive # characters at start
        hash_count = 0
        for ch in stripped:
            if ch == "#":
                hash_count += 1
            else:
                break

        # Must have 1-6 hashes, followed by space or end of line
        if hash_count < 1 or hash_count > 6:
            continue

        # Check what comes after the hashes
        if len(stripped) > hash_count:
            # Must have a space after the hashes
            if stripped[hash_count] != " ":
                continue
            # Text starts after the space
            text = stripped[hash_count + 1 :]
        else:
            # Just hashes - empty text
            text = ""

        # Strip trailing closing hashes with any preceding whitespace
        # Example: "## Title ##" -> "Title"
        text = text.rstrip()
        if text:
            # Find and remove trailing hashes with whitespace before them
            i = len(text) - 1
            while i >= 0 and text[i] == "#":
                i -= 1
            # i is now at the last non-# character (or -1 if all #)
            # Also strip any whitespace before the trailing hashes
            while i >= 0 and text[i].isspace():
                i -= 1
            text = text[: i + 1] if i >= 0 else ""

        text = text.strip()

        headings.append((hash_count, text))

    return headings


def render_outline(headings: list[tuple[int, str]]) -> str:
    """Render a list of headings as an outline string.

    Args:
        headings: A list of (depth, text) tuples from extract_headings().

    Returns:
        A string with one line per heading, indented by 2 spaces per depth
        level below h1. Empty string for empty input.
    """
    if not headings:
        return ""

    lines: list[str] = []
    for depth, text in headings:
        indent = "  " * (depth - 1)
        if text:
            lines.append(f"{indent}- {text}")
        else:
            lines.append(f"{indent}-")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for mdoutline.

    Args:
        argv: Command-line arguments (None uses sys.argv).

    Returns:
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(description="Extract and print a Markdown outline.")
    parser.add_argument("file", nargs="?", help="Markdown file to process (default: stdin)")
    args = parser.parse_args(argv)

    # Determine source name for error messages
    source_name = args.file if args.file is not None else "<stdin>"

    try:
        if args.file is not None:
            with open(args.file, encoding="utf-8-sig") as f:
                content = f.read()
        else:
            if sys.stdin is None:
                print("mdoutline: cannot read <stdin>: file descriptor is closed", file=sys.stderr)
                return 1
            # Read bytes and decode with utf-8-sig to handle BOM
            content_bytes = sys.stdin.buffer.read()
            content = content_bytes.decode("utf-8-sig")
    except OSError as e:
        print(f"mdoutline: cannot read '{source_name}': {e.strerror}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"mdoutline: cannot read '{source_name}': {e.reason}", file=sys.stderr)
        return 1

    lines = content.splitlines()
    headings = extract_headings(lines)
    outline = render_outline(headings)

    # Handle broken pipe quietly (like coreutils tools)
    try:
        sys.stdout.write(outline)
        sys.stdout.flush()
    except BrokenPipeError:
        # Redirect stdout to /dev/null to suppress "Exception ignored" message
        with open(os.devnull, "wb") as devnull:
            os.dup2(devnull.fileno(), sys.stdout.fileno())
        # Exit with SIGPIPE-like exit code (13 on Linux)
        os._exit(13)

    return 0


if __name__ == "__main__":
    sys.exit(main())
