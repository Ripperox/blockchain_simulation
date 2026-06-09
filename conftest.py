"""Root conftest.

Its mere presence makes pytest add the project root to sys.path so the test
modules can `import app` regardless of how pytest is invoked.
"""
