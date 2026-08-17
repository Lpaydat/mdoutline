"""Additional CLI tests for stdout error handling."""

import shlex


def test_closed_stdout_file(run_cli_pipeline):
    """Test closed stdout (>&-) produces clean error with rc=1.

    R1: When stdout file descriptor is closed, mdoutline should print one line
    to stderr and exit with code 1. No traceback should appear.
    """
    result = run_cli_pipeline(">&-", stdin="", executable="/bin/bash")

    assert result.returncode == 1
    stderr = result.stderr
    # Exactly one line starting with "mdoutline: cannot write"
    lines = stderr.strip().split("\n")
    assert len(lines) == 1
    assert lines[0].startswith("mdoutline: cannot write to standard output")
    # No traceback
    assert "Traceback" not in stderr
    # Empty stdout (can't write)
    assert result.stdout == ""


def test_disk_full_large_doc(run_cli_pipeline, tmp_path, write_md_file):
    """Test disk full (/dev/full) with large doc produces clean error with rc=1.

    R2: Writing to /dev/full with >=200k heading lines should produce OSError
    caught and handled with one-line stderr, rc=1, no traceback.
    """
    # Generate a large document with 200k heading lines
    big = tmp_path / "big.md"
    big.write_text("\n".join(f"# H{i}" for i in range(200000)) + "\n")

    result = run_cli_pipeline(
        f"{shlex.quote(str(big))} >/dev/full",
        stdin="",
    )

    assert result.returncode == 1
    stderr = result.stderr
    # Exactly one line starting with "mdoutline: cannot write"
    lines = stderr.strip().split("\n")
    assert len(lines) == 1
    assert lines[0].startswith("mdoutline: cannot write to standard output")
    # No traceback
    assert "Traceback" not in stderr


def test_broken_pipe_remains_quiet(run_cli_pipeline):
    """Test existing broken pipe behavior remains unchanged.

    T3: The BrokenPipeError handler (exit 13, SIGPIPE-like) should continue to
    work exactly as before (from mdoutline-e52 fix).
    """
    # Generate a large outline that exceeds pipe buffer (~64KB)
    lines = [f"# Heading {i}\n## Sub {i}\n### Subsub {i}\n" for i in range(5000)]
    content = "".join(lines)

    result = run_cli_pipeline("| head -1", stdin=content)

    # Should get the first line of output
    assert result.stdout == "- Heading 0\n"
    # No traceback and no BrokenPipeError message in stderr
    assert "Traceback" not in result.stderr
    assert "BrokenPipeError" not in result.stderr
    # The actual exit code from head (0), not the SIGPIPE from mdoutline
    assert result.returncode == 0
