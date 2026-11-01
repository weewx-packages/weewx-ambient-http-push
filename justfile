default: fast

fast:
    PYTHONPATH=bin python -m pytest -q tests
