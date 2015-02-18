import pytest

from data import app

def test_arg_parser_keeps_all_pairs():
    assert app.parseArgs("key1=value1&key2=value2&key3=value3&key4=value4") == {
        "key1":"value1", 
        "key2":"value2",
        "key3":"value3",
        "key4":"value4"}
    assert app.parseArgs("statement&statement&key=value") == {"key":"value"}
    assert app.parseArgs("statement&statement&key=value&key=value2") == {"key":"value2"}