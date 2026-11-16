# this_file: tests/core/fixtures/acp_core.py
"""Run the production boot with a deterministic model and zero provider calls."""

from fontlab_aidus_agentus.core import boot, fontlab_mcp

original_build = fontlab_mcp.build_manifest


def test_manifest(path, server):
    config = original_build(path, server)
    for agent in config["agents"].values():
        agent["model"] = {
            "type": "test",
            "custom_output_text": "Roundtrip complete",
            "call_tools": ["list_fonts" if server else "get_current_glyph_info"],
        }
    return config


fontlab_mcp.build_manifest = test_manifest
raise SystemExit(boot.main())
