import logging
from enum import Enum
from typing import Optional

from jinja2 import TemplateSyntaxError
from jinja2.exceptions import SecurityError
from jinja2.meta import find_referenced_templates, find_undeclared_variables
from jinja2.nodes import Assign, Name

from stacforge.engine.environment import Environment
from stacforge.logging import LOGGER_NAME

_logger = logging.getLogger(LOGGER_NAME)


class TemplateValidationErrorType(str, Enum):
    """Types of errors that can be found in a template."""

    SECURITY_ERROR = "SecurityError"
    SYNTAX_ERROR = "SyntaxError"
    UNDECLARED_VARIABLE = "UndeclaredVariable"
    UNSUPPORTED_REFERENCE = "UnsupportedReference"


class TemplateValidationError:
    """A validation error found in a template."""

    def __init__(
        self,
        type: TemplateValidationErrorType,
        message: str,
        lineno: Optional[int] = None,
    ):
        self.type = type
        self.message = message
        self.lineno = lineno


EXPECTED_VARS = ["scene_info"]
"""List of global variables expected in a GeoTemplate environment."""


def validate_template(
    template: str,
    scene_info: Optional[str] = None,
) -> tuple[bool, list[TemplateValidationError]]:
    """Validate a GeoTemplate."""

    if scene_info:
        _logger.warning("Template execution is not yet supported")
        raise NotImplementedError("Template execution is not yet supported")

    environment = Environment()
    # Add the list of expected vars to the environment
    for var in EXPECTED_VARS:
        environment.add_global_variable(var, None)

    errors: list[TemplateValidationError] = []

    try:
        # Parse the template to find syntax errors
        ast = environment.parse_template(template)
        undeclared_variables = find_undeclared_variables(ast)
        referenced_templates = find_referenced_templates(ast)

        # Look for undeclared variables
        _logger.debug("Looking for undeclared variables")
        for var in undeclared_variables:
            undeclared = True
            # Ensure the variable isn't declared elsewhere in the template
            for assign_node in ast.find_all(node_type=type(Assign())):
                if isinstance(assign_node.target, Name):
                    if assign_node.target.name == var:
                        undeclared = False
                        break

            if undeclared:
                error = TemplateValidationError(
                    type=TemplateValidationErrorType.UNDECLARED_VARIABLE,
                    message=f"Found undeclared variable '{var}'",
                )

                # Find the line number of the undeclared variable
                for name_node in ast.find_all(node_type=type(Name())):
                    if isinstance(name_node, Name):
                        if name_node.name == var:
                            error.lineno = name_node.lineno
                            break

                _logger.warning(
                    error.message + f" at line {error.lineno}" if error.lineno else ""
                )
                errors.append(error)

        # Look for imported and included templates
        for tpl in referenced_templates:
            error = TemplateValidationError(
                type=TemplateValidationErrorType.UNSUPPORTED_REFERENCE,
                message=(
                    f"Found unsupported referenced template '{tpl}'"
                    if tpl is not None
                    else "Found unsupported dynamically referenced template"
                ),
            )
            _logger.warning(error.message)
            errors.append(error)
    except TemplateSyntaxError as e:
        error = TemplateValidationError(
            type=TemplateValidationErrorType.SYNTAX_ERROR,
            message=e.message if e.message else "Syntax error detected",
            lineno=e.lineno,
        )

        _logger.warning(error.message + f" at line {error.lineno}")
        errors.append(error)
        # No security errors are thrown while parsing the template
        # This is here for future execution validation
    except SecurityError as e:
        error = TemplateValidationError(
            type=TemplateValidationErrorType.SECURITY_ERROR,
            message=e.message if e.message else "Security error detected",
        )
        _logger.warning(error.message)
        errors.append(error)

    valid = len(errors) == 0
    if valid:
        _logger.info("Template is valid")
    else:
        _logger.warning(f"Template is invalid: {len(errors)} errors found")
    return valid, errors
