# this_file: tests/test_native_boundaries.py
from unittest.mock import Mock
from fontlab_aidus_agentus.plugin.transport import ACPTransport, TransportState

class QByteArray:
    def __init__(self, value): self.value = value
    def data(self): return self.value


def test_native_qbytearray_read_delivers_message():
    transport = ACPTransport()
    transport._process = Mock()
    transport._process.readAllStandardOutput.return_value = QByteArray(b'{"jsonrpc":"2.0","id":7,"result":{}}\n')
    transport.messageReceived = Mock()
    transport._on_stdout_ready()
    transport.messageReceived.emit.assert_called_once_with({"jsonrpc":"2.0","id":7,"result":{}})


def test_finished_accepts_qt5_exit_status():
    transport = ACPTransport()
    transport.processFinished = Mock()
    transport._on_finished(0, 0)
    transport.processFinished.emit.assert_called_once_with(0)


def test_stop_when_finished_signal_reenters_retains_process_reference():
    transport = ACPTransport()
    process = Mock()
    transport._process = process
    transport._state = TransportState.CONNECTED
    def finished(timeout):
        transport._on_finished(15, 1)
        return False
    process.waitForFinished.side_effect = finished
    transport.stop()
    process.kill.assert_called_once()
    assert transport.state() == TransportState.DISCONNECTED


def test_explicit_config_never_searches_private_default_paths(monkeypatch, tmp_path):
    from fontlab_aidus_agentus.plugin.config import _find_config_paths
    config = tmp_path / "explicit.json"
    monkeypatch.setenv("AIDUS_CONFIG", str(config))
    assert _find_config_paths() == [str(config)]


def test_graceful_stop_closes_acp_stdin_before_signalling_process():
    transport = ACPTransport()
    process = Mock()
    process.waitForFinished.return_value = True
    transport._process = process
    transport.stop()
    process.closeWriteChannel.assert_called_once()
    process.terminate.assert_not_called()
    process.kill.assert_not_called()


def test_public_shutdown_stops_external_brain_and_removes_dock(monkeypatch):
    from fontlab_aidus_agentus.plugin import main
    dock = Mock()
    monkeypatch.setattr(main, "_dock", dock)
    main.shutdown()
    dock.get_client.return_value._transport.stop.assert_called_once()
    dock.get_client.return_value.cleanup.assert_called_once()
    dock.close.assert_called_once()
    dock.deleteLater.assert_called_once()
    assert main.get_dock() is None


def test_executor_accepts_agentpool_script_argument_without_changing_caller():
    from fontlab_aidus_agentus.plugin.executor import FontLabExecutor
    executor = FontLabExecutor()
    arguments = {"script": "result = 6 * 7"}
    assert executor.run("run_fontlab_script", arguments) == {"success": True, "result": 42}
    assert arguments == {"script": "result = 6 * 7"}


def test_executor_metric_validation_matches_optional_agentpool_schema():
    from fontlab_aidus_agentus.plugin.executor import FontLabExecutor
    executor = FontLabExecutor()
    info = executor._registry.get_info("set_glyph_metrics")
    assert executor._validate_args("set_glyph_metrics", {"lsb": 0}, info) is None


class NativeGlyph:
    def __init__(self):
        from types import SimpleNamespace
        self.name = "fixture"
        self.fgGlyphId = 201
        self.fgGlyph = SimpleNamespace(name=self.name, id=201, unicode=65)
        class Font(dict):
            id = 301
        self.package = SimpleNamespace(id=401, fgId=301, isNull=False,
                                       fgPackage=Font({self.name: self.fgGlyph}))
        self.advanceWidth = 600.0
        self.activeLayer = SimpleNamespace(transform=object(), autoLayer=False)
        self.layers = [self.activeLayer]
        self.left = 50.0
        self.right = 60.0
    def getLSB(self, transform):
        assert transform is self.activeLayer.transform
        return self.left
    def getRSB(self, transform):
        assert transform is self.activeLayer.transform
        return self.right
    def setLSB(self, value, move_guidelines, transform):
        assert transform is self.activeLayer.transform
        assert move_guidelines is False
        self.left = value
        return True
    def setRSB(self, value, transform):
        assert transform is self.activeLayer.transform
        self.right = value
        return True


def test_native_glyph_tools_use_supported_attributes_and_layer_transform(monkeypatch):
    from types import SimpleNamespace
    from fontlab_aidus_agentus.plugin import executor
    glyph = NativeGlyph()
    monkeypatch.setattr(executor, "fl", SimpleNamespace(CurrentGlyph=lambda:glyph, CurrentFont=lambda:object(),
        flWorkspace=SimpleNamespace(instance=lambda: SimpleNamespace(
            findPackageId=lambda identity: glyph.package))))
    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    tools = executor.FontLabExecutor()
    info = tools.run("get_current_glyph_info")
    assert (info["unicode"], info["width"], info["lsb"], info["rsb"]) == (65,600,50,60)
    result = tools.run("set_glyph_metrics", {"width":700,"lsb":55,"rsb":65})
    assert result["success"] is True
    assert result["metrics"] == {"width":700,"lsb":55,"rsb":65}
    info = tools.run("get_current_glyph_info")
    assert (info["width"],info["lsb"],info["rsb"]) == (700,55,65)


def test_reconnect_clears_pending_mutations_and_negotiates_new_session():
    from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState
    transport = Mock()
    transport.start.return_value = (True,None)
    transport.send.return_value = True
    client = AidusAgentusClient(transport=transport)
    client._state = ClientState.WAITING
    client._session_id = "old"
    client._pending_requests[99] = "session.prompt"
    assert client.reconnect()
    assert client._session_id is None
    assert 99 not in client._pending_requests
    transport.stop.assert_called_once()
    transport.start.assert_called_once()
    request = transport.send.call_args.args[0]
    assert request["method"] == "initialize"
    assert client.state() == ClientState.INITIALIZING
    assert transport.send.call_count == 1, "Pending mutation must never be replayed"


def test_configured_credentials_resolve_to_child_only_provider_environment(monkeypatch,tmp_path):
    from fontlab_aidus_agentus.plugin.config import child_environment
    path = tmp_path / "synthetic-key"
    path.write_text("synthetic-file-value\n")
    monkeypatch.setenv("AIDUS_SYNTHETIC_KEY","synthetic-env-value")
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY",raising=False)
    env = child_environment({"api_keys":{"openai":str(path),"anthropic":"env:AIDUS_SYNTHETIC_KEY"}})
    assert env == {"OPENAI_API_KEY":"synthetic-file-value","ANTHROPIC_API_KEY":"synthetic-env-value"}
    import os
    assert "OPENAI_API_KEY" not in os.environ
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_readiness_delegates_model_credentials_to_selected_brain(monkeypatch):
    from fontlab_aidus_agentus.plugin import config
    monkeypatch.setattr(config,"load_config",lambda:{"api_keys":{}})
    monkeypatch.setattr(config,"get_api_key",Mock(side_effect=AssertionError("No arbitrary provider check")))
    result = config.check_first_run_setup()
    assert result["ready"],result


def test_native_setter_failure_never_reports_success(monkeypatch):
    from types import SimpleNamespace
    from fontlab_aidus_agentus.plugin import executor
    glyph = NativeGlyph()
    glyph.setLSB = lambda *args: False
    monkeypatch.setattr(executor,"fl",SimpleNamespace(CurrentGlyph=lambda:glyph,CurrentFont=lambda:object()))
    monkeypatch.setattr(executor,"FL_AVAILABLE",True)
    result = executor.FontLabExecutor().run("set_glyph_metrics",{"lsb":55})
    assert "error" in result
    assert "success" not in result


def test_process_finished_discards_stale_session_and_pending_requests():
    from fontlab_aidus_agentus.plugin.client import AidusAgentusClient,ClientState
    client = AidusAgentusClient()
    client._state = ClientState.WAITING
    client._session_id = "stale"
    client._pending_requests[42] = "session.prompt"
    client._handle_process_finished(1)
    assert client.state() == ClientState.DISCONNECTED
    assert client._session_id is None
    assert client._pending_requests == {}


def test_native_ui_reads_qt_scrollbar_property():
    from fontlab_aidus_agentus.plugin.ui import AidusAgentusDock
    dock = object.__new__(AidusAgentusDock)
    scrollbar = Mock(maximum=17)
    dock._chat_display = Mock()
    dock._chat_display.verticalScrollBar.return_value = scrollbar
    dock._scroll_to_bottom()
    scrollbar.setValue.assert_called_once_with(17)


def test_native_submit_reads_qt_lineedit_property():
    from fontlab_aidus_agentus.plugin.ui import AidusAgentusDock
    dock = object.__new__(AidusAgentusDock)
    dock._input_field = Mock(text="second prompt")
    dock._client = Mock()
    dock._on_submit()
    dock._client.send_user_prompt.assert_called_once_with("second prompt")


def test_native_theme_detection_reads_palette_property():
    from types import SimpleNamespace
    from fontlab_aidus_agentus.plugin.ui import AidusAgentusDock
    dock = object.__new__(AidusAgentusDock)
    dock.palette = SimpleNamespace(color=lambda role:SimpleNamespace(lightness=lambda:247))
    assert dock._detect_is_dark() is False


def test_native_metric_noop_accepts_false_setter_when_readback_matches(monkeypatch):
    from types import SimpleNamespace
    from fontlab_aidus_agentus.plugin import executor
    glyph = NativeGlyph()
    glyph.setLSB = lambda *args:False
    glyph.setRSB = lambda *args:False
    monkeypatch.setattr(executor,"fl",SimpleNamespace(CurrentGlyph=lambda:glyph,CurrentFont=lambda:object()))
    monkeypatch.setattr(executor,"FL_AVAILABLE",True)
    result = executor.FontLabExecutor().run("set_glyph_metrics",{"lsb":50,"rsb":60})
    assert result["success"] is True
    assert result["metrics"] == {"width":600,"lsb":50,"rsb":60}


def test_native_rsb_failure_still_reports_applied_width(monkeypatch):
    from types import SimpleNamespace
    from fontlab_aidus_agentus.plugin import executor
    glyph = NativeGlyph()
    glyph.setRSB = lambda *args:False
    monkeypatch.setattr(executor,"fl",SimpleNamespace(CurrentGlyph=lambda:glyph,CurrentFont=lambda:object()))
    monkeypatch.setattr(executor,"FL_AVAILABLE",True)
    result = executor.FontLabExecutor().run("set_glyph_metrics",{"width":700,"rsb":65})
    assert "error" in result
    assert result["changes"] == ["width=700"]
    assert glyph.advanceWidth == 700
