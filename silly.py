"""Silly development entry point.

The shared local runtime module stays separate from this stable product entry
point. Installed builds receive that implementation as silly.py.
"""
import runpy

runpy.run_module("atticus", run_name="__main__")
