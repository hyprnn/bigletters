#!/usr/bin/env python3
"""Run bigletters straight from a checkout:  python3 bigletter.py [options]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bigletters.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
