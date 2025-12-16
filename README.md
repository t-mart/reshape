# reshape

Reshape a directory structure into another structure based on hash.

This is useful when your system already has a lot of files, but they need to be
reorganized, and the structure changes are too complex. (In particular, on
2025-12-15, I've updated how my torrent download directory is organized, and I
need to propogate that to my other seedboxes.)

Note: if there are any hash collisions while using `gen` or `apply`, all
colliding files will be ignored. This is for safety to avoid data loss. Use
another tool like `rclone` to fill in those files manually.

Note: empty directories are not represented in the JSON output, and thus will
not be created in the target structure.

## `reshape gen`

```sh
uvx git+https://github.com/t-mart/reshape.git gen /path/to/source >reshape.json
```

Outputs JSON a list of objects for each file in a root directory, containing the
path and the XXH64 hash.

## `reshape apply`

```sh
uvx git+https://github.com/t-mart/reshape.git apply /path/to/source <reshape.json
```

Given a root directory and JSON input from `reshape gen` on stdin, hardlinks
identically-hashing files from the root directory into the new structure.
