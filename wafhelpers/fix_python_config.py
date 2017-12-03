"""Work around waf bugs related to Python config setup."""

import ast, os, sys

from waflib import Utils  # pylint: disable=import-error
from waflib.Logs import pprint  # pylint: disable=import-error

# NOTE:  Everything in this file relates to waf bugs.  It can go away once
# the waf bugs are fixed.

# The waf code for setting up PYTHONDIR and PYTHONARCHDIR is broken, because
# get_python_lib() only returns guaranteed usable library locations when the
# 'prefix' argument is absent or None, but waf insists on feeding it the PREFIX
# value.  To make matters worse, the design of waf's ConfigSet object makes it
# impossible to get it to return a value of None for any item, so merely
# temporarily patching PREFIX doesn't work.  Thus, the most straightforward
# workaround is to duplicate the relevant code with the properly omitted
# 'prefix'.
#
# The downside of the prefixless get_python_lib() is that the result may not
# be FHS-compliant, and may result in conflicts when a base install includes
# this code and another version is installed later.  There doesn't seem to be
# a universal solution to this, but it tries to do the best it can by using
# waf's original prefixed result when it appears in the target Python's
# sys.path (with any preexisting PYTHONPATH definition inhibited).
# Unfortunately, it will only appear there if it already exists, even though
# the install itself will create it if needed.
#
# In principle, there might be some value in allowing a prefix to be optionally
# supplied (separately from PREFIX), but given that both values are already
# overridable, there's little need for an additional option.
#
# Naturally, the fix doesn't override user-supplied values, but the fixup runs
# after the version check, using the captured original settings to determine
# whether to override.

# An additional function is temporarily needed to clean up any libraries
# that had been installed to the incorrect PYTHONDIR by former
# versions of the script.
#
# Although this code is a NOP when the old and new install locations are
# identical, for maximum safety the extra deletions are done preinstall
# and postuninstall.  This might matter if the old and new locations were
# symlinked together (a possible workaround for the old bug).
#
# Merely removing the libraries doesn't remove the containing directory(s)
# which may have been newly created by the old script.  Removing any such
# directories is desirable, but doing so automatically would be too
# dangerous.  The compromise is to issue a warning message when an empty
# containing directory is left.  This is always done at the end, to avoid
# burying the warning in the install messages.


class FixConfig(object):
    """Methods and state for working around waf's python-config bugs."""

    def __init__(self, conf):
        """Initialize state from conf object."""
        self.conf = conf
        self.opts = None

    def get_options(self):
        """Capture values after option processing."""
        self.opts = self.conf.env.derive().detach()

    def fix_python_libs(self):
        """Fix up library install paths."""
        # Remember original setting for "compatibility cleanup".
        self.conf.env.OLD_PYTHONDIR = self.conf.env.PYTHONDIR
        if Utils.is_win32:
            return  # No fixups supported on Windows
        # Note that get_python_variables() doesn't work for sys.path
        path_env = dict(os.environ)
        path_env.pop('PYTHONPATH', None)  # Ignore any current PYTHONPATH
        path_str = self.conf.cmd_and_log(self.conf.env.PYTHON
                                         + ['-c',
                                            'import sys; print(sys.path)'],
                                         env=path_env)
        sys_path = ast.literal_eval(path_str)
        if (not ('PYTHONDIR' in self.opts or 'PYTHONDIR' in self.conf.environ)
            and self.conf.env.PYTHONDIR not in sys_path):
            (pydir,) = self.conf.get_python_variables(
                ["get_python_lib(plat_specific=0)"]
                )
            self.conf.env.PYTHONDIR = pydir
        if (not ('PYTHONARCHDIR' in self.opts
                 or 'PYTHONARCHDIR' in self.conf.environ)
            and self.conf.env.PYTHONARCHDIR not in sys_path):
            (pyarchdir,) = self.conf.get_python_variables(
                ["get_python_lib(plat_specific=1)"]
                )
            self.conf.env.PYTHONARCHDIR = pyarchdir or pydir

    def load(self, *args, **kwargs):
        """Do the load and capture the options."""
        self.conf.load(*args, **kwargs)
        self.get_options()

    def check_python_version(self, *args, **kwargs):
        """Check version and fix up install paths."""
        self.conf.check_python_version(*args, **kwargs)
        self.fix_python_libs()

    @staticmethod
    def cleanup_python_libs(ctx, cmd='preinstall'):
        """Remove any Python libs that were installed to the wrong location."""
        if not ctx.env.PYTHONDIR:
            return  # Here on pre-setup call
        if ctx.env.PYTHONDIR == ctx.env.OLD_PYTHONDIR:
            return  # Here when old bug had no effect
        if not os.path.isdir(ctx.env.OLD_PYTHONDIR):
            return  # Here when old dir doesn't exist or isn't a dir
        if cmd in ('preinstall', 'uninstall'):
            ctx.exec_command('rm -rf %s/ntp' % ctx.env.OLD_PYTHONDIR)
        if cmd == 'preinstall':
            return  # Skip message where it's not likely to be seen
        # See if we may have left an inappropriate empty directory
        if not os.listdir(ctx.env.OLD_PYTHONDIR):
            pprint('YELLOW',
                   'May need to manually remove %s' % ctx.env.OLD_PYTHONDIR)
