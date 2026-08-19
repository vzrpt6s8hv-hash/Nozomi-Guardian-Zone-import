import os

import pandas as pd
import pytest

from nozomi_zone_import_tool.core import (
    apply_mapping,
    auto_map_asset_columns,
    auto_map_columns,
    generate_config_text,
    load_table_file,
    parse_config_text,
    suggest_zones_from_assets,
)

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")
SAMPLE_CFG_PATH = os.path.join(SAMPLE_DATA_DIR, "sample_guardian_export.cfg")
SAMPLE_TEMPLATE_PATH = os.path.join(SAMPLE_DATA_DIR, "sample_template.csv")
SAMPLE_ASSET_PATH = os.path.join(SAMPLE_DATA_DIR, "sample_asset_export.csv")


def test_round_trip_parse_and_generate_matches_sample_cfg():
    """Parsing a real Guardian export and regenerating it should reproduce
    every non-blank command line exactly."""
    original_text = open(SAMPLE_CFG_PATH, encoding="utf-8").read()
    rows = parse_config_text(original_text)
    assert len(rows) == 5

    compact_zones = {"Cloud_Services_Demo", "Physical_Security_Demo"}
    for row in rows:
        row["output_mode"] = "compact" if row["zone_name"] in compact_zones else "full"

    regenerated_text = generate_config_text(rows, default_mode="full")

    original_lines = {l for l in original_text.splitlines() if l.strip()}
    regenerated_lines = {l for l in regenerated_text.splitlines() if l.strip()}

    # Nothing extra should appear.
    assert regenerated_lines - original_lines == set()
    # Only the documented edge case (a merging_zone command explicitly left
    # blank in the source file) is allowed to be missing - because that
    # command is only ever emitted when the field has an actual value.
    missing = original_lines - regenerated_lines
    assert missing == {"vi zones setmerging_zone  Substation_A_Demo"}


def test_generate_config_text_full_vs_compact_mode():
    rows = [{
        "zone_name": "TestZone", "networks": "10.0.0.0/24", "level": "3",
        "security_profile": "", "force_assigned_vlan_id": "", "mac_matching_fallback": "",
        "extended_network_statistic_enabled": "", "use_label_as_node_device_id": "",
        "matching_vlan_id": "", "assigned_vlan_id": "42", "adaptive_learning": "",
        "learning": "", "is_public": "", "merging_zone": "", "merging": "",
        "isolated": "", "output_mode": "",
    }]
    full_text = generate_config_text(rows, default_mode="full")
    compact_text = generate_config_text(rows, default_mode="compact")

    assert "vi zones add 10.0.0.0/24 TestZone" in full_text
    assert "vi zones setsecurity_profile  TestZone" in full_text  # blank value still written
    assert "vi zones setassigned_vlan_id 42 TestZone" in full_text

    assert "vi zones setsecurity_profile" not in compact_text  # skipped: no value
    assert "vi zones setassigned_vlan_id 42 TestZone" in compact_text  # kept: has value


def test_generate_config_text_skips_rows_without_zone_name():
    rows = [{"zone_name": "", "networks": "10.0.0.0/24", "output_mode": "full"}]
    assert generate_config_text(rows) == ""


def test_auto_map_columns_resolves_messy_headers():
    columns = ["Zone", "Subnets / CIDR", "Trust Level", "VLAN", "Public?"]
    mapping = auto_map_columns(columns)
    assert mapping["zone_name"] == "Zone"
    assert mapping["networks"] == "Subnets / CIDR"
    assert mapping["level"] == "Trust Level"
    assert mapping["assigned_vlan_id"] == "VLAN"
    assert mapping["is_public"] == "Public?"
    # Fields with no matching column should map to "" (manual mapping required)
    assert mapping["security_profile"] == ""


def test_load_and_convert_sample_template_csv():
    df = load_table_file(SAMPLE_TEMPLATE_PATH)
    mapping = auto_map_columns(list(df.columns))
    assert mapping["zone_name"] and mapping["networks"]
    rows = apply_mapping(df, mapping)
    text = generate_config_text(rows, default_mode="full")
    assert "vi zones add 10.10.1.0/24 Corporate_LAN" in text
    assert "vi zones add 172.16.0.0/16 Cloud_Services_Demo" in text


def test_suggest_zones_from_assets_uses_matching_vlan_for_duplicate_networks():
    """When the same network/CIDR is reused across more than one VLAN or
    segment, matching_vlan_id must be populated (not assigned_vlan_id),
    per Guardian's zone-matching semantics."""
    df = load_table_file(SAMPLE_ASSET_PATH)
    mapping = auto_map_asset_columns(list(df.columns))
    rows, warnings = suggest_zones_from_assets(df, mapping)

    by_name = {r["zone_name"]: r for r in rows}

    # Plant-A-Line1 and Plant-B-Line1 share the exact same three IPs
    # (10.40.1.1-3) on different VLANs (100 vs 200) -> ambiguous by IP alone.
    assert by_name["Plant-A-Line1"]["matching_vlan_id"] == "100"
    assert by_name["Plant-A-Line1"]["assigned_vlan_id"] == ""
    assert by_name["Plant-B-Line1"]["matching_vlan_id"] == "200"
    assert by_name["Plant-B-Line1"]["assigned_vlan_id"] == ""

    # ProdLineA's network is unique -> the normal case: assign the VLAN.
    assert by_name["ProdLineA"]["assigned_vlan_id"] == "55"
    assert by_name["ProdLineA"]["matching_vlan_id"] == ""
    assert by_name["ProdLineA"]["force_assigned_vlan_id"] == "true"

    assert any("matching_vlan_id" in w for w in warnings)


def test_suggest_zones_from_assets_requires_ip_or_segment_mapping():
    df = pd.DataFrame({"Foo": ["1", "2"]})
    with pytest.raises(ValueError):
        suggest_zones_from_assets(df, {"ip": "", "vlan": "", "segment": "", "label": ""})


def test_parse_config_text_ignores_unrelated_lines():
    text = "# a comment\nnot a vi zones line\nvi zones add 10.0.0.0/8 Solo\nvi zones setlevel 2 Solo\n"
    rows = parse_config_text(text)
    assert len(rows) == 1
    assert rows[0]["zone_name"] == "Solo"
    assert rows[0]["networks"] == "10.0.0.0/8"
    assert rows[0]["level"] == "2"
