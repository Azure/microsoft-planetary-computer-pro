from os import path

BASE_TEMPLATE_DIRECTORY = path.join(
    path.dirname(__file__),
    "data",
    "templates",
)


def get_template(template_name: str) -> str:
    template_file_path = path.join(
        BASE_TEMPLATE_DIRECTORY,
        template_name,
    )
    with open(template_file_path) as file:
        template = file.read()

    return template
