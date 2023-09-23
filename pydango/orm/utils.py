import sys
from functools import lru_cache

from pydantic.typing import evaluate_forwardref


def get_globals(cls):
    if cls.__module__ in sys.modules:
        globalns = sys.modules[cls.__module__].__dict__.copy()
    else:
        globalns = {}
    return globalns


@lru_cache
def evaluate_forward_ref(source, model, **localns):
    return evaluate_forwardref(model, get_globals(source), localns)
