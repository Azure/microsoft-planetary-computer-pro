from pytest import mark

from stacforge.engine.tests import GeoTemplateTests, contains, ends_with, starts_with


@mark.parametrize(
    "test_name",
    [
        "contains",
        "ends_with",
        "starts_with",
    ],
)
def test_test_registration(test_name: str) -> None:
    assert test_name in GeoTemplateTests


def test_starts_with_test() -> None:
    assert starts_with("Hello, World!", "Hello")
    assert not starts_with("Hello, World!", "World")


def test_ends_with_test() -> None:
    assert ends_with("Hello, World!", "World!")
    assert not ends_with("Hello, World!", "Hello")


def test_contains_test() -> None:
    assert contains("Hello, World!", "Hello")
    assert not contains("Hello, World!", "Goodbye")
