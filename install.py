#!/usr/bin/env python3

import argparse
from glob import glob
import io
import os
import pathlib
import subprocess
import sys
import urllib.request
import zipfile


def apply_monkey_patches():
    def is_relative_to(path, potential_parent):
        return potential_parent in path.parents

    def readlink(path):
        return pathlib.Path(os.readlink(path))

    pathlib.Path.lexists = os.path.lexists

    # Patched is_relaitve_to applies prior to python 3.9
    if not hasattr(pathlib.Path, "is_relative_to"):
        pathlib.Path.is_relative_to = is_relative_to

    # Patched readlink applies prior to python 3.9
    if not hasattr(pathlib.Path, "readlink"):
        pathlib.Path.readlink = readlink


def repo_path(*args):
    path = pathlib.Path(*args)

    script_dir = pathlib.Path(__file__).parent.resolve()
    if not path.is_relative_to(script_dir):
        path = script_dir / path

    return path


def sys_path(*args):
    path = pathlib.Path(*args).expanduser()
    assert path.is_absolute(), "Install location must be absolute path."
    return path


def install(repo_file, sys_file):
    repo_file = repo_path(repo_file)
    sys_file = sys_path(sys_file)

    if sys_file.lexists():
        assert sys_file.is_symlink(), f"{sys_file} already exists"
        assert sys_file.exists(), f"{sys_file} is a broken symlink"
        assert (
            sys_file.resolve() == repo_file
        ), f"{sys_file} points to {sys_file.resolve()}, not to {repo_file}"

    else:
        sys_file.symlink_to(repo_file)
        print("{0} linked to {1}".format(sys_file, repo_file))


def git_submodule_update():
    subprocess.check_call(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=pathlib.Path(__file__).parent,
    )


def download_clangd():
    clangd_symlink = repo_path("bin", "clangd")
    clangd_loc = repo_path("bin", "clangd_12.0.0", "bin", "clangd")
    if clangd_symlink.lexists():
        assert clangd_symlink.is_symlink(), f"{clangd_symlink} already exists"
        assert clangd_symlink.exists(), f"{clangd_symlink} is a broken symlink"
        assert (
            clangd_symlink.resolve() == clangd_loc
        ), f"{clangd_symlink} points to {clangd_symlink.resolve()}, expected {clangd_loc}"
        return

    url = "https://github.com/clangd/clangd/releases/download/12.0.0/clangd-linux-12.0.0.zip"
    response = urllib.request.urlopen(url)
    contents = io.BytesIO(response.read())
    zipped = zipfile.ZipFile(contents)

    zipped.extractall(clangd_symlink.parent)
    clangd_loc.chmod(0o554)

    relpath = clangd_loc.relative_to(clangd_symlink.parent)
    clangd_symlink.symlink_to(relpath)


def install_dotfiles():
    install("dot_emacs", "~/.emacs")
    install("dot_emacs.d", "~/.emacs.d")
    install("dot_bash_common", "~/.bash_common")
    install("dot_screenrc", "~/.screenrc")
    install("dot_dir_colors", "~/.dir_colors")
    install("dot_tmux.conf", "~/.tmux.conf")
    install("dot_gitconfig", "~/.gitconfig")
    install("dot_Xdefaults", "~/.Xdefaults")
    install("dot_Xdefaults", "~/.Xresources")
    install("dot_gdbinit", "~/.gdbinit")


def install_ipython_env():
    ipython_repo = repo_path("ipython_startup")
    ipython_sys = sys_path("~", ".ipython", "profile_default", "startup")

    ipython_sys.mkdir(parents=True, exist_ok=True)

    for startup_file_repo in ipython_repo.glob("*.py"):
        startup_file_sys = ipython_sys / startup_file_repo.name
        install(startup_file_repo, startup_file_sys)


def update_bashrc():
    bashrc_path = sys_path("~", ".bashrc")
    orig_bashrc = open(bashrc_path).read()
    bashrc = orig_bashrc
    if ".bash_common" not in bashrc:
        print("Adding .bash_common to .bashrc")
        bashrc += "if [ -f ~/.bash_common ]; then . ~/.bash_common; fi\n"

    if bashrc != orig_bashrc:
        with open(bashrc_path, "w") as f:
            f.write(bashrc)


def main(args):
    apply_monkey_patches()

    git_submodule_update()
    download_clangd()

    install_dotfiles()
    install_ipython_env()

    update_bashrc()


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )

    args = parser.parse_args()

    try:
        main(args)
    except Exception:
        if args.pdb:
            import pdb, traceback

            traceback.print_exc()
            pdb.post_mortem()
        raise


if __name__ == "__main__":
    arg_main()
