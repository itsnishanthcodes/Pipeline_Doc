import os
import tempfile

# Tests must never touch a real PostgreSQL server, GitHub or the LLM API.
_tmp = tempfile.mkdtemp(prefix="rootcause-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LLM_API_KEY"] = ""
os.environ["GITHUB_TOKEN"] = ""
os.environ["GITHUB_WEBHOOK_SECRET"] = ""
os.environ["JWT_SECRET"] = "test-secret-for-unit-tests-only"
os.environ["APP_ENV"] = "development"
