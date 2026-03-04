#!/usr/bin/env python3
"""
Useful script if you use Github Copilot or similar tools to edit large .ipynb files, which can be very slow in VS Code's diff editor.
Script NOT necessary for the notebook to run.
nb_edit.py - Notebook Reader & Editor for Large .ipynb Files

Bypasses VS Code diff editor limitations for large notebooks.
Works directly on the JSON structure of .ipynb files.

Usage Examples:
    # List all cells (summary)
    python nb_edit.py list

    # Read a specific cell (0-indexed)
    python nb_edit.py read 7

    # Read cell lines 100-150 (within that cell's source)
    python nb_edit.py read 7 --lines 100-150

    # Search for text across all cells
    python nb_edit.py search "GEOCATALOG_URI"

    # Replace text in a specific cell
    python nb_edit.py replace 70 --old "old_text" --new "new_text"

    # Replace with multiline strings from files
    python nb_edit.py replace 70 --old-file old.txt --new-file new.txt

    # Insert a new cell after cell 5
    python nb_edit.py insert 5 --type code --file new_cell.py

    # Delete a cell
    python nb_edit.py delete 10

    # Clear outputs from all cells (shrinks file significantly)
    python nb_edit.py clear-outputs

    # Clear output from a specific cell
    python nb_edit.py clear-outputs --cell 21

    # Show notebook stats
    python nb_edit.py stats

    # Backup notebook before edits
    python nb_edit.py backup
"""

import json
import sys
import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path

NOTEBOOK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hurricane_forecast_infra_impact.ipynb"
)


def load_notebook(path=None):
    """Load notebook JSON."""
    path = path or NOTEBOOK_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_notebook(nb, path=None):
    """Save notebook JSON with proper formatting."""
    path = path or NOTEBOOK_PATH
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"Saved: {path}")


def cleanup_old_backups(path=None, keep=1):
    """Remove old backup files, keeping only the most recent `keep` backups."""
    path = path or NOTEBOOK_PATH
    parent = Path(path).parent
    base = Path(path).name
    backups = sorted(parent.glob(f"{base}.backup_*"))
    if keep == 0:
        for old in backups:
            old.unlink()
            print(f"Removed old backup: {old}")
    elif len(backups) > keep:
        for old in backups[:-keep]:
            old.unlink()
            print(f"Removed old backup: {old}")


def remove_backup(backup_path):
    """Remove a specific backup file after a successful save."""
    if backup_path and os.path.exists(backup_path):
        os.unlink(backup_path)
        print(f"Cleaned up backup: {os.path.basename(backup_path)}")


def backup_notebook(path=None):
    """Create a timestamped backup and clean up older ones (keeps only the latest)."""
    path = path or NOTEBOOK_PATH
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.backup_{ts}"
    shutil.copy2(path, backup_path)
    print(f"Backup created: {backup_path}")
    cleanup_old_backups(path, keep=1)
    return backup_path


def get_cell_source(cell):
    """Get cell source as a single string."""
    src = cell.get("source", [])
    if isinstance(src, list):
        return "".join(src)
    return src


def set_cell_source(cell, text):
    """Set cell source from a string (splits into lines for .ipynb format)."""
    # .ipynb stores source as list of lines, each ending with \n except possibly the last
    lines = text.split("\n")
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + "\n")
        else:
            if line:  # don't add empty trailing line
                result.append(line)
    cell["source"] = result


# ─── Commands ───────────────────────────────────────────────────────────────

def cmd_list(args):
    """List all cells with summary info."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    print(f"Notebook: {args.notebook}")
    print(f"Total cells: {len(cells)}\n")
    print(f"{'Cell':>5}  {'Type':>8}  {'Lines':>6}  {'OutKB':>6}  First Line")
    print("-" * 80)
    for i, cell in enumerate(cells):
        src = get_cell_source(cell)
        lines = src.count("\n") + (1 if src and not src.endswith("\n") else 0)
        out_size = sum(len(str(o)) for o in cell.get("outputs", []))
        first_line = src.split("\n")[0][:50] if src else "(empty)"
        ct = cell["cell_type"][:4]
        print(f"{i:>5}  {ct:>8}  {lines:>6}  {out_size // 1024:>5}K  {first_line}")


def cmd_read(args):
    """Read a specific cell's source code."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    idx = args.cell_index

    if idx < 0 or idx >= len(cells):
        print(f"Error: Cell index {idx} out of range (0-{len(cells) - 1})")
        sys.exit(1)

    cell = cells[idx]
    src = get_cell_source(cell)
    lines = src.split("\n")

    print(f"--- Cell {idx} ({cell['cell_type']}) | {len(lines)} lines ---")

    if args.lines:
        start, end = map(int, args.lines.split("-"))
        lines = lines[start:end + 1]
        for i, line in enumerate(lines, start=start):
            print(f"{i:>5}: {line}")
    else:
        for i, line in enumerate(lines):
            print(f"{i:>5}: {line}")


def cmd_search(args):
    """Search for text across all cells."""
    nb = load_notebook(args.notebook)
    pattern = args.pattern
    found = False

    for i, cell in enumerate(nb["cells"]):
        src = get_cell_source(cell)
        lines = src.split("\n")
        for ln, line in enumerate(lines):
            if pattern in line:
                found = True
                print(f"Cell {i:>3}, line {ln:>4}: {line.strip()}")

    if not found:
        print(f"No matches found for: {pattern}")


def cmd_replace(args):
    """Replace text in a specific cell."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    idx = args.cell_index

    if idx < 0 or idx >= len(cells):
        print(f"Error: Cell index {idx} out of range (0-{len(cells) - 1})")
        sys.exit(1)

    # Get old/new text
    if args.old_file:
        with open(args.old_file, "r", encoding="utf-8") as f:
            old_text = f.read()
    else:
        old_text = args.old

    if args.new_file:
        with open(args.new_file, "r", encoding="utf-8") as f:
            new_text = f.read()
    else:
        new_text = args.new

    if not old_text:
        print("Error: Must provide --old or --old-file")
        sys.exit(1)

    src = get_cell_source(cells[idx])
    count = src.count(old_text)

    if count == 0:
        print(f"Error: Old text not found in cell {idx}")
        print(f"  Searched for: {old_text[:100]}...")
        sys.exit(1)
    elif count > 1 and not args.all:
        print(f"Warning: Found {count} occurrences. Use --all to replace all, or be more specific.")
        sys.exit(1)

    backup_path = None
    if not args.no_backup:
        backup_path = backup_notebook(args.notebook)

    if args.all:
        new_src = src.replace(old_text, new_text)
    else:
        new_src = src.replace(old_text, new_text, 1)

    set_cell_source(cells[idx], new_src)
    save_notebook(nb, args.notebook)
    remove_backup(backup_path)
    print(f"Replaced {count if args.all else 1} occurrence(s) in cell {idx}")


def cmd_replace_lines(args):
    """Replace specific line range in a cell with new content."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    idx = args.cell_index

    if idx < 0 or idx >= len(cells):
        print(f"Error: Cell index {idx} out of range (0-{len(cells) - 1})")
        sys.exit(1)

    src = get_cell_source(cells[idx])
    lines = src.split("\n")

    start, end = map(int, args.lines.split("-"))

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            new_content = f.read()
    else:
        new_content = args.content

    if not new_content:
        print("Error: Must provide --content or --file")
        sys.exit(1)

    new_lines = new_content.split("\n")

    backup_path = None
    if not args.no_backup:
        backup_path = backup_notebook(args.notebook)

    # Replace lines[start:end+1] with new_lines
    result_lines = lines[:start] + new_lines + lines[end + 1:]

    set_cell_source(cells[idx], "\n".join(result_lines))
    save_notebook(nb, args.notebook)
    remove_backup(backup_path)
    print(f"Replaced lines {start}-{end} ({end - start + 1} lines) with {len(new_lines)} lines in cell {idx}")


def cmd_insert(args):
    """Insert a new cell after the specified index."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    idx = args.after_index

    if idx < -1 or idx >= len(cells):
        print(f"Error: Index {idx} out of range (-1 to {len(cells) - 1}). Use -1 to insert at top.")
        sys.exit(1)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
    else:
        source = args.content or ""

    new_cell = {
        "cell_type": args.type,
        "metadata": {},
        "source": [],
    }
    if args.type == "code":
        new_cell["outputs"] = []
        new_cell["execution_count"] = None

    set_cell_source(new_cell, source)

    backup_path = None
    if not args.no_backup:
        backup_path = backup_notebook(args.notebook)

    cells.insert(idx + 1, new_cell)
    save_notebook(nb, args.notebook)
    remove_backup(backup_path)
    print(f"Inserted {args.type} cell at position {idx + 1}")


def cmd_delete(args):
    """Delete a cell."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    idx = args.cell_index

    if idx < 0 or idx >= len(cells):
        print(f"Error: Cell index {idx} out of range (0-{len(cells) - 1})")
        sys.exit(1)

    backup_path = None
    if not args.no_backup:
        backup_path = backup_notebook(args.notebook)

    src = get_cell_source(cells[idx])
    first_line = src.split("\n")[0][:60]
    cells.pop(idx)
    save_notebook(nb, args.notebook)
    remove_backup(backup_path)
    print(f"Deleted cell {idx}: {first_line}")


def cmd_clear_outputs(args):
    """Clear outputs from cells to reduce file size."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    cleared = 0

    if args.cell is not None:
        if args.cell < 0 or args.cell >= len(cells):
            print(f"Error: Cell {args.cell} out of range")
            sys.exit(1)
        if cells[args.cell].get("cell_type") == "code":
            cells[args.cell]["outputs"] = []
            cells[args.cell]["execution_count"] = None
            cleared = 1
    else:
        for cell in cells:
            if cell.get("cell_type") == "code" and cell.get("outputs"):
                cell["outputs"] = []
                cell["execution_count"] = None
                cleared += 1

    if cleared > 0:
        backup_path = None
        if not args.no_backup:
            backup_path = backup_notebook(args.notebook)
        save_notebook(nb, args.notebook)
        remove_backup(backup_path)

    print(f"Cleared outputs from {cleared} cell(s)")


def cmd_stats(args):
    """Show notebook statistics."""
    nb = load_notebook(args.notebook)
    cells = nb["cells"]
    file_size = os.path.getsize(args.notebook)

    code_cells = [c for c in cells if c["cell_type"] == "code"]
    md_cells = [c for c in cells if c["cell_type"] == "markdown"]
    total_src_lines = sum(get_cell_source(c).count("\n") for c in cells)
    total_output_chars = sum(
        sum(len(str(o)) for o in c.get("outputs", [])) for c in cells
    )

    print(f"Notebook: {args.notebook}")
    print(f"File size: {file_size / 1024 / 1024:.2f} MB")
    print(f"Total cells: {len(cells)} ({len(code_cells)} code, {len(md_cells)} markdown)")
    print(f"Total source lines: {total_src_lines}")
    print(f"Total output size: {total_output_chars / 1024 / 1024:.2f} MB")
    print()

    # Top 5 largest cells by source
    by_src = sorted(enumerate(cells), key=lambda x: len(get_cell_source(x[1])), reverse=True)
    print("Top 5 largest cells by source:")
    for i, (idx, cell) in enumerate(by_src[:5]):
        lines = get_cell_source(cell).count("\n")
        first = get_cell_source(cell).split("\n")[0][:50]
        print(f"  Cell {idx}: {lines} lines - {first}")

    # Top 5 largest by output
    by_out = sorted(
        enumerate(cells),
        key=lambda x: sum(len(str(o)) for o in x[1].get("outputs", [])),
        reverse=True,
    )
    print("\nTop 5 largest cells by output:")
    for i, (idx, cell) in enumerate(by_out[:5]):
        out_kb = sum(len(str(o)) for o in cell.get("outputs", [])) / 1024
        print(f"  Cell {idx}: {out_kb:.1f} KB output")


def cmd_backup(args):
    """Create a backup of the notebook."""
    backup_notebook(args.notebook)


def cmd_diff(args):
    """Show diff between current notebook and a backup."""
    nb1 = load_notebook(args.notebook)
    nb2 = load_notebook(args.backup_path)

    cells1 = nb1["cells"]
    cells2 = nb2["cells"]

    if len(cells1) != len(cells2):
        print(f"Cell count differs: current={len(cells1)}, backup={len(cells2)}")

    for i in range(min(len(cells1), len(cells2))):
        src1 = get_cell_source(cells1[i])
        src2 = get_cell_source(cells2[i])
        if src1 != src2:
            print(f"\n{'='*60}")
            print(f"Cell {i} differs:")
            lines1 = src1.split("\n")
            lines2 = src2.split("\n")
            import difflib
            diff = difflib.unified_diff(lines2, lines1, lineterm="",
                                         fromfile=f"backup/cell_{i}",
                                         tofile=f"current/cell_{i}")
            for line in diff:
                print(line)


def main():
    parser = argparse.ArgumentParser(
        description="Notebook Editor - bypass VS Code diff limitations for large notebooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--notebook", "-n", default=NOTEBOOK_PATH,
        help="Path to notebook file (default: hurricane_forecast_infra_impact.ipynb)"
    )

    sub = parser.add_subparsers(dest="command", help="Command to run")

    # list
    sub.add_parser("list", aliases=["ls"], help="List all cells")

    # read
    p = sub.add_parser("read", aliases=["cat"], help="Read a cell's source")
    p.add_argument("cell_index", type=int, help="Cell index (0-based)")
    p.add_argument("--lines", "-l", help="Line range, e.g. 100-150")

    # search
    p = sub.add_parser("search", aliases=["grep"], help="Search for text")
    p.add_argument("pattern", help="Text to search for")

    # replace
    p = sub.add_parser("replace", help="Replace text in a cell")
    p.add_argument("cell_index", type=int, help="Cell index (0-based)")
    p.add_argument("--old", help="Text to replace")
    p.add_argument("--new", help="Replacement text")
    p.add_argument("--old-file", help="File containing text to replace")
    p.add_argument("--new-file", help="File containing replacement text")
    p.add_argument("--all", action="store_true", help="Replace all occurrences")
    p.add_argument("--no-backup", action="store_true", help="Skip backup")

    # replace-lines
    p = sub.add_parser("replace-lines", help="Replace line range in a cell")
    p.add_argument("cell_index", type=int, help="Cell index (0-based)")
    p.add_argument("--lines", "-l", required=True, help="Line range, e.g. 100-150")
    p.add_argument("--content", "-c", help="New content string")
    p.add_argument("--file", "-f", help="File with new content")
    p.add_argument("--no-backup", action="store_true", help="Skip backup")

    # insert
    p = sub.add_parser("insert", help="Insert a new cell")
    p.add_argument("after_index", type=int, help="Insert after this index (-1 for top)")
    p.add_argument("--type", "-t", choices=["code", "markdown"], default="code")
    p.add_argument("--content", "-c", help="Cell content string")
    p.add_argument("--file", "-f", help="File with cell content")
    p.add_argument("--no-backup", action="store_true", help="Skip backup")

    # delete
    p = sub.add_parser("delete", aliases=["rm"], help="Delete a cell")
    p.add_argument("cell_index", type=int, help="Cell index (0-based)")
    p.add_argument("--no-backup", action="store_true", help="Skip backup")

    # clear-outputs
    p = sub.add_parser("clear-outputs", help="Clear cell outputs")
    p.add_argument("--cell", type=int, help="Specific cell index (default: all)")
    p.add_argument("--no-backup", action="store_true", help="Skip backup")

    # stats
    sub.add_parser("stats", help="Show notebook statistics")

    # backup
    sub.add_parser("backup", help="Create a backup")

    # diff
    p = sub.add_parser("diff", help="Diff current vs backup")
    p.add_argument("backup_path", help="Path to backup file")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    cmd_map = {
        "list": cmd_list, "ls": cmd_list,
        "read": cmd_read, "cat": cmd_read,
        "search": cmd_search, "grep": cmd_search,
        "replace": cmd_replace,
        "replace-lines": cmd_replace_lines,
        "insert": cmd_insert,
        "delete": cmd_delete, "rm": cmd_delete,
        "clear-outputs": cmd_clear_outputs,
        "stats": cmd_stats,
        "backup": cmd_backup,
        "diff": cmd_diff,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
