import os
import subprocess
from django.conf import settings

APPNAME = settings.APPNAME
REPO_DIR = settings.MUNKI_REPO_DIR


try:
    GIT = settings.GIT_PATH
except:
    GIT = None

class MunkiGit(object):
    """A simple interface for some common interactions with the git binary"""
    cmd = GIT
    args = []
    results = {}

    @staticmethod
    def __chdirToMatchPath(aPath):
        """Changes the current working directory to the same parent directory as
        the file specified in aPath. Example:
        "/Users/Shared/munki_repo/manifests/CoolManifest" would change
        directories to "/Users/Shared/munki_repo/manifests" """
        os.chdir(os.path.dirname(aPath))

    def runGit(self, customArgs=None):
        """Executes the git command with the current set of arguments and
        returns a dictionary with the keys 'output', 'error', and
        'returncode'. You can optionally pass an array into customArgs to
        override the self.args value without overwriting them."""
        customArgs = self.args if customArgs == None else customArgs
        proc = subprocess.Popen([self.cmd] + customArgs,
                                shell=False,
                                bufsize=-1,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE)
        (output, error) = proc.communicate()
        self.results = {"output": output, 
                       "error": error, "returncode": proc.returncode}
        return self.results

    def pathIsRepo(self, aPath):
        """Returns True if the path is in a Git repo, false otherwise."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['status', aPath])
        return self.results['returncode'] == 0

    def commitFileAtPathForCommitter(self, aPath, committer):
        """Commits the file at 'aPath'. This method will also automatically
        generate the commit log appropriate for the status of aPath where status
        would be 'modified', 'new file', or 'deleted'"""
        print "Doing git commit"
        self.__chdirToMatchPath(aPath)
        # get the author information
        author_name = committer.first_name + ' ' + committer.last_name
        author_name = author_name if author_name != ' ' else committer.username
        author_email = (committer.email or 
                        "%s@%s" % (committer.username, APPNAME))
        author_info = '%s <%s>' % (author_name, author_email)

        # get the status of the file at aPath
        statusResults = self.runGit(['status', aPath])
        statusOutput = statusResults['output']
        if statusOutput.find("new file:") != -1:
            action = 'created'
        elif statusOutput.find("modified:") != -1:
            action = 'modified'
        elif statusOutput.find("deleted:") != -1:
            action = 'deleted'
        else:
            action = 'did something with'

        # determine the path relative to REPO_DIR for the file at aPath
        itempath = aPath
        if aPath.startswith(REPO_DIR):
            itempath = aPath[len(REPO_DIR)+1:]

        # generate the log message
        log_msg = ('%s %s \'%s\' via %s'
                  % (author_name, action, itempath, APPNAME))
        self.runGit(['commit', '-m', log_msg, '--author', author_info])
        if self.results['returncode'] != 0:
            print "Failed to commit changes to %s" % aPath
            print self.results['error']
            return -1
        return 0

    def addFileAtPathForCommitter(self, aPath, aCommitter):
        """Commits a file to the Git repo."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['add', aPath])
        if self.results['returncode'] == 0:
            self.commitFileAtPathForCommitter(aPath, aCommitter)
        else:
            print "Git error: %s" % self.results['error']

    def deleteFileAtPathForCommitter(self, aPath, aCommitter):
        """Deletes a file from the filesystem and Git repo."""
        self.__chdirToMatchPath(aPath)
        self.runGit(['rm', aPath])
        if self.results['returncode'] == 0:
            self.commitFileAtPathForCommitter(aPath, aCommitter)
        else:
            print "Git error: %s" % self.results['error']
