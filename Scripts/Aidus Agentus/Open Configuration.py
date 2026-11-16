# this_file: Scripts/Aidus Agentus/Open Configuration.py
"""Open the active host configuration from FontLab's Scripts menu."""

try:
    from fontlab_aidus_agentus.launchers import open_configuration
except ImportError:
    print(
        "[Aidus Agentus] Install or update fontlab-aidus-agentus in FontLab's Python path. "
        "Keep the AI brain in a separate Python 3.13+ environment. "
        "Setup (repository access required): "
        "https://github.com/fontlabcom/fontlab-aidus-agentus/blob/main/README.md"
    )
else:
    open_configuration()
