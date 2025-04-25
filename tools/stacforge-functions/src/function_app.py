import importlib
import logging
import pkgutil

import azure.durable_functions as df  # type: ignore
import azure.functions as func

from stacforge import blueprint

_logger = logging.getLogger()


def force_initialize_package(package_name: str) -> None:
    """
    Force the initialization of a package to ensure that all
    functions are registered.
    """
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.walk_packages(
        package.__path__,
        package.__name__ + ".",
    ):
        importlib.import_module(module_name)


# Create the durable function app
app = df.DFApp()

# Initialize the stacforge package to force the registration of functions
force_initialize_package("stacforge")

# Register the functions in the blueprint
app.register_functions(blueprint)


@app.route("orchestrations/{orchestration}")
@app.durable_client_input(client_name="client")
async def start_orchestration(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """
    Start a new orchestration with the given name.
    """

    orchestration_name = req.route_params["orchestration"]
    _logger.info(f"Request to start orchestration {orchestration_name}")

    # Try to get a JSON payload from the request
    try:
        req_json = req.get_json()
    except ValueError:
        req_json = None

    # Start the orchestration
    instance_id = await client.start_new(
        orchestration_name,
        client_input=req_json,
    )
    if instance_id is None:
        return func.HttpResponse(
            f"Failed to start orchestration {orchestration_name}",
            status_code=500,
        )

    _logger.info(f"Started orchestration {orchestration_name} with ID {instance_id}")

    response = client.create_check_status_response(req, instance_id)
    return response
