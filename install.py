#!/usr/bin/env python3

from glob import glob
import io
import os
import subprocess
import sys
import urllib.request
import zipfile

fold = os.path.abspath(os.path.dirname(sys.argv[0]))


def path(*args):
    return os.path.expanduser(os.path.expandvars(os.path.join(*args)))


def link(source, dest):
    source = os.path.join(fold, source)
    dest = path(dest)
    if os.path.exists(dest):
        print("{0} exists, not overwriting".format(dest))
    else:
        if os.path.lexists(dest):
            os.remove(dest)
        os.symlink(source, dest)
        print("{0} linked to {1}".format(dest, source))


def git_submodule_update():
    subprocess.call(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=os.path.dirname(__file__),
    )


def download_clangd():
    clangd_symlink = os.path.join(os.path.dirname(__file__), "bin", "clangd")
    clangd_loc = os.path.join(
        os.path.dirname(__file__), "bin", "clangd_12.0.0", "bin", "clangd"
    )
    if os.path.exists(clangd_symlink):
        return

    url = "https://github.com/clangd/clangd/releases/download/12.0.0/clangd-linux-12.0.0.zip"
    response = urllib.request.urlopen(url)
    contents = io.BytesIO(response.read())
    zipped = zipfile.ZipFile(contents)

    zipped.extractall(os.path.dirname(clangd_symlink))
    os.chmod(clangd_loc, 0o554)

    relpath = os.path.relpath(clangd_loc, os.path.dirname(clangd_symlink))
    os.symlink(relpath, clangd_symlink)


def install_dotfiles():
    link("dot_emacs", "~/.emacs")
    link("dot_emacs.d", "~/.emacs.d")
    link("dot_bash_common", "~/.bash_common")
    link("dot_screenrc", "~/.screenrc")
    link("dot_dir_colors", "~/.dir_colors")
    link("dot_tmux.conf", "~/.tmux.conf")
    link("dot_gitconfig", "~/.gitconfig")
    link("dot_Xdefaults", "~/.Xdefaults")
    link("dot_Xdefaults", "~/.Xresources")
    link("dot_gdbinit", "~/.gdbinit")


def install_ipython_env():
    ipython_dir = path("~", ".ipython", "profile_default", "startup")
    if not os.path.exists(ipython_dir):
        os.makedirs(ipython_dir)

    for startup_file in glob(os.path.join("ipython_startup", "*.py")):
        script_name = os.path.basename(startup_file)
        link(startup_file, os.path.join(ipython_dir, script_name))


def update_bashrc():
    bashrc_path = os.path.expanduser("~/.bashrc")
    orig_bashrc = open(bashrc_path).read()
    bashrc = orig_bashrc
    if ".bash_common" not in bashrc:
        print("Adding .bash_common to .bashrc")
        bashrc += "if [ -f ~/.bash_common ]; then . ~/.bash_common; fi\n"

    if bashrc != orig_bashrc:
        with open(bashrc_path, "w") as f:
            f.write(bashrc)


def main():
    git_submodule_update()
    download_clangd()

    install_dotfiles()
    install_ipython_env()

    update_bashrc()


if __name__ == "__main__":
    main()
