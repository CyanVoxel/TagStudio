# Contributing to TagStudio

_Last Updated: June 10th, 2024_

Thank you so much for showing interest in contributing to TagStudio! Here are a set of instructions and guidelines for contributing code or documentation to the project. This document will change over time, so make sure that your contributions still line up with the requirements here before submitting a pull request.

## Getting Started

- Check the [Planned Features](https://github.com/TagStudioDev/TagStudio/blob/main/doc/updates/planned_features.md) page, [FAQ](/README.md/#faq), as well as the open [Issues](https://github.com/TagStudioDev/TagStudio/issues) and [Pull Requests](https://github.com/TagStudioDev/TagStudio/pulls).
- If you'd like to add a feature that isn't on the roadmap or doesn't have an open issue, **PLEASE create a feature request** issue for it discussing your intentions so any feedback or important information can be given by the team first.
  - We don't want you wasting time developing a feature or making a change that can't/won't be added for any reason ranging from pre-existing refactors to design philosophy differences.

### Contribution Checklist

- I've read the [Planned Features](https://github.com/TagStudioDev/TagStudio/blob/main/doc/updates/planned_features.md) page
- I've read the [FAQ](/README.md/#faq), including the "[Features I Likely Won't Add/Pull](/README.md/#features-i-likely-wont-addpull)" section
- I've checked the open [Issues](https://github.com/TagStudioDev/TagStudio/issues) and [Pull Requests](https://github.com/TagStudioDev/TagStudio/pulls)
- **I've created a new issue for my feature _before_ starting work on it**, or have at least notified others in the relevant existing issue(s) of my intention to work on it
- I've set up my development environment including Ruff and Mypy
- I've read the [Code Guidelines](#code-guidelines) and/or [Documentation Guidelines](#documentation-guidelines)
- **_I mean it, I've found or created a new issue for my feature!_**

## Creating a Development Environment

### Prerequisites

- [Python](https://www.python.org/downloads/) 3.12
- [Ruff](https://github.com/astral-sh/ruff) (Included in `requirements-dev.txt`)
- [Mypy](https://github.com/python/mypy) (Included in `requirements-dev.txt`)
- [PyTest](https://docs.pytest.org) (Included in `requirements-dev.txt`)

### Creating a Python Virtual Environment

If you wish to launch the source version of TagStudio outside of your IDE:

> [!IMPORTANT]
> Depending on your system, Python may be called `python`, `py`, `python3`, or `py3`. These instructions use the alias `python3` for consistency. You can check to see which alias your system uses and if it's for the correct Python version by typing `python3 --version` (or whichever alias) into your terminal.

> [!TIP]
> On Linux and macOS, you can launch the `tagstudio.sh` script to skip the following process, minus the `requirements-dev.txt` installation step. _Using the script is fine if you just want to launch the program from source._

1. In the root repository directory, create a python virtual environment:  
   `python3 -m venv .venv`
2. Activate your environment:

- Windows w/Powershell: `.venv\Scripts\Activate.ps1`
- Windows w/Command Prompt: `.venv\Scripts\activate.bat`
- Linux/macOS: `source .venv/bin/activate`

3. Install the required packages:

- `pip install -r requirements.txt`
- If developing (includes Ruff and Mypy): `pip install -r requirements-dev.txt`

_Learn more about setting up a virtual environment [here](https://docs.python.org/3/tutorial/venv.html)._

### Manually Launching (Outside of an IDE)

- **Windows** (start_win.bat)

  - To launch TagStudio, launch the `start_win.bat` file. You can modify this .bat file or create a shortcut and add one or more additional arguments if desired.

- **Linux/macOS** (TagStudio.sh)

  - Run the "TagStudio.sh" script and the program should launch! (Make sure that the script is marked as executable if on Linux). Note that launching from the script from outside of a terminal will not launch a terminal window with any debug or crash information. If you wish to see this information, just launch the shell script directly from your terminal with `./TagStudio.sh`.

  - **NixOS** (Nix Flake)
    > [!WARNING]
    > Support for NixOS is still a work in progress.
    - Use the provided [Flake](https://nixos.wiki/wiki/Flakes) to create and enter a working environment by running `nix develop`. Then, run the program via `python3 tagstudio/tag_studio.py` from the root directory.

- **Any** (No Scripts)

  - Alternatively, with the virtual environment loaded, run the python file at `tagstudio\tag_studio.py` from your terminal. If you're in the project's root directory, simply run `python3 tagstudio/tag_studio.py`.

## Workflow Checks

When pushing your code, several automated workflows will check it against predefined tests and style checks. It's _highly recommended_ that you run these checks locally beforehand to avoid having to fight back-and-forth with the workflow checks inside your pull requests.

> [!TIP]
> To format the code automatically before each commit, there's a configured action available for the `pre-commit` hook. Install it by running `pre-commit install`. The hook will be executed each time on running `git commit`.

### [Ruff](https://github.com/astral-sh/ruff)

A Python linter and code formatter. Ruff uses the `pyproject.toml` as its config file and runs whenever code is pushed or pulled into the project.

#### Running Locally

- Lint code with by moving into the `/tagstudio` directory with `cd tagstudio` and running `ruff --config ../pyproject.toml`.
- Format code with `ruff format` inside the repository directory

Ruff is also available as a VS Code [extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff), PyCharm [plugin](https://plugins.jetbrains.com/plugin/20574-ruff), and [more](https://docs.astral.sh/ruff/integrations/).

### [Mypy](https://github.com/python/mypy)

Mypy is a static type checker for Python. It sure has a lot to say sometimes, but we recommend you take its advice when possible. Mypy also uses the `pyproject.toml` as its config file and runs whenever code is pushed or pulled into the project.

#### Running Locally

- **First time only:** Move into the `/tagstudio` directory with `cd tagstudio` and run the following:
  - `mkdir -p .mypy_cache`
  - `mypy --install-types --non-interactive`
- Check code by moving into the `/tagstudio` directory with `cd tagstudio` _(if you aren't already inside)_ and running `mypy --config-file ../pyproject.toml .`. _(Don't forget the `.` at the end!)_

> [!CAUTION]
> There's a known issue between PySide v6.6.3 and Mypy where Mypy will detect issues with the `.pyi` files inside of PySide and prematurely stop checking files. This issue is not present in PySide v6.6.2, which _should_ be compatible with everything else if you wish to try using that version in the meantime.

Mypy is also available as a VS Code [extension](https://marketplace.visualstudio.com/items?itemName=matangover.mypy), PyCharm [plugin](https://plugins.jetbrains.com/plugin/11086-mypy), and [more](https://plugins.jetbrains.com/plugin/11086-mypy).

### PyTest

- Run all tests by moving into the `/tagstudio` directory with `cd tagstudio` and running `pytest tests/`.

## Code Guidelines

### Style

Most of the style guidelines can be checked, fixed, and enforced via Ruff. Older code may not be adhering to all of these guidelines, in which case _"do as I say, not as I do"..._

- Do your best to write clear, concise, and modular code.
- Try to keep a maximum column with of no more than **100** characters.
- Code comments should be used to help describe sections of code that don't speak for themselves.
- Use [Google style](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) docstrings for any classes and functions you add.
  - If you're modifying an existing function that does _not_ have docstrings, you don't _have_ to add docstrings to it... but it would be pretty cool if you did ;)
- Imports should be ordered alphabetically (in newly created python files).
- When writing text for window titles, form titles, or dropdown options, use "[Title Case](https://apastyle.apa.org/style-grammar-guidelines/capitalization/title-case)" capitalization. Your IDE may have a command to format this for you automatically, although some may incorrectly capitalize short prepositions. In a pinch you can use a website such as [capitalizemytitle.com](https://capitalizemytitle.com/) to check.
- If it wasn't mentioned above, then stick to [**PEP-8**](https://peps.python.org/pep-0008/)!
  > [!WARNING]
  > Column width limits, docstring formatting, and import sorting aren't currently checked in the Ruff workflow but likely will be in the near future.

### Implementations

- Avoid direct calls to `os`
  - Use `Pathlib` library instead of `os.path`
  - Use `sys.platform` instead of `os.name`
- Don't prepend local imports with `tagstudio`, stick to `src`
- Use `logging` instead of `print` statements
- Avoid nested `f-string`s

#### Runtime

- Code must function on supported versions of Windows, macOS, and Linux:
  - Windows: 10, 11
  - macOS: 12.0+
  - Linux: TBD
- Avoid use of unnecessary logging statements in final submitted code.
- Code should not cause unreasonable slowdowns to the program outside of a progress-indicated task.

#### Git/GitHub Specifics

- Use clear and concise commit messages. If your commit does too much, either consider breaking it up into smaller commits or providing extra detail in the commit description.
- Use imperative-style present-tense commit messages. Examples:
  - "Add feature foo"
  - "Change method bar"
  - "Fix function foobar"
- Pull Requests should have an adequate title and description which clearly outline your intentions and changes/additions. Feel free to provide screenshots, GIFs, or videos, especially for UI changes.

## Documentation Guidelines

Documentation contributions include anything inside of the `doc/` folder, as well as the `README.md` and `CONTRIBUTING.md` files.

- Use "[snake_case](https://developer.mozilla.org/en-US/docs/Glossary/Snake_case)" for file and folder names
- Follow the folder structure pattern
- Don't add images or other media with excessively large file sizes
- Provide alt text for all embedded media
- Use "[Title Case](https://apastyle.apa.org/style-grammar-guidelines/capitalization/title-case)" for title capitalization

## Translation Guidelines

_TBA_
