# this_file: Scripts/Aidus Agentus/Enable FontLab MCP.py
"""Enable native FontLab MCP from FontLab's Scripts menu."""

try:
    from fontlab_aidus_agentus.launchers import enable_mcp
except ImportError:
    print(
        "[Aidus Agentus] Install or update fontlab-aidus-agentus in FontLab's Python path. "
        "Keep the AI brain in a separate Python 3.13+ environment. "
        "Setup (repository access required): "
        "https://github.com/fontlabcom/fontlab-aidus-agentus/blob/main/README.md"
    )
else:
    enable_mcp()
