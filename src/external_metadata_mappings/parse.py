"""
Parse dep: dependencies
"""

from packageurl import PackageURL
from univers.versions import PypiVersion
from univers.version_range import PypiVersionRange


class DepURL(PackageURL):
    # TODO: Needs https://github.com/package-url/packageurl-python/pull/184
    SCHEME = "dep"

    def parse_version(self):
        if not self.version:
            return None
        if self.version[0].isdigit():
            return PypiVersion.build_value(self.version)
        return PypiVersionRange.from_native(self.version)
