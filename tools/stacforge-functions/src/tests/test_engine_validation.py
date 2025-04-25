from pytest import raises

from stacforge.engine import TemplateValidationErrorType, validate_template

from .utils import get_template


def test_valid_template() -> None:
    template = get_template("valid_stac.j2")

    valid, errors = validate_template(template)

    assert valid
    assert not errors


def test_referenced_template() -> None:
    template = get_template("reference.j2")

    valid, errors = validate_template(template)

    assert not valid
    assert len(errors) == 3
    assert errors[0].type == TemplateValidationErrorType.UNSUPPORTED_REFERENCE
    assert "base_template" in errors[0].message
    assert errors[1].type == TemplateValidationErrorType.UNSUPPORTED_REFERENCE
    assert "some_import" in errors[1].message
    assert errors[2].type == TemplateValidationErrorType.UNSUPPORTED_REFERENCE
    assert "some_include" in errors[2].message


def test_syntax_error_template() -> None:
    template = get_template("syntax_error.j2")

    valid, errors = validate_template(template)

    assert not valid
    assert len(errors) == 1
    assert errors[0].type == TemplateValidationErrorType.SYNTAX_ERROR
    assert errors[0].lineno == 61


def test_undeclared_vars_template() -> None:
    template = get_template("undeclared_vars.j2")

    valid, errors = validate_template(template)

    assert not valid
    assert len(errors) == 2

    # Ensure errors are sorted by line number
    errors.sort(key=lambda x: x.lineno if x.lineno else 0)

    assert errors[0].type == TemplateValidationErrorType.UNDECLARED_VARIABLE
    assert "foo" in errors[0].message
    assert errors[0].lineno == 43
    assert errors[1].type == TemplateValidationErrorType.UNDECLARED_VARIABLE
    assert "bar" in errors[1].message
    assert errors[1].lineno == 44


def test_validation_with_execution() -> None:
    template = get_template("valid_stac.j2")

    with raises(NotImplementedError):
        validate_template(template, scene_info="foo")
