from unittest.mock import ANY


def _assert(actual, expected, key):
    expected_value = expected[key]
    actual_value = actual[key]
    if expected_value == ANY:
        return

    if isinstance(expected_value, dict) and isinstance(actual_value, dict):
        assert_equals_dicts(expected_value, actual_value)
    elif isinstance(expected_value, list) and isinstance(actual_value, list):
        assert_equals_lists(expected_value, actual_value)
    else:
        assert expected_value == actual_value, f"Values for key '{key}' do not match"


def assert_equals_dicts(expected, actual):
    assert isinstance(actual, dict), "Expected a dictionary for actual value"
    assert isinstance(expected, dict), "Expected a dictionary for expected value"

    expected_keys = expected.keys()
    actual_keys = actual.keys()
    _expected_keys = set(expected_keys)
    _actual_keys = set(actual_keys)
    assert _actual_keys == _expected_keys, ("Keys in dictionaries do not match", _actual_keys, _expected_keys)
    assert actual_keys == expected_keys, "Keys in dictionaries do not match"
    for key in expected:
        _assert(actual, expected, key)


def assert_equals_lists(expected, actual):
    assert isinstance(actual, list), "Expected a list for actual value"
    assert isinstance(expected, list), "Expected a list for expected value"

    assert len(actual) == len(expected), "Lists have different lengths"

    for i in range(len(expected)):
        _assert(actual, expected, i)
