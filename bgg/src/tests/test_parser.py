import pytest

from data import parsePlayHistory

def test_url_builder_empty():
    """
    default url builder does not have a base url, and the builder won't produce a url without a base
    base url can be set after object creation
    """
    builder = parsePlayHistory.URLBuilder()
    assert builder.baseURL == ""
    with pytest.raises(ValueError):
        builder.build()
    builder.baseURL = "www.example.com"
    assert builder.build() == "www.example.com"

def test_url_builder_qargs():
    """
    if an argument is provided without a value, it is not inlcuded in the final url
    an argument that is set multiple times, will only include the last value
    """
    builder = parsePlayHistory.URLBuilder("www.example.com")
    builder.addQueryArg("foo", 1)
    builder.addQueryArg("bar", "2")
    builder.addQueryArg("bar", 5)\
        .addQueryArg("bar", "6")
    builder.addQueryArg("baz", None)
    final = builder.build()
    assert final.find("baz") == -1
    assert final[final.find("bar") + 4] == "6"
    assert final[final.find("foo") + 4] == "1"