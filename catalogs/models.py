"""
catalogs/models.py

"""
#from django.db import models
import os
import plistlib
from xml.parsers.expat import ExpatError

from django.conf import settings

REPO_DIR = settings.MUNKI_REPO_DIR


def trim_version_string(version_string):
    ### from munkilib.updatecheck
    """Trims all lone trailing zeros in the version string after major/minor.

    Examples:
      10.0.0.0 -> 10.0
      10.0.0.1 -> 10.0.0.1
      10.0.0-abc1 -> 10.0.0-abc1
      10.0.0-abc1.0 -> 10.0.0-abc1
    """
    if version_string == None or version_string == '':
        return ''
    version_parts = version_string.split('.')
    # strip off all trailing 0's in the version, while over 2 parts.
    while len(version_parts) > 2 and version_parts[-1] == '0':
        del version_parts[-1]
    return '.'.join(version_parts)


class Catalog(object):
    '''Not really a Django object, but a useful substitute'''
    @classmethod
    def list(cls):
        '''Returns a list of available catalogs, which is a list
        of catalog names (strings)'''
        catalogs_path = os.path.join(REPO_DIR, 'catalogs')
        catalogs = []
        for name in os.listdir(catalogs_path):
            if name.startswith("._") or name == ".DS_Store" or name == 'all':
                # don't process these
                continue
            try:
                # attempt to read the plist so we know it's valid
                _ = plistlib.readPlist(
                    os.path.join(catalogs_path, name))
            except (ExpatError, IOError):
                # skip items that aren't valid plists
                pass
            else:
                catalogs.append(name)
        return catalogs

    @classmethod
    def next_catalog_contents(cls):
        '''Generator that returns the next catalog name and its contents'''
        catalogs_path = os.path.join(REPO_DIR, 'catalogs')
        for name in os.listdir(catalogs_path):
            if name.startswith("._") or name == ".DS_Store" or name == 'all':
                # don't process these
                continue
            try:
                catalog = plistlib.readPlist(
                    os.path.join(catalogs_path, name))
            except (ExpatError, IOError):
                # skip items that aren't valid plists
                pass
            else:
                yield (name, catalog)

    @classmethod
    def detail(cls, catalog_name):
        '''Gets the contents of a catalog, which is a list
        of pkginfo items'''
        catalog_path = os.path.join(
            REPO_DIR, 'catalogs', catalog_name)
        if os.path.exists(catalog_path):
            try:
                catalog_items = plistlib.readPlist(catalog_path)
                return catalog_items
            except (ExpatError, IOError):
                return None
        else:
            return None

    @classmethod
    def catalog_info(cls):
        '''Returns a dictionary containing types of install items
        used by autocomplete and manifest validation'''
        catalog_info = {}
        categories_set = set()
        developers_set = set()
        for catalog, catalog_items in cls.next_catalog_contents():
            suggested_set = set()
            update_set = set()
            versioned_set = set()
            if catalog_items:
                suggested_names = list(set(
                    [item['name'] for item in catalog_items
                     if not item.get('update_for')]))
                suggested_set.update(suggested_names)
                update_names = list(set(
                    [item['name'] for item in catalog_items
                     if item.get('update_for')]))
                update_set.update(update_names)
                item_names_with_versions = list(set(
                    [item['name'] + '-' +
                     trim_version_string(item['version'])
                     for item in catalog_items]))
                versioned_set.update(item_names_with_versions)
                catalog_info[catalog] = {}
                catalog_info[catalog]['suggested'] = list(suggested_set)
                catalog_info[catalog]['updates'] = list(update_set)
                catalog_info[catalog]['with_version'] = list(versioned_set)
                categories_set.update(
                    {item['category'] for item in catalog_items
                     if item.get('category')})
                developers_set.update(
                    {item['developer'] for item in catalog_items
                     if item.get('developer')})
        catalog_info['._categories'] = list(categories_set)
        catalog_info['._developers'] = list(developers_set)
        return catalog_info

    @classmethod
    def get_pkg_ref_count(cls, pkg_path):
        '''Returns the number of pkginfo items containing a reference to
        pkg_path'''
        matching_count = 0
        catalog_items = Catalog.detail('all')
        if catalog_items:
            matches = [item for item in catalog_items
                       if item.get('installer_item_location') == pkg_path]
            matching_count = len(matches)
        return matching_count
                     