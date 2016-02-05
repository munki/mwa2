"""
pkgsinfo/models.py
"""

from django.db import models
import os
import logging
import plistlib
from collections import defaultdict
from distutils.version import LooseVersion
from multiprocessing.pool import ThreadPool
from xml.parsers.expat import ExpatError

from django.conf import settings
from process.utils import record_status
from munkiwebadmin.utils import MunkiGit
from catalogs.models import Catalog

try:
    GIT = settings.GIT_PATH
except AttributeError:
    GIT = None

REPO_DIR = settings.MUNKI_REPO_DIR
CATALOGS_PATH = os.path.join(REPO_DIR, 'catalogs')
PKGSINFO_PATH = os.path.join(REPO_DIR, 'pkgsinfo')
PKGSINFO_PATH_PREFIX_LEN = len(PKGSINFO_PATH) + 1
PKGSINFO_STATUS_TAG = 'pkgsinfo_list_process'

LOGGER = logging.getLogger('munkiwebadmin')


def pkg_ref_count(pkginfo_path, catalog_items):
    '''Returns the number of pkginfo items containing a reference to
    the installer_item_location in pkginfo_path'''
    filepath = os.path.join(PKGSINFO_PATH, pkginfo_path)
    try:
        plistdata = plistlib.readPlist(filepath)
    except (ExpatError, IOError):
        return 0
    pkg_path = plistdata.get('installer_item_location')
    if not pkg_path:
        return 0
    matching_count = 0
    if catalog_items:
        matches = [item for item in catalog_items
                   if item.get('installer_item_location') == pkg_path]
        matching_count = len(matches)
    return matching_count


def process_file(filepath):
    '''Worker function called by our multiprocessing pool. Reads a pkginfo
    file and returns a tuple of name, version, catalogs, and relative path'''
    try:
        pkginfo = plistlib.readPlist(filepath)
    except (ExpatError, IOError):
        return ()
    return (pkginfo.get('name', 'NO_NAME'),
            pkginfo.get('version', 'NO_VERSION'),
            pkginfo.get('catalogs', []),
            filepath[PKGSINFO_PATH_PREFIX_LEN:])


def any_files_in_list_newer_than(files, filepath):
    '''Returns true if any file in the list of files
    is newer that filepath'''
    try:
        mtime = os.stat(filepath).st_mtime
    except OSError:
        return True
    for fname in files:
        if os.stat(fname).st_mtime > mtime:
            return True
    return False


def record(message=None, percent_done=None):
    '''Record a status message for a long-running process'''
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
        '''Returns a list of items'''
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
        if any_files_in_list_newer_than(files, all_catalog):
            LOGGER.debug('files newer than all catalog')
            use_slower_approach = True
        else:
            all_items = plistlib.readPlist(all_catalog)
            if len(all_items) != len(files):
                LOGGER.debug('number of files differ from all catalog')
                use_slower_approach = True
        pkginfo_dict = defaultdict(list)
        record(message='Assembling pkgsinfo data')
        if use_slower_approach:
            LOGGER.debug("using slower approach")
            # read the individual pkgsinfo files but use four threads
            # to speed things up a bit since we wait a lot for I/O
            pool = ThreadPool(processes=4)
            tuples = pool.map(process_file, files)
            for name, version, catalogs, pathname in tuples:
                pkginfo_dict[name].append((version, catalogs, pathname))
        else:
            LOGGER.debug("using faster approach")
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
        LOGGER.debug('Sorted pkgsinfo dict')

        # now convert to a list of lists
        pkginfo_list = []
        for key, value in pkginfo_dict.items():
            pkginfo_list.append([key, value])
        LOGGER.debug('Converted to tuple')
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
        except ExpatError:
            # just read and return the raw text
            try:
                with open(filepath) as fileref:
                    pkginfo = fileref.read().decode('utf-8')
                return pkginfo
            except IOError:
                return None

    @classmethod
    def search(cls, search_dict):
        '''Not implemented'''
        pass

    @classmethod
    def write(cls, data, pathname, user):
        '''Writes a pkginfo file'''
        pkgsinfo_path = os.path.join(REPO_DIR, 'pkgsinfo')
        filepath = os.path.join(pkgsinfo_path, pathname)
        try:
            with open(filepath, 'w') as fileref:
                fileref.write(data)
            LOGGER.info('Wrote %s', pathname)
            if GIT:
                MunkiGit().add_file_at_path(filepath, user)
        except Exception, err:
            LOGGER.error('Write failed for %s: %s', pathname, err)
            raise PkginfoWriteError(err)

    @classmethod
    def delete(cls, pathname, user, delete_pkg=False):
        '''Deletes a pkginfo file and optionally the installer item'''
        filepath = os.path.join(PKGSINFO_PATH, pathname)
        if delete_pkg:
            pkgs_path = os.path.join(REPO_DIR, 'pkgs')
            try:
                pkginfo = plistlib.readPlist(filepath)
                install_item_path = pkginfo.get('installer_item_location')
                if install_item_path:
                    pkg_path = os.path.join(pkgs_path, install_item_path)
                    if os.path.exists(pkg_path):
                        LOGGER.info("Deleting %s", pkg_path)
                        os.unlink(pkg_path)
                        # unlikely the large pkgs are under direct git control
                        #if GIT:
                        #    MunkiGit().delete_file_at_path(
                        #        pkg_path, user)
            except (ExpatError, IOError), err:
                LOGGER.error('Delete failed for %s: %s', install_item_path, err)
                raise PkginfoDeleteError(err)
        try:
            LOGGER.info("Deleting %s", filepath)
            os.unlink(filepath)
            if GIT:
                MunkiGit().delete_file_at_path(
                    filepath, user)
        except Exception, err:
            LOGGER.error('Delete failed for %s: %s', pathname, err)
            raise PkginfoDeleteError(err)

    @classmethod
    def mass_delete(cls, pathname_list, user, delete_pkg=False):
        '''Deletes pkginfo files from a list and optionally deletes the
        associated installer items (pkgs)'''
        errors = []
        catalog_items = []
        if delete_pkg:
            # cache the catalog_items once; we don't want to incur the
            # overhead of reading the 'all' catalog multiple times
            catalog_items = Catalog.detail('all')

        for pathname in pathname_list:
            if delete_pkg and pkg_ref_count(pathname, catalog_items) == 1:
                # OK to delete the pkg if there is only one pkginfo
                # file that refers to it
                delete_this_pkg = True
            else:
                delete_this_pkg = False
            try:
                cls.delete(pathname, user, delete_this_pkg)
            except PkginfoDeleteError, err:
                errors.append('Error %s when removing %s' % (err, pathname))

        if errors:
            raise PkginfoDeleteError(errors)

    @classmethod
    def mass_edit_catalogs(
            cls, pathname_list, catalogs_to_add, catalogs_to_remove, user):
        '''For all pkginfo items in the list, add and remove catalogs'''

        errors = []
        # normalize the catalog lists -- no duplicates; eliminate
        # any items that are in both lists
        normalized_catalogs_to_add = (
            set(catalogs_to_add) - set(catalogs_to_remove))
        normalized_catalogs_to_remove = (
            set(catalogs_to_remove)- set(catalogs_to_add))
        catalogs_to_add = list(normalized_catalogs_to_add)
        catalogs_to_remove = list(normalized_catalogs_to_remove)

        for pathname in pathname_list:
            filepath = os.path.join(PKGSINFO_PATH, pathname)
            try:
                plistdata = plistlib.readPlist(filepath)
            except (ExpatError, IOError):
                errors.append('Could not read %s' % pathname)
                continue
            if not 'catalogs' in plistdata:
                plistdata['catalogs'] = []
            # what will be added?
            new_catalogs = [item for item in catalogs_to_add
                            if item not in plistdata['catalogs']]
            # what will be removed?
            removed_catalogs = [item for item in catalogs_to_remove
                                if item in plistdata['catalogs']]
            if new_catalogs or removed_catalogs:
                # add the new ones
                plistdata['catalogs'].extend(new_catalogs)
                # remove catalogs to remove
                plistdata['catalogs'] = [item for item in plistdata['catalogs']
                                         if item not in catalogs_to_remove]
                try:
                    plistlib.writePlist(plistdata, filepath)
                    LOGGER.info("Updated %s", pathname)
                    if GIT:
                        MunkiGit().add_file_at_path(filepath, user)
                except IOError, err:
                    LOGGER.error('Update failed for %s: %s', pathname, err)
                    errors.append('Error %s when updating %s' % (err, pathname))
                    continue

        if errors:
            raise PkginfoWriteError(errors)
