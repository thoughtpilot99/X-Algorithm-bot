"""Paths and configuration loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(REPO_ROOT / ".env")

DATA_DIR = Path(os.environ.get("XAUDIT_DATA_DIR", REPO_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
REPORTS_DIR = Path(os.environ.get("XAUDIT_REPORTS_DIR", REPO_ROOT / "reports"))
ALGO_REPO_DIR = Path(os.environ.get("XAUDIT_ALGO_REPO", DATA_DIR / "x-algorithm"))
ALGO_REPO_URL = "https://github.com/xai-org/x-algorithm"
CONFIG_DIR = Path(__file__).resolve().parent / "config"


@lru_cache
def config() -> dict:
    with open(CONFIG_DIR / "accounts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clients() -> dict[str, dict]:
    return config()["clients"]


def analysis_cfg() -> dict:
    return config()["analysis"]
