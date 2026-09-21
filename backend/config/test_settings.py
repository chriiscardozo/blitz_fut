"""Settings used only while running the automated test suite."""

import os


os.environ.setdefault("BLITZ_FUT_DEBUG", "true")
os.environ.setdefault("BLITZ_FUT_SECRET_KEY", "blitz-fut-test-key-not-for-deployment")

from config.settings import *  # noqa: E402,F403
