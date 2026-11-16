# this_file: src/fontlab_aidus_agentus/boot.py
"""Production ACP entrypoint for external Python 3.13+ interpreters."""
import sys


def main() -> int:
    """Use the retained AgentPool brain and fail clearly for host interpreters."""
    if sys.version_info < (3, 13):
        print("The Aidus brain needs external Python 3.13+; install fontlab-aidus-agentus[brain] there.", file=sys.stderr)
        return 1
    try:
        from fontlab_aidus_agentus.core.boot import main as core_main
    except ImportError as exc:
        print("Install fontlab-aidus-agentus[brain] in this Python 3.13+ environment: " + str(exc), file=sys.stderr)
        return 1
    return core_main()

if __name__ == "__main__":
    raise SystemExit(main())
