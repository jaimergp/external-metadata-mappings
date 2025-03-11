import pytest
from packageurl import PackageURL
from univers.version_range import PypiVersionRange
from univers.versions import PypiVersion


@pytest.mark.parametrize(
    "url",
    [
        "pkg:pypi/requests@>=2.0",
        "pkg:pypi/requests@2.0",
    ],
)
def test_parse(url):
    pkg = PackageURL.from_string(url)
    # Current packageurl-python (0.16.0) does not
    # complain about operators in versions :)
    assert pkg.type == "pypi"
    assert pkg.name == "requests"
    assert pkg.version == url.split("@")[-1]
    if pkg.version[0].isdigit():
        PypiVersion.build_value(pkg.version)
    else:
        PypiVersionRange.from_native(pkg.version)
