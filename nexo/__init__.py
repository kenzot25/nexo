"""nexo - extract · build · cluster · analyze · report."""


def __getattr__(name):
    # Lazy imports so `nexo install` works before heavy deps are in place.
    _map = {
        "extract": ("nexo.extract", "extract"),
        "collect_files": ("nexo.extract", "collect_files"),
        "build_from_json": ("nexo.build", "build_from_json"),
        "cluster": ("nexo.cluster", "cluster"),
        "score_all": ("nexo.cluster", "score_all"),
        "cohesion_score": ("nexo.cluster", "cohesion_score"),
        "god_nodes": ("nexo.analyze", "god_nodes"),
        "surprising_connections": ("nexo.analyze", "surprising_connections"),
        "suggest_questions": ("nexo.analyze", "suggest_questions"),
        "generate": ("nexo.report", "generate"),
        "to_json": ("nexo.export", "to_json"),
        "to_html": ("nexo.export", "to_html"),
    }
    if name in _map:
        import importlib
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'nexo' has no attribute {name!r}")
