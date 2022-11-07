#!/usr/bin/env python3

import argparse
import io
import json
import os
import subprocess
import urllib.request
import zipfile

from install_utils import Installer

installer = Installer(__file__)
install = installer.install
repo_path = installer.repo_path
sys_path = installer.sys_path


def git_submodule_update():
    subprocess.check_call(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=repo_path(),
    )


def download_clangd():
    clangd_symlink = repo_path("bin", "clangd")
    clangd_loc = repo_path("bin", "clangd_12.0.0", "bin", "clangd")
    if os.path.lexists(clangd_symlink):
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
    install("dot_gitignore_global", "~/.gitignore_global")


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


def update_docker_config():
    """Add custom parameters to the docker config

    I'd love to just symlink ~/.docker/config.json to a file in this
    repo, but the config file has an annoying mix of user preferences
    (e.g. detachKeys) and system setup (e.g. currentContext).
    Therefore, need to update the file with my user preferences while
    carefully preserving the system setup.
    """

    config_path = sys_path("~", ".docker", "config.json")

    config = {}
    if config_path.exists():
        with config_path.open() as f:
            text = f.read()

        text = text.strip()
        if text:
            config = json.loads(text)

    updated = False

    if "detachKeys" not in config:
        config["detachKeys"] = "ctrl-@,ctrl-@"
        updated = True

    if updated:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as f:
            json.dump(config, f)


def run_private_install():
    private_script = repo_path("external", "settings-private", "install.py")
    if private_script.exists():
        subprocess.check_call([private_script])


def main(args):
    git_submodule_update()
    download_clangd()

    install_dotfiles()
    install_ipython_env()

    update_bashrc()
    update_docker_config()

    run_private_install()


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
