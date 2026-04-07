"""Tests for generic source-registry facts and raw-schema planner input."""

from __future__ import annotations

import pytest

from app.agent.planner import build_planner_input
from app.config import get_settings
from app.data.registry import clear_source_registry, create_source_link, ingest_source
from app.data.semantic_model import clear_semantic_context_cache


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_PATH", str(tmp_path / "source_registry.duckdb"))
    get_settings.cache_clear()
    clear_source_registry()
    clear_semantic_context_cache()
    yield
    clear_source_registry()
    clear_semantic_context_cache()
    get_settings.cache_clear()


def _table_by_name(planner_input, table_name: str):
    for source in planner_input.sources:
        for table in source.tables:
            if table.table_name == table_name:
                return table
    raise AssertionError(f"Table {table_name!r} not found in planner input.")


def test_build_planner_input_returns_empty_sources_without_uploads() -> None:
    planner_input = build_planner_input("What data is available?")

    assert planner_input.execution_dialect == "duckdb"
    assert planner_input.sources == []
    assert planner_input.relationships == []


def test_csv_planner_input_preserves_raw_table_and_column_names() -> None:
    asset = ingest_source(
        "Sales Orders 2024.csv",
        b"Order ID,Customer Name,Order Value ($)\n1,Ada,120.5\n2,Ben,80.0\n",
    )

    planner_input = build_planner_input("Which customers spent the most?", [asset.id])

    assert len(planner_input.sources) == 1
    source = planner_input.sources[0]
    assert source.source_format == "csv"
    table = _table_by_name(planner_input, "Sales Orders 2024")
    assert table.source_id == asset.id
    assert table.table_name == "Sales Orders 2024"
    assert {column.column_name for column in table.columns} == {"Order ID", "Customer Name", "Order Value ($)"}
    assert table.identifier_columns == ["Order ID"]
    assert table.measure_columns == ["Order Value ($)"]
    assert "semantic_mappings" not in table.model_dump()
    assert all("semantic_hints" not in column.model_dump() for column in table.columns)


def test_tsv_planner_input_keeps_full_schema_without_trimming() -> None:
    headers = ["Order ID"] + [f"Column {index}" for index in range(1, 23)]
    row_one = ["o1"] + [str(index) for index in range(1, 23)]
    row_two = ["o2"] + [str(index + 100) for index in range(1, 23)]
    payload = ("\t".join(headers) + "\n" + "\t".join(row_one) + "\n" + "\t".join(row_two) + "\n").encode("utf-8")
    asset = ingest_source("wide.tsv", payload)

    planner_input = build_planner_input("Show me every field.", [asset.id])
    table = _table_by_name(planner_input, "wide")

    assert planner_input.sources[0].source_format == "tsv"
    assert len(table.columns) == len(headers)
    assert {column.column_name for column in table.columns} == set(headers)


def test_nested_json_upload_uses_raw_table_names_and_confirmed_relationships() -> None:
    asset = ingest_source(
        "orders.json",
        b'[{"order_id":"o1","customer":{"name":"Ada"},"items":[{"sku":"A1","qty":2},{"sku":"B2","qty":1}]}]',
    )

    planner_input = build_planner_input("Which items were ordered?", [asset.id])
    root = _table_by_name(planner_input, "orders")
    child = _table_by_name(planner_input, "orders.items")

    assert {table.table_name for table in planner_input.sources[0].tables} == {"orders", "orders.items"}
    assert any(column.column_name == "name" and column.source_path == "customer.name" for column in root.columns)
    assert {column.column_name for column in child.columns} == {"sku", "qty"}

    relationship = planner_input.relationships[0]
    assert relationship.left_table == "orders"
    assert relationship.right_table == "orders.items"
    assert relationship.relationship_type == "parent_child"
    assert relationship.cardinality == "one_to_many"
    assert relationship.join_safety == "aggregate_child_before_join"
    assert relationship.confirmed_by == "json_nesting"
    assert relationship.join_keys[0].left_column == "record_id"
    assert relationship.join_keys[0].right_column == "parent_record_id"


def test_unrelated_sources_do_not_auto_join_on_shared_column_names() -> None:
    customers = ingest_source("customers.csv", b"Customer ID,Name\nc1,Ada\nc2,Ben\n")
    orders = ingest_source("orders.csv", b"Customer ID,Amount\nc1,100\nc2,50\n")

    planner_input = build_planner_input("Which customers spent the most?", [customers.id, orders.id])

    assert len(planner_input.sources) == 2
    assert planner_input.relationships == []


def test_explicit_source_links_are_exposed_as_confirmed_relationships() -> None:
    customers = ingest_source("customers.csv", b"Customer ID,Name\nc1,Ada\nc2,Ben\n")
    orders = ingest_source("orders.csv", b"Customer ID,Amount\nc1,100\nc1,50\n")
    create_source_link(customers.primaryRelationName, "customer_id", orders.primaryRelationName, "customer_id")

    planner_input = build_planner_input("Which customers spent the most?", [customers.id, orders.id])

    assert len(planner_input.relationships) == 1
    relationship = planner_input.relationships[0]
    assert relationship.relationship_type == "explicit"
    assert relationship.confirmed_by == "user_link"
    assert relationship.cardinality == "one_to_many"
    assert relationship.join_keys[0].left_column == "Customer ID"
    assert relationship.join_keys[0].right_column == "Customer ID"
