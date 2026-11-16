# this_file: src/fontlab_aidus_agentus/core_launcher.py
"""Script adapter launched by QProcess using the configured external Python."""
from fontlab_aidus_agentus.boot import main
raise SystemExit(main())
