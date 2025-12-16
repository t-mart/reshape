from pathlib import Path
from dataclasses import dataclass
import json
from collections import defaultdict

import xxhash
import click


def humanize_bytes(num_bytes: int | float) -> str:
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.2f} PiB"


@dataclass
class FileEntry:
    path: Path
    hexhash: str

    @staticmethod
    def get_hash(path: Path) -> str:
        hasher = xxhash.xxh128()
        with path.open("rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def from_path(cls, path: Path) -> "FileEntry":
        hexhash = cls.get_hash(path)
        return cls(path=path, hexhash=hexhash)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "FileEntry":
        path = data["path"]
        hexhash = data["hexhash"]
        return cls(path=Path(path), hexhash=hexhash)

    def to_dict(self) -> dict[str, str]:
        return {
            "path": str(self.path),
            "hexhash": self.hexhash,
        }


@click.group()
def reshape():
    pass


@reshape.command()
@click.argument(
    "root", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
def gen(root: Path) -> None:
    """
    Outputs JSON a list of objects for each file in a root directory, containing the
    path and the XXH64 hash.
    """
    files: list[Path] = [path for path in root.rglob("**/*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    total_bytes_human = humanize_bytes(total_bytes)
    hashes: dict[str, list[Path]] = defaultdict(list)

    bytes_hashed = 0

    for path in files:
        hexhash = FileEntry.get_hash(path)
        bytes_hashed += path.stat().st_size
        bytes_hashed_human = humanize_bytes(bytes_hashed)
        progress_part = f"[bytes: {bytes_hashed_human} / {total_bytes_human}, ({bytes_hashed / total_bytes:.2%})]"
        hashes[hexhash].append(path)
        collision = len(hashes[hexhash]) > 1
        click.echo(
            f"{progress_part} {hexhash} {path}{' ⚠️ (collision)' if collision else ''}",
            err=True,
        )

    entries: list[FileEntry] = []
    for hexhash, paths in hashes.items():
        if len(paths) == 1:
            entries.append(FileEntry(path=paths[0], hexhash=hexhash))
        else:
            click.echo(
                f"Omitting output for collision to hash {hexhash} with files:", err=True
            )
            for path in paths:
                click.echo(f" - {path}", err=True)

    click.echo(json.dumps([entry.to_dict() for entry in entries], indent=2))


@reshape.command()
@click.argument(
    "root", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)
def apply(root: Path) -> None:
    """
    Given a root directory and JSON input from `reshape gen` on stdin, hardlinks
    identically-hashing files from the root directory into the new structure.
    """

    # 1. read entries from stdin
    # 2. produce hashes for each file in source dir
    # 3. for non-colliding files, hard link from source to target

    input_entries: list[FileEntry] = [
        FileEntry.from_dict(entry)
        for entry in json.load(click.get_text_stream("stdin"))
    ]
    input_hashes: dict[str, Path] = {
        entry.hexhash: entry.path for entry in input_entries
    }

    source_files: list[Path] = [path for path in root.rglob("**/*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in source_files)
    total_bytes_human = humanize_bytes(total_bytes)
    source_hashes: dict[str, list[Path]] = defaultdict(list)

    bytes_hashed = 0

    for path in source_files:
        hexhash = FileEntry.get_hash(path)
        bytes_hashed += path.stat().st_size
        bytes_hashed_human = humanize_bytes(bytes_hashed)
        progress_part = f"[bytes: {bytes_hashed_human} / {total_bytes_human}, ({bytes_hashed / total_bytes:.2%})]"
        source_hashes[hexhash].append(path)
        collision = len(source_hashes[hexhash]) > 1
        click.echo(
            f"{progress_part} {hexhash} {path}{' ⚠️ (collision)' if collision else ''}",
            err=True,
        )

    for hexhash, paths in source_hashes.items():
        if hexhash not in input_hashes:
            continue
        if len(paths) > 1:
            click.echo(
                f"Omitting hard link for collision to hash {hexhash} with files:",
                err=True,
            )
            for path in paths:
                click.echo(f" - {path}", err=True)
            continue

        new_path = input_hashes[hexhash]
        target_path = paths[0]
        click.echo(f"Linking {target_path} to {new_path}", err=True)

        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            click.echo(f"Error creating directories for {new_path}: {e}", err=True)
            continue

        try:
            new_path.unlink(missing_ok=True)
        except Exception as e:
            click.echo(f"Error removing existing file {new_path}: {e}", err=True)
            continue

        try:
            new_path.hardlink_to(target_path)
        except Exception as e:
            click.echo(f"Error hardlinking {new_path} to {target_path}: {e}", err=True)
            continue