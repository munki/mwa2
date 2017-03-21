"""
munkiwebadmin/utils.py

utilities used by other apps
"""
import logging
import os
import subprocess
from django.conf import settings

APPNAME = settings.APPNAME
REPO_DIR = settings.MUNKI_REPO_DIR

LOGGER = logging.getLogger('munkiwebadmin')

try:
    GIT = settings.GIT_PATH
except AttributeError:
    GIT = None

class MunkiGit(object):
    """A simple interface for some common interactions with the git binary"""
    cmd = GIT
    git_repo_dir = os.getcwd()
    args = []
    results = {}

    def run_git(self, custom_args=None):
        """Executes the git command with the current set of arguments and
        returns a dictionary with the keys 'output', 'error', and
        'returncode'. You can optionally pass an array into customArgs to
        override the self.args value without overwriting them."""
        custom_args = self.args if custom_args is None else custom_args
        proc = subprocess.Popen([self.cmd] + custom_args,
                                shell=False,
                                bufsize=-1,
                                cwd=self.git_repo_dir,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        (output, error) = proc.communicate()
        self.results = {"output": output,
                        "error": error, "returncode": proc.returncode}
        return self.results

    def path_is_gitignored(self, a_path):
        """Returns True if path will be ignored by Git (usually due to being
        in a .gitignore file)"""
        self.git_repo_dir = os.path.dirname(a_path)
        self.run_git(['check-ignore', a_path])
        return self.results['returncode'] == 0

    def path_is_in_git_repo(self, a_path):
        """Returns True if the path is in a Git repo, false otherwise."""
        self.git_repo_dir = os.path.dirname(a_path)
        self.run_git(['status', a_path])
        return self.results['returncode'] == 0

    def commit_file_at_path(self, a_path, committer):
        """Commits the file at 'a_path'. This method will also automatically
        generate the commit log appropriate for the status of a_path where
        status would be 'modified', 'new file', or 'deleted'"""

        # get the author information
        author_name = committer.first_name + ' ' + committer.last_name
        author_name = author_name if author_name != ' ' else committer.username
        author_email = (committer.email or
                        "%s@%s" % (committer.username, APPNAME))
        author_info = '%s <%s>' % (author_name, author_email)

        # get the status of the file at a_path
        self.git_repo_dir = os.path.dirname(a_path)
        status_results = self.run_git(['status', a_path])
        status_output = status_results['output']
        if status_output.find("new file:") != -1:
            action = 'created'
        elif status_output.find("modified:") != -1:
            action = 'modified'
        elif status_output.find("deleted:") != -1:
            action = 'deleted'
        else:
            action = 'did something with'

        # determine the path relative to REPO_DIR for the file at a_path
        itempath = a_path
        if a_path.startswith(REPO_DIR):
            itempath = a_path[len(REPO_DIR)+1:]

        # generate the log message
        log_msg = ('%s %s \'%s\' via %s'
                   % (author_name, action, itempath, APPNAME))
        LOGGER.info("Doing git commit for %s", itempath)
        LOGGER.debug(log_msg)
        self.run_git(['commit', '-m', log_msg, '--author', author_info])
        if self.results['returncode'] != 0:
            LOGGER.info("Failed to commit changes to %s", a_path)
            LOGGER.info(self.results['error'])
            return -1
        return 0

    def add_file_at_path(self, a_path, committer):
        """Commits a file to the Git repo."""
        if self.path_is_in_git_repo(a_path):
            if not self.path_is_gitignored(a_path):
                self.git_repo_dir = os.path.dirname(a_path)
                self.run_git(['add', a_path])
                if self.results['returncode'] == 0:
                    self.commit_file_at_path(a_path, committer)
                else:
                    LOGGER.info("Git error: %s", self.results['error'])
        else:
            LOGGER.debug("%s is not in a git repo.", a_path)

    def delete_file_at_path(self, a_path, committer):
        """Deletes a file from the filesystem and Git repo."""
        if self.path_is_in_git_repo(a_path):
            if not self.path_is_gitignored(a_path):
                self.git_repo_dir = os.path.dirname(a_path)
                self.run_git(['rm', a_path])
                if self.results['returncode'] == 0:
                    self.commit_file_at_path(a_path, committer)
                else:
                    LOGGER.info("Git error: %s", self.results['error'])
        else:
            LOGGER.debug("%s is not in a git repo.", a_path)
