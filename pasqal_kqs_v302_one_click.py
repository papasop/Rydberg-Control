#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy compatibility entry point for v3.0.2 packaging.

This file no longer contains verifier logic. It delegates to
verify_v302_strict_v1.py, which performs file-byte source identity checks,
ranking-certificate verification, expected-pass classification, and
self-contained bundle staging.

Changing this legacy entry point changes its file-byte hash. It must not be
treated as an original v3.0.2 source identity.
"""

from __future__ import annotations

from verify_v302_strict_v1 import main


if __name__ == "__main__":
    raise SystemExit(main())
