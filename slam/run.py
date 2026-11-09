#!/usr/bin/env python3
"""Single entry point for experiments (runs in .venv-headcam; steps run in their own envs).

  python -m slam.run experiments/<exp>/config.yaml [--dry-run] [--repro slam.E3[=N]]

See slam/pipeline/orchestrator.py and experiments/README.md.
"""
from slam.pipeline.orchestrator import main

if __name__ == "__main__":
    main()
