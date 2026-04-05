"""Tests for the persistent source registry and registry-backed manifests."""

from __future__ import annotations

from app.agent.planner import _schema_subset_for_question
from app.data.registry import create_source_link, get_schema_manifest, ingest_source
from app.data.semantic_model import get_semantic_context


def _relation_by_name(manifest: dict, relation_name: str) -> dict:
    return next(relation for relation in manifest["relations"] if relation["name"] == relation_name)


def test_registry_manifest_includes_builtin_primary_relation() -> None:
    manifest = get_schema_manifest()

    relation = _relation_by_name(manifest, "opportunities_enriched")
    assert relation["source_id"] == "source_builtin_crm"
    assert relation["is_primary"] is True
    assert relation["source_name"] == "CRM Sales Opportunities"


def test_nested_json_upload_creates_primary_and_child_relations() -> None:
    asset = ingest_source(
        "orders.json",
        b'[{"order_id":"o1","customer":{"name":"Ada"},"items":[{"sku":"A1","qty":2},{"sku":"B2","qty":1}]}]',
    )

    manifest = get_schema_manifest([asset.id])
    root = _relation_by_name(manifest, asset.primaryRelationName)
    child = next(relation for relation in manifest["relations"] if relation["name"].startswith(f"{asset.primaryRelationName}__"))

    assert asset.relationCount == 2
    assert root["is_primary"] is True
    assert any(column["name"] == "customer__name" and column["source_path"] == "customer.name" for column in root["columns"])
    assert child["parent_relation"] == asset.primaryRelationName
    assert any(join["target_relation"] == asset.primaryRelationName for join in child["join_keys"])
    assert {column["name"] for column in child["columns"]} >= {"record_id", "parent_record_id", "ordinal", "sku", "qty"}


def test_unrelated_sources_do_not_auto_link_even_with_shared_column_names() -> None:
    customers = ingest_source("customers.csv", b"customer_id,name\nc1,Ada\nc2,Ben\n")
    orders = ingest_source("orders.csv", b"customer_id,amount\nc1,100\nc2,50\n")

    manifest = get_schema_manifest([customers.id, orders.id])
    customers_relation = _relation_by_name(manifest, customers.primaryRelationName)
    orders_relation = _relation_by_name(manifest, orders.primaryRelationName)

    assert customers_relation["join_keys"] == []
    assert orders_relation["join_keys"] == []


def test_explicit_source_links_appear_in_manifest() -> None:
    customers = ingest_source("customers.csv", b"customer_id,name\nc1,Ada\nc2,Ben\n")
    orders = ingest_source("orders.csv", b"customer_id,amount\nc1,100\nc2,50\n")

    create_source_link(customers.primaryRelationName, "customer_id", orders.primaryRelationName, "customer_id")
    manifest = get_schema_manifest([customers.id, orders.id])
    customers_relation = _relation_by_name(manifest, customers.primaryRelationName)
    orders_relation = _relation_by_name(manifest, orders.primaryRelationName)

    assert any(join["target_relation"] == orders.primaryRelationName and join["source_column"] == "customer_id" for join in customers_relation["join_keys"])
    assert any(join["target_relation"] == customers.primaryRelationName and join["source_column"] == "customer_id" for join in orders_relation["join_keys"])


def test_semantic_context_scopes_to_selected_sources() -> None:
    asset = ingest_source("inventory.csv", b"sku,stock\nA1,10\nB2,3\n")

    full_context = get_semantic_context().schema_manifest
    scoped_context = get_semantic_context([asset.id]).schema_manifest

    assert any(relation["name"] == "opportunities_enriched" for relation in full_context["relations"])
    assert not any(relation["name"] == "opportunities_enriched" for relation in scoped_context["relations"])
    assert any(relation["name"] == asset.primaryRelationName for relation in scoped_context["relations"])


def test_schema_subset_prefers_relevant_uploaded_primary_relation() -> None:
    ingest_source("inventory.csv", b"sku,stock\nA1,10\nB2,3\n")
    invoices = ingest_source("invoices.csv", b"invoice_id,invoice_amount,status\ni1,100,paid\ni2,250,due\n")
    ingest_source("campaigns.csv", b"campaign,spend\nspring,1200\nsummer,950\n")

    manifest = get_schema_manifest()
    subset = _schema_subset_for_question(manifest, "Which invoice amount is highest?")

    assert any(relation["name"] == invoices.primaryRelationName for relation in subset["relations"])
