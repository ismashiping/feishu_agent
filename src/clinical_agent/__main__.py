"""Delegate module execution to the shared CLI."""

from clinical_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
