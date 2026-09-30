# Backup behavior

Commands that modify a PDF in place ([`replace-cover`](../commands/replace-cover.md), [`set-cover`](../commands/set-cover.md), [`apply-toc`](../commands/apply-toc.md), and [`optimize`](../commands/optimize.md)) keep a backup of the original file with a `.bak` suffix. To restore the original, copy the `.bak` file back over the PDF. For the full behavior, run `calpdf --help`.

To write to a new file instead of updating the input in place, pass `--output` (short form `-o`) where the command supports it.
