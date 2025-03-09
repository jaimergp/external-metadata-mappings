from packageurl import PackageURL


def test_parse():
    pkg = PackageURL.from_string("pkg:pypi/requests@>=2.0")
    # Current packageurl-python (0.16.0) does not
    # complain about operators in versions :)
    assert pkg.type == "pypi"
    assert pkg.name == "requests"
    assert pkg.version == ">=2.0"
