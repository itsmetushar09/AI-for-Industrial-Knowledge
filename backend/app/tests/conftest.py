"""Keep automated tests isolated from developer and production credentials."""

import os
import uuid

import pytest

# Environment variables override values loaded from backend/.env. Blank values
# are intentionally normalized to None by Settings.
os.environ["DATABASE_URL"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_PUBLISHABLE_KEY"] = ""
os.environ["SUPABASE_SECRET_KEY"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["AI_PROVIDER"] = "gemini"


@pytest.fixture(autouse=True)
def authenticated_api_user():
    """Run non-authentication endpoint tests as a verified administrator."""

    from app.core.auth import AuthenticatedUser, get_current_user
    from app.main import app
    from app.models.enums import UserRole

    user = AuthenticatedUser(
        id=uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        email="admin@example.com",
        role=UserRole.ADMINISTRATOR,
        department_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)
