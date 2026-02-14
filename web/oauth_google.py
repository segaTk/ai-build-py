import urllib.parse
import secrets

from state_storage import state_storage
from config import settings


def generate_google_oauth_redirect_uri():
    random_state = secrets.token_urlsafe(16)
    state_storage.add(random_state)

    query_params = {
        "client_id": settings.OAUTH_GOOGLE_CLIENT_ID,
        "redirect_uri": "http://ai-build.space/auth/google/callback",  # ← ОБЯЗАТЕЛЬНО /callback
        "response_type": "code",
        "scope": "openid profile email",
        "access_type": "offline",
        "state": random_state,
    }

    query_string = urllib.parse.urlencode(query_params)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
