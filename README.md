<div align="center">

</div>

```plaintext
█  ▄ ▄ █ █ ▄▄▄▄  ▄   ▄              ____
█▄▀  ▄ █ █ █   █ █   █           .'`_ o `;__,
█ ▀▄ █ █ █ █▄▄▄▀  ▀▀▀█ .       .'.'` '---'  '
█  █ █ █ █ █     ▄   █  .`-...-'.'A tool to delete virtual environments (.venv, Conda, Poetry)
           ▀      ▀▀▀    `-...-'and clean up __pycache__ and temp files.
```

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/killpy.svg)](https://pypi.org/project/killpy/)
[![Downloads](https://static.pepy.tech/personalized-badge/killpy?period=month&units=international_system&left_color=grey&right_color=blue&left_text=PyPi%20Downloads)](https://pepy.tech/project/killpy)
[![Stars](https://img.shields.io/github/stars/Tlaloc-Es/killpy?color=yellow&style=flat)](https://github.com/Tlaloc-Es/killpy/stargazers)

![killpy in action](show.gif)

</div>

# Delete .venv (Virtualenv, Poetry and Conda) Directories

`killpy` is a simple tool designed to locate and delete `.venv` directories from your projects, including virtual environments created by Poetry and Conda. It can help you quickly clean up unnecessary virtual environments and save disk space.

## Features

- **Automatic search:** Finds all .venv directories and any folders containing a pyvenv.cfg file recursively from the current working directory, as they are considered virtual environment folders.
- **Support for Conda**: Lists all available Conda environments.
- **Safe deletion:** Lists the directories to be deleted and asks for confirmation.
- **Fast and lightweight:** Minimal dependencies for quick execution.

## Installation

To install `killpy`, use pip:

```bash
pip install killpy
```

## Usage

Run the following command to search for .venv directories and any folders containing a pyvenv.cfg file, as well as to list all Conda environments from the current directory and all its subdirectories recursively:

```bash
killpy
```

With `pipx`

```bash
pipx run killpy
```

With `uvx`

```bash
uvx killpy
```

- To **close the application**, press `Ctrl+Q`.
- To **mark a virtual environment for deletion**, press `D`.
- To **confirm deletion of marked virtual environments**, press `Ctrl+D`.
- To **delete a virtual environment immediately**, press `Shift+Delete`.
- To **delete a virtual environment immediately**, press `Shift+Delete`.
- To **clean up __pycache__ folders**, press `P`.

## Roadmap

- [x] Delete `__pycache__` Files
- [ ] Remove `dist` Folders and Build Artifacts
- [ ] Clean Up Installed Package Cache
- [ ] Delete `.egg-info` and `.dist-info` Files
- [ ] Analyze and Remove Unused Dependencies
- [ ] Optimize Disk Space in Python Projects

## Contributing

Contributions are welcome! If you'd like to improve this tool, feel free to fork the repository and submit a pull request.

1. Fork the repository
1. Create a new branch for your feature: `git checkout -b my-feature`
1. Commit your changes: `git commit -m 'Add my feature'`
1. Push to the branch: `git push origin my-feature`
1. Submit a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

______________________________________________________________________

Thank you for using `killpy`! If you find it useful, please star the repository on GitHub!
