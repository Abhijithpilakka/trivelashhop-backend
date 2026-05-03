#!/usr/bin/env python3
"""
scripts/hash_password.py
Usage:
    python scripts/hash_password.py
    → prompts for a password, prints the bcrypt hash
    → paste the hash into your .env as ADMIN_PASSWORD_HASH
"""

import sys

try:
    from passlib.context import CryptContext
except ImportError:
    print("Run: pip install passlib[bcrypt]")
    sys.exit(1)

import getpass

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
pw = getpass.getpass("Enter admin password: ")
confirm = getpass.getpass("Confirm: ")

if pw != confirm:
    print("Passwords do not match.")
    sys.exit(1)

hashed = ctx.hash(pw)
print(f"\nADMIN_PASSWORD_HASH={hashed}")
print("\nAdd this line to your .env file.")
