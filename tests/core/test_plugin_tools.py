# this_file: tests/core/test_plugin_tools.py
"""Check that fallback tools preserve their arguments and surface executor errors."""

import ast
import inspect
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from agentpool_server.acp_server.input_provider import ACPInputProvider

from fontlab_aidus_agentus.core import plugin_tools


@pytest.fixture
def context():
    client = SimpleNamespace(ext_method=AsyncMock(return_value={"width": 600}))
    session = SimpleNamespace(client=client, session_id="test-session")
    return Mock(get_input_provider=Mock(return_value=ACPInputProvider(session)))


@pytest.mark.asyncio
async def test_info_when_plugin_backend_uses_registered_name(context):
    assert await plugin_tools.get_current_glyph_info(context) == {"width": 600}
    context.get_input_provider().session.client.ext_method.assert_awaited_once_with(
        "fontlab/tool",
        {"sessionId": "test-session", "name": "get_current_glyph_info", "arguments": {}},
    )


@pytest.mark.asyncio
async def test_metrics_when_optional_values_omitted_preserves_zero(context):
    await plugin_tools.set_glyph_metrics(context, width=0, lsb=10)
    assert context.get_input_provider().session.client.ext_method.call_args.args[1][
        "arguments"
    ] == {"width": 0, "lsb": 10}


@pytest.mark.asyncio
async def test_script_when_plugin_backend_delegates_to_existing_sandbox(context):
    await plugin_tools.run_fontlab_script(context, "print(1)")
    assert context.get_input_provider().session.client.ext_method.call_args.args[1][
        "arguments"
    ] == {"code": "print(1)"}


@pytest.mark.asyncio
async def test_call_when_executor_returns_error_surfaces_it(context):
    context.get_input_provider().session.client.ext_method.return_value = {
        "error": "No active font"
    }
    with pytest.raises(RuntimeError, match="No active font"):
        await plugin_tools.get_current_glyph_info(context)


@pytest.mark.asyncio
async def test_call_when_not_in_acp_session_fails_before_execution():
    with pytest.raises(RuntimeError, match="ACP session"):
        await plugin_tools.get_current_glyph_info(Mock(get_input_provider=Mock(return_value=None)))


ROUNDTRIP_CASES = [
    pytest.param("get_current_glyph_info", {}, id="glyph-info"),
    pytest.param("set_glyph_metrics", {}, id="metrics-omitted"),
    pytest.param("set_glyph_metrics", {"width": 0}, id="metrics-zero-width"),
    pytest.param("set_glyph_metrics", {"lsb": 0}, id="metrics-zero-lsb"),
    pytest.param("set_glyph_metrics", {"rsb": 0}, id="metrics-zero-rsb"),
    pytest.param(
        "set_glyph_metrics",
        {"width": 700, "lsb": -10, "rsb": 20},
        id="metrics-all",
    ),
    pytest.param("run_fontlab_script", {"script": "result = 6 * 7"}, id="script"),
]


def test_roundtrip_cases_cover_every_brain_tool_calling_call_plugin():
    source = ast.parse(inspect.getsource(plugin_tools))
    tools = {
        node.name
        for node in source.body
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "call_plugin"
            for call in ast.walk(node)
        )
    }
    covered = {case.values[0] for case in ROUNDTRIP_CASES}
    assert covered == tools, "Add round-trip cases for every brain tool using call_plugin"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,arguments", ROUNDTRIP_CASES)
async def test_brain_tool_when_roundtripped_through_executor_matches_contract(
    tool_name, arguments, context, monkeypatch
):
    from fontlab_aidus_agentus.plugin import executor as plugin_executor

    glyph = SimpleNamespace(name="A", unicode=65, width=600, lsb=50, rsb=60, layers=[])
    monkeypatch.setattr(plugin_executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(
        plugin_executor,
        "fl",
        SimpleNamespace(
            CurrentFont=lambda: object(),
            CurrentGlyph=lambda: glyph,
        ),
    )
    executor = plugin_executor.FontLabExecutor()

    async def dispatch(method, params):
        # Cross a JSON boundary and validate before run() can normalize aliases.
        params = json.loads(json.dumps(params))
        assert method == "fontlab/tool", "Use the actual ACP extension route"
        assert params["sessionId"] == "test-session", "Preserve the ACP session"
        assert params["name"] == tool_name, "Brain and executor tool names must agree"
        info = executor._registry.get_info(params["name"])
        assert info is not None, "Brain tool must be registered by the executor"
        assert executor._validate_args(params["name"], params["arguments"], info) is None, (
            f"Noncanonical arguments for {tool_name}: {sorted(params['arguments'])}"
        )
        return executor.run(params["name"], params["arguments"])

    client = context.get_input_provider().session.client
    client.ext_method.side_effect = dispatch
    result = await getattr(plugin_tools, tool_name)(context, **arguments)
    client.ext_method.assert_awaited_once()
    assert "error" not in result, f"Fallback tool failed: {result}"
    if tool_name == "get_current_glyph_info":
        assert result == {
            "name": "A",
            "unicode": 65,
            "width": 600,
            "lsb": 50,
            "rsb": 60,
            "height": None,
            "layers": 0,
        }, "Glyph info must survive the complete fallback path"
    elif tool_name == "set_glyph_metrics":
        expected = {"width": 600, "lsb": 50, "rsb": 60} | arguments
        assert result == {
            "success": True,
            "glyph": "A",
            "changes": [f"{key}={value}" for key, value in arguments.items()],
        }, "Only supplied metrics should be changed"
        assert {key: getattr(glyph, key) for key in expected} == expected, (
            "Metrics must be applied to the glyph, including zeros and negative bearings"
        )
    else:
        assert result == {"success": True, "result": 42}, "Script must reach the sandbox"
