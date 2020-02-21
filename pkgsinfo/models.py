"""
pkgsinfo/models.py
"""

from __future__ import absolute_import
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
from catalogs.models import Catalog
from api.models import Plist, MunkiFile, \
                       FileReadError, FileWriteError, FileDeleteError


REPO_DIR = settings.MUNKI_REPO_DIR
CATALOGS_PATH = os.path.join(REPO_DIR, 'catalogs')
PKGSINFO_PATH = os.path.join(REPO_DIR, 'pkgsinfo')
PKGSINFO_PATH_PREFIX_LEN = len(PKGSINFO_PATH) + 1
PKGSINFO_STATUS_TAG = 'pkgsinfo_list_process'

LOGGER = logging.getLogger('munkiwebadmin')


def pkg_ref_count(pkginfo_path, catalog_items):
    '''Returns the number of pkginfo items containing a reference to
    the installer_item_location in pkginfo_path and the relative path to
    the installer_item_location'''
    filepath = os.path.join(PKGSINFO_PATH, os.path.normpath(pkginfo_path))
    try:
        plistdata = plistlib.readPlist(filepath)
    except (ExpatError, IOError):
        return 0, ''
    pkg_path = plistdata.get('installer_item_location')
    if not pkg_path:
        return 0, ''
    matching_count = 0
    if catalog_items:
        matches = [item for item in catalog_items
                   if item.get('installer_item_location') == pkg_path]
        matching_count = len(matches)
    return matching_count, pkg_path


def process_file(pkginfo_path):
    '''Worker function called by our multiprocessing pool. Reads a pkginfo
    file and returns a tuple of name, version, catalogs, and relative path'''
    filepath = os.path.join(PKGSINFO_PATH, os.path.normpath(pkginfo_path))
    try:
        pkginfo = plistlib.readPlist(filepath)
    except (ExpatError, IOError):
        return ()
    return (pkginfo.get('name', 'NO_NAME'),
            pkginfo.get('version', 'NO_VERSION'),
            pkginfo.get('catalogs', []),
            pkginfo_path)


def any_files_in_list_newer_than(files, filepath):
    '''Returns true if any file in the list of files
    is newer that filepath'''
    try:
        mtime = os.stat(filepath).st_mtime
    except OSError:
        return True
    for fname in files:
        fullpath = os.path.join(PKGSINFO_PATH, fname)
        if os.stat(fullpath).st_mtime > mtime:
            return True
    return False


def record(message=None, percent_done=None):
    '''Record a status message for a long-running process'''
    record_status(
        PKGSINFO_STATUS_TAG, message=message, percent_done=percent_done)


class PkginfoFile(models.Model):
    '''Placeholder so we get permissions entries in the admin database'''
    pass


class Pkginfo(Plist):
    '''Models pkginfo items'''
    @classmethod
    def data(cls):
        '''Returns a structure with itemnames, versions, and filepaths'''
        def compare_versions(a, b):
            """Internal comparison function for use in sorting"""
            return cmp(LooseVersion(b[0]), LooseVersion(a[0]))
        record(message='Starting scan of pkgsinfo data')
        files = cls.list('pkgsinfo')
        record(message='Processing %s files' % len(files))
        all_catalog = os.path.join(CATALOGS_PATH, 'all')
        try:
            all_items = plistlib.readPlist(all_catalog)
        except (ExpatError, OSError, IOError):
            all_items = []
        use_slower_approach = False
        if len(all_items) != len(files):
            LOGGER.debug('number of files differ from all catalog')
            use_slower_approach = True
        elif any_files_in_list_newer_than(files, all_catalog):
            LOGGER.debug('files newer than all catalog')
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
                pathname = files[index]
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
    def mass_delete(cls, pathname_list, user, delete_pkgs=False):
        '''Deletes pkginfo files from a list and optionally deletes the
        associated installer items (pkgs)'''
        errors = []
        catalog_items = []
        if delete_pkgs:
            # cache the catalog_items once; we don't want to incur the
            # overhead of reading the 'all' catalog multiple times
            catalog_items = Catalog.detail('all')

        for pathname in pathname_list:
            delete_this_pkg = False
            if delete_pkgs:
                ref_count, pkg_path = pkg_ref_count(pathname, catalog_items)
                if ref_count == 1:
                    # OK to delete the pkg if there is only one pkginfo
                    # file that refers to it
                    delete_this_pkg = True
            try:
                cls.delete('pkgsinfo', pathname, user)
            except FileDeleteError as err:
                errors.append('Error %s when removing %s' % (err, pathname))
            else:
                if delete_this_pkg:
                    try:
                        MunkiFile.delete('pkgs', pkg_path, user)
                    except FileDeleteError as err:
                        errors.append('Error %s when removing %s'
                                      % (err, pkg_path))
        if errors:
            raise FileDeleteError(errors)

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
            try:
                plist = cls.read('pkgsinfo', pathname)
            except FileReadError:
                errors.append('Could not read %s' % pathname)
                continue
            if not 'catalogs' in plist:
                plist['catalogs'] = []
            # what will be added?
            new_catalogs = [item for item in catalogs_to_add
                            if item not in plist['catalogs']]
            # what will be removed?
            removed_catalogs = [item for item in catalogs_to_remove
                                if item in plist['catalogs']]
            if new_catalogs or removed_catalogs:
                # add the new ones
                plist['catalogs'].extend(new_catalogs)
                # remove catalogs to remove
                plist['catalogs'] = [item for item in plist['catalogs']
                                     if item not in catalogs_to_remove]
                data = plistlib.writePlistToString(plist)
                try:
                    cls.write(data, 'pkgsinfo', pathname, user)
                except FileWriteError as err:
                    LOGGER.error('Update failed for %s: %s', pathname, err)
                    errors.append('Error %s when updating %s' % (err, pathname))
                    continue

        if errors:
            raise FileWriteError(errors)
