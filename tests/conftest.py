# this_file: tests/conftest.py
"""A recording fake of the PythonQt surface the dock uses, with FontLab's quirks.

PythonQt exposes some getters as values (`QLineEdit.text`, `QScrollBar.maximum`,
`QWidget.palette`) where development bindings expose callables; `fake_qt` lets a
test pick either form. Modules that bind PythonQt at import are loaded fresh
against the fake and removed again afterwards.
"""

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def disconnect(self, slot=None):
        self.slots = [] if slot is None else [s for s in self.slots if s is not slot]

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class Recorder:
    """Records every unknown method call as (name, args)."""

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def record(*args, **kwargs):
            self.calls.append((name, args))
            return None

        return record

    def called(self, name):
        return [args for call, args in self.calls if call == name]


class FakeColor:
    def __init__(self, lightness, callable_form):
        self._lightness = lightness
        self.lightness = (lambda: lightness) if callable_form else lightness


class FakePalette:
    Window = 10

    def __init__(self, lightness, callable_form):
        self._color = FakeColor(lightness, callable_form)

    def color(self, role):
        assert role == FakePalette.Window
        return self._color


class FakeQt:
    LeftDockWidgetArea = 1
    RightDockWidgetArea = 2
    Key_Escape = 0x01000000
    Key_Return = 0x01000004


class FakeScrollBar(Recorder):
    def __init__(self, maximum, callable_form):
        super().__init__()
        self.maximum = (lambda: maximum) if callable_form else maximum


def build_qt(*, callable_getters=False, lightness=30):
    """Return (PythonQt, QtCore, QtGui) fake modules."""

    class QWidget(Recorder):
        pass

    class QDockWidget(Recorder):
        def __init__(self, title="", parent=None):
            super().__init__(title, parent)
            self.palette = (
                (lambda: FakePalette(lightness, True)) if callable_getters
                else FakePalette(lightness, False)
            )

    class QPushButton(Recorder):
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.clicked = FakeSignal()

    class QLineEdit(Recorder):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.returnPressed = FakeSignal()
            self.value = ""

        def __getattr__(self, name):
            if name == "text":
                return (lambda: self.value) if callable_getters else self.value
            return super().__getattr__(name)

        def clear(self):
            self.calls.append(("clear", ()))
            self.value = ""

    class QTextEdit(Recorder):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.html = []
            self.scrollbar = FakeScrollBar(500, callable_getters)

        def append(self, html):
            self.html.append(html)

        def clear(self):
            self.html = []

        def verticalScrollBar(self):
            return self.scrollbar

    class QLabel(Recorder):
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.text_value, self.visible, self.style = text, True, ""

        def setText(self, text):
            self.text_value = text

        def setVisible(self, visible):
            self.visible = visible

        def isVisible(self):
            return self.visible

        def setStyleSheet(self, style):
            self.style = style

    pythonqt = ModuleType("PythonQt")
    core = ModuleType("PythonQt.QtCore")
    gui = ModuleType("PythonQt.QtGui")
    core.Qt = FakeQt
    for cls in (QWidget, QDockWidget, QPushButton, QLineEdit, QTextEdit, QLabel):
        setattr(gui, cls.__name__, cls)
    gui.QFont = Recorder
    gui.QHBoxLayout = Recorder
    gui.QVBoxLayout = Recorder
    gui.QPalette = FakePalette
    pythonqt.QtCore, pythonqt.QtGui = core, gui
    return pythonqt, core, gui


@pytest.fixture
def fake_qt():
    """Load a fresh module against the fake PythonQt; restore sys.modules afterwards."""
    saved = {}
    loaded = []

    def load(module_name, **options):
        pythonqt, core, gui = build_qt(**options)
        for name, module in (("PythonQt", pythonqt), ("PythonQt.QtCore", core), ("PythonQt.QtGui", gui)):
            saved.setdefault(name, sys.modules.get(name))
            sys.modules[name] = module
        saved.setdefault(module_name, sys.modules.get(module_name))
        sys.modules.pop(module_name, None)
        module = importlib.import_module(module_name)
        loaded.append(module_name)
        return module

    yield load
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    for name in loaded:
        package, _, attr = name.rpartition(".")
        original = saved.get(name)
        if package in sys.modules:
            if original is None:
                sys.modules[package].__dict__.pop(attr, None)
            else:
                setattr(sys.modules[package], attr, original)


class FakeClient:
    """Signals and calls the dock uses from AidusAgentusClient."""

    def __init__(self, transport=True):
        self.chatUpdate = FakeSignal()
        self.stateChanged = FakeSignal()
        self.transport = SimpleNamespace() if transport else None
        self.prompts = []
        self.reconnects = 0

    def send_user_prompt(self, text):
        self.prompts.append(text)
        return True

    def reconnect(self):
        self.reconnects += 1
        return True


@pytest.fixture
def fake_client():
    return FakeClient
