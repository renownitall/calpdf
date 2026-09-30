# Installation

To install calpdf, run the following command from the project directory:

```bash
uv pip install .
```

To set up a development environment instead, see [Development](development.md).

## Arch Linux

If you run Arch Linux, you can install the signed `calpdf-git` package from my [Forge repository](https://github.com/renownitall/forge). For setup instructions, see the [Forge README](https://github.com/renownitall/forge#set-up-the-repository).

## External dependencies

calpdf uses one program that it does not install for you:

- `qpdf`: The [`optimize`](commands/optimize.md) command requires it. You must install it before you can optimize a PDF.
