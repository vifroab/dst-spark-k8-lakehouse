# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: py:percent
#     notebook_metadata_filter: -widgets,-varInspector
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.7
# ---

# %%
"""
catalog_helpers.py

Provides helper functions to simulate a three-level namespace (catalog.schema.table)
while using a standard two-level Hive Metastore (database.table).
"""

# %%
import re
import unicodedata

# %%
# The virtual "catalog" name we will use in our code.
ALIAS_CATALOG = "leru"


# %%
def _slugify(s: str) -> str:
    """
    Normalizes a string for use as a database name.
    Converts to lowercase, maps Danish characters to ASCII equivalents,
    and replaces any non-alphanumeric characters with underscores.

    Example: "Skema Indlæst" -> "skema_indlaest"
    """
    if not s:
        return ""
    s = s.lower()
    s = s.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9_]+", "_", s).strip("_")
    return s


# %%
def resolve_table_name(three_part_name: str) -> str:
    """
    Converts a simulated three-part name into a valid two-part Hive table name.

    Example: "leru.integreret.my_cool_table" -> "leru_integreret.my_cool_table"
    """
    parts = three_part_name.split(".", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Invalid format. Expected '<catalog>.<schema>.<table>', but got '{three_part_name}'."
        )

    catalog, schema, table = parts

    if catalog.lower() != ALIAS_CATALOG:
        raise ValueError(
            f"Unsupported catalog '{catalog}'. This helper only supports the '{ALIAS_CATALOG}' catalog."
        )

    # Combine catalog and schema with an underscore to form the real database name
    database_name = f"{_slugify(catalog)}_{_slugify(schema)}"

    return f"`{database_name}`.`{table}`"


# %%
# A simple regex to find and replace three-part names in a SQL query.
# This is a basic implementation and might not handle all edge cases (e.g., names within strings).
_3PART_RE = re.compile(
    rf"\b({ALIAS_CATALOG})\.([a-zA-Z0-9_æøåÆØÅ]+)\.([a-zA-Z0-9_]+)\b", re.IGNORECASE
)


# %%
def resolve_sql_query(query: str) -> str:
    """
    Rewrites a SQL query, converting all simulated three-part names to their
    valid two-part Hive equivalents.

    Example: "SELECT * FROM leru.integreret.my_table" -> "SELECT * FROM leru_integreret.my_table"
    """

    def replacer(match):
        catalog, schema, table = match.groups()
        return resolve_table_name(f"{catalog}.{schema}.{table}")

    return _3PART_RE.sub(replacer, query)


# %% [markdown]
# --- Spark Session Wrapper Functions ---


# %%
def table(spark, three_part_name: str):
    """A wrapper for spark.table() that uses the resolver."""
    resolved_name = resolve_table_name(three_part_name)
    return spark.table(resolved_name)


# %%
def sql(spark, query: str):
    """A wrapper for spark.sql() that uses the SQL resolver."""
    resolved_query = resolve_sql_query(query)
    return spark.sql(resolved_query)
