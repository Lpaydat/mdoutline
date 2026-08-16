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


def filter_by_depth(
    headings: list[tuple[int, str]], max_depth: int | None
) -> list[tuple[int, str]]:
    """Filter headings by maximum depth.

    Args:
        headings: A list of (depth, text) tuples from extract_headings().
        max_depth: Maximum depth to keep (inclusive). If None, returns all
            headings without filtering.

    Returns:
        A new list containing only headings with depth <= max_depth.
        Preserves original order and depth values. Does not mutate the input
        list.
    """
    if max_depth is None:
        return list(headings)
    return [(depth, text) for depth, text in headings if depth <= max_depth]


def number_headings(headings: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """Number headings according to hierarchical outline numbering.

    Args:
        headings: A list of (depth, text) tuples from extract_headings().

    Returns:
        A new list of (depth, text, number) tuples. The number is the
        hierarchical section number for each heading. Rules:
        - A heading at depth d increments counter[d] and resets ALL deeper
          counters to 0.
        - The number for a heading at depth d joins counter[1..d] with dots.
        - Format: depth 1 gets a trailing dot ("1.", "2."); depth >= 2 gets
          none ("1.1", "1.2.1").
        - Skipped intermediate levels render a mechanical 0: e.g., h1 followed
          directly by h3 -> "1.0.1".
        - Empty input returns an empty list.
        - The input list is never mutated.

    Example:
        >>> number_headings([(1, "A"), (2, "B"), (2, "C"), (3, "D"), (2, "E"), (1, "F")])
        [(1, 'A', '1.'), (2, 'B', '1.1'), (2, 'C', '1.2'), (3, 'D', '1.2.1'), (2, 'E', '1.3'), (1, 'F', '2.')]
    """
    # Initialize counters for depths 1-6 (using 1-based indexing for convenience)
    counter = [0] * 7  # index 0 unused, depths 1-6 map to indices 1-6

    result: list[tuple[int, str, str]] = []

    for depth, text in headings:
        # Increment counter at current depth
        counter[depth] += 1

        # Reset all deeper counters to 0
        for d in range(depth + 1, len(counter)):
            counter[d] = 0

        # Build number string from counter[1..depth]
        number_parts = [str(counter[d]) for d in range(1, depth + 1)]
        number = ".".join(number_parts)

        # Add trailing dot for depth 1
        if depth == 1:
            number += "."

        result.append((depth, text, number))

    return result


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

    def _non_negative_int(value: str) -> int:
        """Validate that value is a non-negative integer.

        Args:
            value: String to parse as integer.

        Returns:
            The parsed integer.

        Raises:
            argparse.ArgumentTypeError: If value is not a valid non-negative integer.
        """
        try:
            ivalue = int(value)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"invalid int value: '{value}'") from e
        if ivalue < 0:
            raise argparse.ArgumentTypeError(f"must be >= 0, got {ivalue}")
        return ivalue

    parser = argparse.ArgumentParser(description="Extract and print a Markdown outline.")
    parser.add_argument("file", nargs="?", help="Markdown file to process (default: stdin)")
    parser.add_argument(
        "--max-depth",
        type=_non_negative_int,
        default=None,
        metavar="N",
        help="maximum heading depth to include (1-6, default: all depths)",
    )
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
    headings = filter_by_depth(headings, args.max_depth)
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
