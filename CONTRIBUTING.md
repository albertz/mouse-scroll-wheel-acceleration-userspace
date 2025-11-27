Thank you for your interest in contributing to `scroll-accelerator`!

We ask that you follow the guidelines below in order to make it easier to
review and merge your changes.

## Prerequisites

### Uninstall the package (if applicable)

If you already installed the package using `pipx` or some other method,
it is highly recommended to uninstall it first.
This will ensure that you are not using a version of the package that is not
under development.
See the *Uninstallation* section in the [README](README.md) for instructions.

### Install `uv`

We ask that you use `uv` to manage the project and its dependencies.
`uv` is a modern, fast, and cross-platform Python package and project
management tool.
To install `uv`, see [here](https://docs.astral.sh/uv/getting-started/installation/).

### Fork the repository

If you want to contribute and you do not have write access to the
repository,
you will need to fork the repository (create a copy of the repository in
your own GitHub account).
To fork, go to our [GitHub repository page](https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace)
and click the "Fork" button in the top right corner.
Follow the instructions to finish creating the fork.

## Setup

Now that you have forked the repository, you can clone it using:
```bash
git clone <your-fork-url> scroll-accelerator
cd scroll-accelerator
```

We've included a `uv.lock` file to lock the dependencies for development
purposes.
To install the package and its dependencies with uv, simply run:
```bash
uv sync
```
This will create a virtual environment and install the package and its
dependencies
into it.

To run the application, you can use the `uv run` command:
```bash
uv run scroll-accelerator
```

Alternatively, you can first manually activate the virtual environment.
```bash
source .venv/bin/activate
```

You can then run the application as normal:
```bash
scroll-accelerator
```

## Pre-commit hooks

We use `pre-commit` to run automated checks and formatting on the code
before it is committed.
To install the pre-commit hooks, run:
```bash
uv run pre-commit install
```
Now whenever you commit, the pre-commit hooks will run and check the code.
If the code does not pass the checks, the commit will be rejected.
Pre-commit may automatically fix some of the issues,
but if any of the files have been modified, you will need to stage them again
using `git add` and commit again.

You can also run the checks manually without committing:
```bash
uv run pre-commit run --all-files
```

## Committing and pushing

When you are satisfied with your changes, you can stage and commit them:
```bash
git add -A
git commit -m "Your commit message"
```
or in one command:
```bash
git commit -am "Your commit message"
```

You can then push your changes to your fork:
```bash
git push
```

## Submitting a pull request

Now that you have pushed your changes to your fork,
you can submit a pull request to the main branch of the repository.
To do this, go to the the [pull requests page](https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace/pulls)
and click the "New pull request" button.
Follow the instructions to submit the pull request.
