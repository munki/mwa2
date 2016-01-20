from django.db import models
import os
import plistlib
from collections import defaultdict
from distutils.version import LooseVersion
#from multiprocessing import Pool
from multiprocessing.pool import ThreadPool

from django.conf import settings
from process.utils import record_status
from munkiwebadmin.utils import MunkiGit

try:
    GIT = settings.GIT_PATH
except:
    GIT = None

REPO_DIR = settings.MUNKI_REPO_DIR
CATALOGS_PATH = os.path.join(REPO_DIR, 'catalogs')
PKGSINFO_PATH = os.path.join(REPO_DIR, 'pkgsinfo')
PKGSINFO_PATH_PREFIX_LEN = len(PKGSINFO_PATH) + 1
PKGSINFO_STATUS_TAG = 'pkgsinfo_list_process'


def process_file(filepath):
    '''Worker function called by our multiprocessing pool. Reads a pkginfo
    file and returns a tuple of name, version, catalogs, and relative path'''
    try:
        pkginfo = plistlib.readPlist(filepath)
    except:
        return ()
    return (pkginfo.get('name', 'NO_NAME'),
            pkginfo.get('version', 'NO_VERSION'),
            pkginfo.get('catalogs', []),
            filepath[PKGSINFO_PATH_PREFIX_LEN:])


def anyFilesInList_newerThan_(files, filepath):
    try:
        mtime = os.stat(filepath).st_mtime
    except OSError:
        return True
    for fname in files:
        if os.stat(fname).st_mtime > mtime:
            return True
    return False


def record(message=None, percent_done=None):
    record_status(
        PKGSINFO_STATUS_TAG, message=message, percent_done=percent_done)


class PkginfoError(Exception):
    '''Class for Pkginfo errors'''
    pass


class PkginfoReadError(PkginfoError):
    '''Error reading a Pkginfo'''
    pass


class PkginfoWriteError(PkginfoError):
    '''Error writing a Pkginfo'''
    pass


class PkginfoDeleteError(PkginfoError):
    '''Error deleting a Pkginfo'''
    pass


class PkginfoDoesNotExistError(PkginfoError):
    '''Error when Pkginfo doesn't exist at pathname'''
    pass


class PkginfoFile(models.Model):
    '''Placeholder so we get permissions entries in the admin database'''
    pass


class Pkginfo(object):
    '''Models pkginfo items'''
    @classmethod
    def _list(cls):
        files = []
        rootdir = PKGSINFO_PATH.rstrip(os.sep)
        for dirpath, dirnames, filenames in os.walk(rootdir, followlinks=True):
            record(message='Scanning %s' % dirpath[PKGSINFO_PATH_PREFIX_LEN:])
            for dirname in dirnames:
                # don't recurse into directories that start with a period.
                if dirname.startswith('.'):
                    dirnames.remove(dirname)
            files.extend(
                [os.path.join(dirpath, filename)
                 for filename in filenames if not filename.startswith('.')])
        return files


    @classmethod
    def list(cls):
        '''Returns a dict with itemnames, versions, and filepaths'''
        def compare_versions(a, b):
            """Internal comparison function for use in sorting"""
            return cmp(LooseVersion(b[0]), LooseVersion(a[0]))
        record(message='Starting scan of pkgsinfo data')
        files = cls._list()
        record(message='Processing %s files' % len(files))
        all_catalog = os.path.join(CATALOGS_PATH, 'all')
        use_slower_approach = False
        if anyFilesInList_newerThan_(files, all_catalog):
            print 'files newer than all catalog'
            use_slower_approach = True
        else:
            all_items = plistlib.readPlist(all_catalog)
            if len(all_items) != len(files):
                print 'number of files differ from all catalog'
                use_slower_approach = True
        pkginfo_dict = defaultdict(list)
        record(message='Assembling pkgsinfo data')
        if use_slower_approach:
            print "using slower approach"
            # read the individual pkgsinfo files but use four threads
            # to speed things up a bit since we wait a lot for I/O
            pool = ThreadPool(processes=4)
            tuples = pool.map(process_file, files)
            for name, version, catalogs, pathname in tuples:
                pkginfo_dict[name].append((version, catalogs, pathname))
        else:
            print "using faster approach"
            # use the data in the all catalog; one file read instead
            # of hundreds or thousands
            for index, item in enumerate(all_items):
                name = item.get('name', 'NO_NAME')
                version = item.get('version', 'NO_VERSION')
                catalogs = item.get('catalogs', [])
                pathname = files[index][PKGSINFO_PATH_PREFIX_LEN:]
                pkginfo_dict[name].append((version, catalogs, pathname))
        for key in pkginfo_dict.keys():
            pkginfo_dict[key].sort(compare_versions)
        print 'Sorted pkgsinfo dict'

        # now convert to a list of lists
        pkginfo_list = []
        for key, value in pkginfo_dict.items():
            pkginfo_list.append([key, value])
        print 'Converted to tuple'
        record(message='Completed assembly of pkgsinfo data')
        return pkginfo_list


    @classmethod
    def read(cls, pathname):
        '''Reads a pkginfo file and returns the plist as text data'''
        pkgsinfo_path = os.path.join(REPO_DIR, 'pkgsinfo')
        filepath = os.path.join(pkgsinfo_path, pathname)
        default_items = {
            'display_name': '',
            'description': '',
            'category': '',
            'developer': '',
            'unattended_install': False,
            'unattended_uninstall': False,
        }
        try:
            plistdata = plistlib.readPlist(filepath)
            # define default fields for easier editing
            for item in default_items:
                if not item in plistdata:
                    plistdata[item] = default_items[item]
            return plistlib.writePlistToString(plistdata)
        except:
            # just read and return the raw text
            try:
                with open(filepath) as FILEREF:
                    pkginfo = FILEREF.read().decode('utf-8')
                return pkginfo
            except:
                return None

    @classmethod
    def search(cls, search_dict):
        pass

    @classmethod
    def write(cls, data, pathname, user):
        '''Writes a pkginfo file'''
        pkgsinfo_path = os.path.join(REPO_DIR, 'pkgsinfo')
        filepath = os.path.join(pkgsinfo_path, pathname)
        try:
            with open(filepath, 'w') as FILEREF:
                FILEREF.write(data.encode('utf-8'))
            print 'Wrote %s' % pathname
            if GIT:
                MunkiGit().addFileAtPathForCommitter(filepath, user)
        except Exception, err:
            raise PkginfoWriteError(err)

    @classmethod
    def delete(cls, pathname, user, delete_pkg=False):
        '''Deletes a pkginfo file and optionally the installer item'''
        pkgsinfo_path = os.path.join(REPO_DIR, 'pkgsinfo')
        filepath = os.path.join(pkgsinfo_path, pathname)
        if delete_pkg:
            pkgs_path = os.path.join(REPO_DIR, 'pkgs')
            try:
                pkginfo = plistlib.readPlist(filepath)
                install_item_path = pkginfo.get('installer_item_location')
                if install_item_path:
                    pkg_path = os.path.join(pkgs_path, install_item_path)
                    if os.path.exists(pkg_path):
                        os.unlink(pkg_path)
            except Exception, err:
                raise PkginfoDeleteError(err)
        try:
            os.unlink(filepath)
            if GIT:
                MunkiGit().deleteFileAtPathForCommitter(
                    filepath, user)
        except Exception, err:
            raise PkginfoDeleteError(err)
