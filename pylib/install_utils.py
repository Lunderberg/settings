import pathlib
import os


class Installer:
    def __init__(self, script_file):
        self._repo_path = self._find_repo_path(script_file)

    def _find_repo_path(self, file_in_repo):
        path = pathlib.Path(file_in_repo).resolve()
        while path != pathlib.Path(path.root):
            path = path.parent
            if path.joinpath(".git").exists():
                return path

        raise RuntimeError("Couldn't find .git in parent directories")

    def repo_path(self, *args):
        path = pathlib.Path(*args)

        if not self._is_relative_to(path, self._repo_path):
            path = self._repo_path / path

        return path

    def sys_path(self, *args):
        path = pathlib.Path(*args).expanduser()
        assert path.is_absolute(), "Install location must be absolute path."
        return path

    def install(self, repo_file, sys_file):
        repo_file = self.repo_path(repo_file)
        sys_file = self.sys_path(sys_file)

        if os.path.lexists(sys_file):
            assert sys_file.is_symlink(), f"{sys_file} already exists"
            assert sys_file.exists(), f"{sys_file} is a broken symlink"
            assert (
                sys_file.resolve() == repo_file
            ), f"{sys_file} points to {sys_file.resolve()}, not to {repo_file}"

        else:
            sys_file.parent.mkdir(parents=True, exist_ok=True)
            sys_file.symlink_to(repo_file)
            print("{0} linked to {1}".format(sys_file, repo_file))

    def _is_relative_to(self, path, potential_parent):
        return potential_parent in path.parents
