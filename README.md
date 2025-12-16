# reshape

Reshape a directory structure into another structure based on hash.

This is useful when your system already has a lot of files, but they need to be
reorganized. In particular, on 2025-12-15, I've updated how my torrent downloads
are organized, and I need to propogate that to my other seedboxes.

Note: empty directories are not represented in the JSON output, and thus will
not be created in the target structure.

## `reshape gen`

Outputs JSON a list of objects for each file in a root directory, containing the
path and the XXH64 hash.

## `reshape apply`

Given a root directory and JSON input from `reshape gen` on stdin, hardlinks
identically-hashing files from the root directory into the new structure.
