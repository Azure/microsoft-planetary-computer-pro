import json
import os
from datetime import datetime
from importlib.metadata import version
from io import TextIOWrapper

import click
import psycopg2  # type: ignore
import pystac
from dotenv import load_dotenv  # type: ignore
from pystac import STACTypeError, STACValidationError
from slugify import slugify  # type: ignore
from tqdm import tqdm  # type: ignore

load_dotenv()


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(version("stac-export"))
    ctx.exit()


@click.group()
@click.option(
    "--version",
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
)
def cli():
    """A command line interface for exporting STAC items."""
    ...


@cli.group()
def pgstac():
    """Commands for working with PgSTAC databases."""
    ...


@pgstac.group(name="list")
def pgstac_list():
    """List STAC entities in a PgSTAC database."""
    ...


@pgstac_list.command(name="collections")
@click.option(
    "-h",
    "--host",
    "pgstac_host",
    envvar="PGHOST",
    default="localhost",
    show_default=True,
    help="The host of the PgSTAC database.",
)
@click.option(
    "-p",
    "--port",
    "pgstac_port",
    envvar="PGPORT",
    default=5432,
    show_default=True,
    help="The port of the PgSTAC database.",
)
@click.option(
    "-u",
    "--username",
    "pgstac_username",
    envvar="PGUSER",
    default="postgres",
    show_default=True,
    help="The user of the PgSTAC database.",
)
@click.option(
    "-pw",
    "--password",
    "pgstac_password",
    envvar="PGPASSWORD",
    help="The password of the PgSTAC database.",
    required=True,
    prompt="PgSTAC password",
    hide_input=True,
)
@click.option(
    "-d",
    "--database",
    "pgstac_database",
    envvar="PGDATABASE",
    default="postgres",
    show_default=True,
    help="The name of the PgSTAC database.",
)
@click.option(
    "-l",
    "--limit",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="The maximum number of collections to list. 0 means no limit.",
)
def pgstac_list_collections(
    pgstac_host: str,
    pgstac_port: int,
    pgstac_username: str,
    pgstac_password: str,
    pgstac_database: str,
    limit: int,
):
    """List all the STAC collections in a PgSTAC database."""
    with psycopg2.connect(
        host=pgstac_host,
        port=pgstac_port,
        user=pgstac_username,
        password=pgstac_password,
        database=pgstac_database,
    ) as conn:
        with conn.cursor() as cur:
            cur.itersize = 1000
            query = "SELECT id FROM pgstac.collections ORDER BY id"
            if limit > 0:
                query += " LIMIT %(limit)s"
            cur.execute(
                query,
                {"limit": limit},
            )
            for record in cur.fetchall():
                print(record[0])


@pgstac_list.command(name="items")
@click.option(
    "-h",
    "--host",
    "pgstac_host",
    envvar="PGHOST",
    default="localhost",
    show_default=True,
    help="The host of the PgSTAC database.",
)
@click.option(
    "-p",
    "--port",
    "pgstac_port",
    envvar="PGPORT",
    default=5432,
    show_default=True,
    help="The port of the PgSTAC database.",
)
@click.option(
    "-u",
    "--username",
    "pgstac_username",
    envvar="PGUSER",
    default="postgres",
    show_default=True,
    help="The user of the PgSTAC database.",
)
@click.option(
    "-pw",
    "--password",
    "pgstac_password",
    envvar="PGPASSWORD",
    help="The password of the PgSTAC database.",
    required=True,
    prompt="PgSTAC password",
    hide_input=True,
)
@click.option(
    "-d",
    "--database",
    "pgstac_database",
    envvar="PGDATABASE",
    default="postgres",
    show_default=True,
    help="The name of the PgSTAC database.",
)
@click.option(
    "-c",
    "--collection",
    "collection_id",
    required=True,
    help="The ID of the collection to list.",
)
@click.option(
    "-l",
    "--limit",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="The maximum number of items to list. 0 means no limit.",
)
def pgstac_list_items(
    pgstac_host: str,
    pgstac_port: int,
    pgstac_username: str,
    pgstac_password: str,
    pgstac_database: str,
    collection_id: str,
    limit: int,
):
    """List all the STAC items from a collection in a PgSTAC database."""
    with psycopg2.connect(
        host=pgstac_host,
        port=pgstac_port,
        user=pgstac_username,
        password=pgstac_password,
        database=pgstac_database,
    ) as conn:
        with conn.cursor() as cur:
            cur.itersize = 1000
            query = "SELECT id FROM pgstac.items WHERE collection = %(collection)s ORDER BY id"  # noqa: E501
            if limit > 0:
                query += " LIMIT %(limit)s"
            cur.execute(
                query,
                {
                    "collection": collection_id,
                    "limit": limit,
                },
            )
            for record in cur.fetchall():
                print(record[0])


@pgstac.command(name="export")
@click.option(
    "-h",
    "--host",
    "pgstac_host",
    envvar="PGHOST",
    default="localhost",
    show_default=True,
    help="The host of the PgSTAC database.",
)
@click.option(
    "-p",
    "--port",
    "pgstac_port",
    envvar="PGPORT",
    default=5432,
    show_default=True,
    help="The port of the PgSTAC database.",
)
@click.option(
    "-u",
    "--username",
    "pgstac_username",
    envvar="PGUSER",
    default="postgres",
    show_default=True,
    help="The user of the PgSTAC database.",
)
@click.option(
    "-pw",
    "--password",
    "pgstac_password",
    envvar="PGPASSWORD",
    help="The password of the PgSTAC database.",
    required=True,
    prompt="PgSTAC password",
    hide_input=True,
)
@click.option(
    "-d",
    "--database",
    "pgstac_database",
    envvar="PGDATABASE",
    default="postgres",
    show_default=True,
    help="The name of the PgSTAC database.",
)
@click.option(
    "-c",
    "--collection",
    "collection_id",
    required=True,
    help="The ID of the collection to export.",
)
@click.option(
    "-l",
    "--limit",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="The maximum number of items to export. 0 means no limit.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    help="The path to the output directory.",
)
@click.option(
    "--batch-size",
    "batch_size",
    default=1000,
    show_default=True,
    type=click.IntRange(min=100, max=5000),
    help="The number of items to export in a batch.",
)
@click.option(
    "--validate/--no-validate",
    "validate",
    default=False,
    show_default=True,
    help="Validate the STAC items.",
)
@click.option(
    "--max-items-per-collection",
    "max_items_per_collection",
    default=500000,
    show_default=True,
    type=click.IntRange(min=1, max=1000000),
    help="The maximum number of items per collection. If the number of items is greater than this value, the items will be split into multiple collections.",  # noqa: E501
)
def pgstac_export(
    pgstac_host: str,
    pgstac_port: int,
    pgstac_username: str,
    pgstac_password: str,
    pgstac_database: str,
    collection_id: str,
    limit: int,
    output_path: str,
    batch_size: int,
    validate: bool,
    max_items_per_collection: int,
):
    """Export all the STAC items in a collection from a PgSTAC database."""
    with psycopg2.connect(
        host=pgstac_host,
        port=pgstac_port,
        user=pgstac_username,
        password=pgstac_password,
        database=pgstac_database,
        options="-c statement_timeout=0",
    ) as conn:
        # Get the collection
        with conn.cursor() as col_cur:
            col_cur.execute(
                "SELECT pgstac.get_collection(%(collection)s)",
                {"collection": collection_id},
            )
            (collection,) = col_cur.fetchone()
            if collection is None:
                click.echo(
                    click.style("Collection ", fg="red")
                    + click.style(collection_id, fg="red", bold=True)
                    + click.style(" not found.", fg="red"),
                    err=True,
                )
                exit(1)
            stac_collection = pystac.Collection.from_dict(dict(collection))
            stac_collection.catalog_type = pystac.CatalogType.SELF_CONTAINED
            stac_collection.remove_links("items")

        # Create the output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        # Create the items directory if it doesn't exist
        items_path = os.path.join(output_path, "items")
        os.makedirs(items_path, exist_ok=True)

        # Get the total number of items
        with conn.cursor() as count_cur:
            count_cur.execute(
                "SELECT count(*) FROM pgstac.items WHERE collection = %(collection)s",  # noqa: E501
                {"collection": collection_id},
            )
            (total_items,) = count_cur.fetchone()
            if limit > 0 and total_items > limit:
                total_items = limit

        # Get the items
        assets_href: list[str] = []
        invalid_item_ids: list[str] = []
        items_count = 0
        items_in_collection = 0
        collection_number = 1
        with conn.cursor("stac_items_cursor") as items_cur:
            items_cur.itersize = batch_size
            query = "SELECT id, pgstac.get_item(id, collection) FROM pgstac.items WHERE collection = %(collection)s ORDER BY datetime"  # noqa: E501
            if limit > 0:
                query += " LIMIT %(limit)s"
            items_cur.execute(
                query,
                {
                    "collection": collection_id,
                    "limit": limit,
                },
            )

            with tqdm(
                total=total_items,
                desc="Exporting items",
                unit=" items",
                colour="green",
            ) as progress_bar:
                while True:
                    items = items_cur.fetchmany(batch_size)
                    if not items:
                        break
                    for item_id, item in items:
                        collection_file_name = f"{slugify(collection_id)}_{collection_number}.json"  # noqa: E501
                        progress_bar.update()
                        try:
                            stac_item = pystac.Item.from_dict(item)
                            stac_item.set_parent(None)
                            stac_item.set_root(None)
                            stac_item.remove_links("self")
                            stac_item.remove_links("collection")
                            stac_item.add_link(
                                pystac.Link(
                                    rel="collection",
                                    target=f"../{collection_file_name}",
                                )
                            )

                            if validate:
                                stac_item.validate()

                            # Save the item to a file
                            item_file_name = f"{slugify(item_id)}.json"
                            item_path = os.path.join(items_path, item_file_name)
                            with open(item_path, "w") as item_file:
                                item_file.write(
                                    json.dumps(stac_item.to_dict(), indent=2)
                                )

                            # Add the assets to the assets list
                            for asset in stac_item.assets.values():
                                assets_href.append(asset.href)

                            # Add the item to the collection
                            link = {
                                "rel": "item",
                                "href": f"items/{item_file_name}",
                                "type": "application/json",
                            }
                            stac_collection.add_link(pystac.Link.from_dict(link))
                            items_in_collection += 1
                            items_count += 1

                            if (
                                items_in_collection >= max_items_per_collection
                                or items_count == total_items
                            ):
                                # Write the collection to a file
                                collection_path = os.path.join(
                                    output_path,
                                    collection_file_name,
                                )
                                with open(collection_path, "w") as collection_file:
                                    collection_file.write(
                                        json.dumps(
                                            stac_collection.to_dict(False, False),
                                            indent=2,
                                        )
                                    )
                                # Reset the collection
                                stac_collection.clear_items()
                                items_in_collection = 0
                                collection_number += 1
                        except STACTypeError:
                            invalid_item_ids.append(item_id)
                        except STACValidationError:
                            invalid_item_ids.append(item_id)

            # Show the invalid items
            if invalid_item_ids:
                click.echo(
                    click.style("The following items are invalid:", fg="red"),
                    err=True,
                )
                for item_id in invalid_item_ids:
                    click.echo(click.style(f"\t{item_id}", fg="red"), err=True)

            # Write the assets list to a file
            assets_file_name = f"{slugify(collection_id)}-assets.txt"
            assets_path = os.path.join(output_path, assets_file_name)
            with open(assets_path, "w") as assets_file:
                for href in assets_href:
                    assets_file.write(f"{href}\n")


@cli.group()
def ndjson():
    """Commands for working with NDJSON files."""
    ...


@ndjson.command(name="list")
@click.option(
    "-l",
    "--limit",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="The maximum number of items to list. 0 means no limit.",
)
@click.argument(
    "ndjson_file",
    type=click.File("r"),
)
def ndjson_list(
    limit: int,
    ndjson_file: TextIOWrapper,
):
    """List all the STAC items in an NDJSON file."""
    for i, line in enumerate(ndjson_file):
        if limit > 0 and i >= limit:
            break
        try:
            item_dict = json.loads(line)
            stac_item = pystac.Item.from_dict(item_dict)
            click.echo(stac_item.id)
        except json.JSONDecodeError:
            click.echo(
                click.style(f"Invalid JSON at line {i}", fg="red"),
                err=True,
            )
        except STACTypeError:
            click.echo(
                click.style(f"Invalid STAC item at line {i}", fg="red"),
                err=True,
            )


@ndjson.command(name="export")
@click.option(
    "-c",
    "--collection",
    "collection_id",
    required=True,
    default="exported-collection",
    show_default=True,
    help="The ID of the exported collection.",
)
@click.option(
    "-l",
    "--limit",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="The maximum number of items to export. 0 means no limit.",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    help="The path to the output directory.",
)
@click.option(
    "--validate/--no-validate",
    "validate",
    default=False,
    show_default=True,
    help="Validate the STAC items.",
)
@click.option(
    "--max-items-per-collection",
    "max_items_per_collection",
    default=500000,
    show_default=True,
    type=click.IntRange(min=1, max=1000000),
    help="The maximum number of items per collection. If the number of items is greater than this value, the items will be split into multiple collections.",  # noqa: E501
)
@click.argument(
    "ndjson_file",
    type=click.File("r"),
)
def ndjson_export(
    collection_id: str,
    limit: int,
    output_path: str,
    validate: bool,
    max_items_per_collection: int,
    ndjson_file: TextIOWrapper,
):
    """Export all the STAC items in an NDJSON file."""
    stac_collection = pystac.Collection(
        id=collection_id,
        description="Exported collection",
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([[-180.0, -90.0, 180.0, 90.0]]),
            temporal=pystac.TemporalExtent(
                [[datetime.fromisoformat("2020-01-01T00:00:00Z"), None]]
            ),
        ),
        catalog_type=pystac.CatalogType.SELF_CONTAINED,
    )

    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    # Create the items directory if it doesn't exist
    items_path = os.path.join(output_path, "items")
    os.makedirs(items_path, exist_ok=True)

    # Get the number of lines in the NDJSON file
    click.echo("Counting items...")
    total_items = sum(1 for _ in ndjson_file)
    ndjson_file.seek(0)
    if limit > 0 and total_items > limit:
        total_items = limit

    collection_number = 1
    items_in_collection = 0
    items_count = 0
    assets_href: list[str] = []
    invalid_items: list[str] = []
    collection_file_name = f"{slugify(collection_id)}_{collection_number}.json"

    for line in tqdm(
        ndjson_file,
        total=total_items,
        desc="Exporting items",
        unit=" items",
        colour="green",
    ):
        if items_count >= limit:
            break
        try:
            item = json.loads(line)
            stac_item = pystac.Item.from_dict(item)
            stac_item.set_parent(None)
            stac_item.set_root(None)
            stac_item.remove_links("self")
            stac_item.remove_links("collection")
            stac_item.add_link(
                pystac.Link(
                    rel="collection",
                    target=f"../{collection_file_name}",
                )
            )

            if validate:
                stac_item.validate()

            # Save the item to a file
            item_file_name = f"{slugify(stac_item.id)}.json"
            item_path = os.path.join(items_path, item_file_name)
            with open(item_path, "w") as item_file:
                item_file.write(json.dumps(stac_item.to_dict(), indent=2))

            # Add the assets to the assets list
            for asset in stac_item.assets.values():
                assets_href.append(asset.href)

            # Add the item to the collection
            link = {
                "rel": "item",
                "href": f"items/{item_file_name}",
                "type": "application/json",
            }
            stac_collection.add_link(pystac.Link.from_dict(link))
            items_in_collection += 1
            items_count += 1

            if (
                items_in_collection >= max_items_per_collection
                or items_count == total_items
            ):
                # Write the collection to a file
                collection_path = os.path.join(
                    output_path,
                    collection_file_name,
                )
                with open(collection_path, "w") as collection_file:
                    collection_file.write(
                        json.dumps(
                            stac_collection.to_dict(False, False),
                            indent=2,
                        )
                    )
                # Reset the collection
                stac_collection.clear_items()
                items_in_collection = 0
                collection_number += 1
                collection_file_name = (
                    f"{slugify(collection_id)}_{collection_number}.json"  # noqa: E501
                )
        except STACTypeError:
            invalid_items.append(line.strip())
        except STACValidationError:
            invalid_items.append(line.strip())

    # Show the invalid items
    if invalid_items:
        click.echo(
            click.style("The following items are invalid:", fg="red"),
            err=True,
        )
        for item_id in invalid_items:
            click.echo(click.style(f"\t{item_id}", fg="red"), err=True)

    # Write the assets list to a file
    assets_file_name = f"{slugify(collection_id)}-assets.txt"
    assets_path = os.path.join(output_path, assets_file_name)
    with open(assets_path, "w") as assets_file:
        for href in assets_href:
            assets_file.write(f"{href}\n")


if __name__ == "__main__":
    cli()
