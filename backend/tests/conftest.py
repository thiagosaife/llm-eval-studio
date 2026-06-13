"""Point storage at a throwaway DB so tests never touch real run history."""
import os
import tempfile

# Must run before `app` is imported (conftest is loaded before test modules),
# because storage resolves its DB path at import time.
_db = os.path.join(tempfile.mkdtemp(prefix="llm-eval-test-"), "eval.db")
os.environ["LLM_EVAL_DB"] = _db
