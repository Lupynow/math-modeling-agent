from __future__ import annotations

import argparse

from .config import get_settings
from .runtime import build_runtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Math Modeling Agent maintenance commands")
    parser.add_argument("command", choices=["reindex", "ready"])
    args = parser.parse_args()
    runtime = build_runtime(get_settings())
    if runtime.error:
        print(runtime.error)
        return 1
    if args.command == "reindex":
        assert runtime.knowledge_store is not None
        print(f"Indexed {runtime.knowledge_store.reindex()} knowledge chunks.")
    else:
        assert runtime.repository is not None and runtime.knowledge_store is not None
        print(
            {
                "database": runtime.repository.ping(),
                "qdrant": runtime.knowledge_store.ping(),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
