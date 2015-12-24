import os
import subprocess
import sys

script_dir = os.path.dirname(sys.argv[0])
venv_name = 'venv'
venv_dir = os.path.join(script_dir, venv_name)

def ensure_venv(*args, **kwargs):
    '''
    Ensures that the script is being run in a virtual environment.
    If the script is not run in a virtual environment,
      look for one in the directory of the script,
      then run itself inside that virtual environment.
    If there is no virtual environment present, make one.
    The arguments given here are interpreted according to make_venv.
    '''

    if hasattr(sys, 'real_prefix'):
        return

    make_venv(*args, **kwargs)

    venv_python = os.path.join(venv_dir,'bin','python')
    args = [venv_python] + sys.argv
    res = subprocess.call(args)
    sys.exit(res)

def make_venv(requirements=None, python='python3', script=None,
              system_site_packages=False):
    '''
    Creates the virtual environment requested.
    If the virtual environment already exists, return immediately.

    If script is not None, use it to generate the virtual environment.
    The first argument passed to the script is the full directory
      where the virtual environment should be created.

    If script is None, make a virtual environment with the python version specified.
    It then installs any requirements listed in the requirements.txt given.

    The requirements or script path are relative to the directory of sys.argv[0],
      the script that is being run.
    '''

    venv_python = os.path.join(venv_dir, 'bin','python')
    venv_pip = os.path.join(venv_dir, 'bin', 'pip')
    # Bail out if we already have made the virtualenv
    if is_exe(venv_python):
        return

    # Check input arguments
    if script is not None and requirements is not None:
        raise TooManyArguments('Cannot specify both a script and a requirements file')

    # Make sure that we have the executables that we need.
    virtualenv_exe = which('virtualenv')
    if virtualenv_exe is None:
        raise EnvironmentError('virtualenv is not installed')

    python_exe = which(python)
    if python_exe is None:
        raise EnvironmentError('Could not find python version "{}"'.format(python))

    if script is None:
        # Install the virtualenv
        system_site = ('--system-site-packages' if system_site_packages else
                       '--no-site-packages')
        res = subprocess.call([virtualenv_exe, '-p', python_exe,
                               system_site, venv_dir])
        if res:
            raise VirtualenvRunError('Error while running virtualenv')

        # Install any packages required
        if requirements is not None:
            full_path = os.path.join(script_dir, requirements)
            res = subprocess.call([venv_pip, 'install', '-r', full_path])
            if res:
                raise PipInstallError('Error installing requirements from {}'.format(requirements))
    else:
        # Run the virtualenv script
        full_path = os.path.join(script_dir, script)
        res = subprocess.call([full_path, venv_dir])
        if res:
            raise ScriptRunError('Error running venv build script')

        # Check to make sure that the script produced the desired executable
        if which(venv_python) is None:
            raise ScriptRunError('Script did not generate {}'.format(venv_python))

def is_exe(program_path):
    '''
    Returns whether the path given is an executable.
    '''
    return (os.path.isfile(program_path) and
            os.access(program_path, os.X_OK))

# Python 3.3 onward gives shutil.which(),
#   but I may starting this from an earlier version.
# Modified somewhat from http://stackoverflow.com/a/377028/2689797
def which(program):
    '''
    Given a name of a program, search PATH for an executable of that name.
    Returns the full path to the executable found.
    If no such executable exists, returns None.
    If PATHEXT has been defined, then it will also search for executable with those extensions.
    '''
    try:
        extensions = os.environ['PATHEXT'].split(os.pathsep)
    except KeyError:
        extensions = []
    extensions.insert(0, '')

    path, name = os.path.split(program)
    if path:
        # If absolute path is given, check if it is an executable
        if is_exe(program):
            return program
    else:
        # Otherwise, check for the program name in each
        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            for extension in extensions:
                exe_file = os.path.join(path, program) + extension
                if is_exe(exe_file):
                    return exe_file
    return None


class EnsureVenvException(Exception):
    '''
    Base Exception for all exceptions through by ensure_venv
    '''

class MissingVirtualenvExe(EnsureVenvException):
    pass

class MissingPythonExe(EnsureVenvException):
    pass

class TooManyArguments(EnsureVenvException):
    pass

class VirtualenvRunError(EnsureVenvException):
    pass

class PipInstallError(EnsureVenvException):
    pass

class ScriptRunError(EnsureVenvException):
    pass
