"""
Backend Tools Package
=====================

This directory contains standalone operational helpers (email proxy, webhook handlers,
conference calls) that can also be imported by the WhatsApp agent tool layer.

WHY THIS MATTERS: treating these scripts as an importable package lets the agent
reuse the same logic without copy/paste, while keeping the scripts runnable via
`python -m tools.<module>` for manual debugging.
"""

