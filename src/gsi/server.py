import logging
import os
import time
import json
import base64
import subprocess
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
import requests
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

from src.global_config import GLOBAL_CONFIG, BASE_DIR
from src.data.gsi.extraction.state_manager import state_manager

# --- Load Environment Variables & Configuration ---
load_dotenv()

# --- Google OAuth Configuration ---
SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("FASTAPI_SECRET_KEY environment variable not set!")

# --- Session Management (using itsdangerous) ---
serializer = URLSafeTimedSerializer(SECRET_KEY)
MAX_AGE = 3600  # Session timeout in seconds (1 hour)

# --- FastAPI App Initialization ---
app = FastAPI()

# --- GSI Data Model ---
class GameStateUpdate(BaseModel):
    provider: dict = {}
    map: dict = {}
    player: dict = {}
    hero: dict = {}
    abilities: dict = {}
    items: dict = {}
    buildings: dict = {}
    draft: dict = {}
    minimap: dict = {}

# --- Authentication Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page, redirects to login if not authenticated."""
    try:
        session_data = serializer.loads(request.cookies.get("session-data", ""), max_age=MAX_AGE)
        username = session_data.get('username', 'User')
        return f"""
            <html>
                <head><title>KeenMind</title></head>
                <body>
                    <h1>Welcome, {username}!</h1>
                    <p>You are logged in. <a href="/app">Go to App</a></p>
                    <p><a href="/logout">Logout</a></p>
                </body>
            </html>
        """
    except (BadSignature, SignatureExpired):
        return """
            <html>
                <head><title>KeenMind Login</title></head>
                <body>
                    <h1>KeenMind</h1>
                    <p>You are not logged in. <a href="/login/google">Login with Google</a></p>
                </body>
            </html>
        """

@app.get("/login/google")
async def login_google():
    """Redirect to Cognito Hosted UI with Google as identity provider"""
    cognito_domain = os.getenv("COGNITO_DOMAIN")
    client_id = os.getenv("COGNITO_CLIENT_ID")
    redirect_uri = os.getenv("COGNITO_REDIRECT_URI")

    if not all([cognito_domain, client_id, redirect_uri]):
        raise HTTPException(status_code=500, detail="Missing Cognito configuration")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "identity_provider": "Google",
        "scope": "openid email profile"
    }
    auth_url = f"https://{cognito_domain}/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@app.get("/callback")
async def cognito_callback(code: str, request: Request, response: Response):
    """Handle Cognito callback with authorization code"""
    cognito_domain = os.getenv('COGNITO_DOMAIN')
    client_id = os.getenv("COGNITO_CLIENT_ID")
    client_secret = os.getenv("COGNITO_CLIENT_SECRET")
    redirect_uri = os.getenv("COGNITO_REDIRECT_URI")

    if not all([cognito_domain, client_id, redirect_uri]):
        raise HTTPException(status_code=500, detail="Missing Cognito configuration")

    token_url = f"https://{cognito_domain}/oauth2/token"

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    if client_secret:
        auth_str = f"{client_id}:{client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f'Basic {encoded_auth}'

    try:
        token_response = requests.post(token_url, data=urlencode(data), headers=headers)
        token_response.raise_for_status()
        token_data = token_response.json()

        id_token = token_data['id_token']
        _, payload_encoded, _ = id_token.split('.')
        payload = json.loads(base64.b64decode(payload_encoded + "==").decode('utf-8'))

        session_data = {
            "username": payload.get("cognito:username", payload.get("email")),
            "email": payload["email"],
            "cognito_id": payload["sub"],
            "id_token": id_token
        }

        response = RedirectResponse(url="/app")
        response.set_cookie(key="session-data", value=serializer.dumps(session_data), httponly=True, max_age=MAX_AGE)
        os.environ["KEENMIND_USER"] = payload["email"]
        return response

    except requests.exceptions.RequestException as e:
        logging.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        logging.error(f"Token parsing error: {e}")
        raise HTTPException(status_code=400, detail="Invalid token data")

@app.get("/logout")
async def logout(response: Response):
    """Logs the user out by clearing the session and redirecting to Cognito logout."""
    cognito_domain = os.getenv("COGNITO_DOMAIN")
    client_id = os.getenv("COGNITO_CLIENT_ID")
    logout_uri = os.getenv("COGNITO_LOGOUT_URI")

    if not all([cognito_domain, client_id, logout_uri]):
        raise HTTPException(status_code=500, detail="Missing Cognito configuration for logout")

    response = RedirectResponse(url="/")
    response.delete_cookie("session-data")

    logout_url = f"https://{cognito_domain}/logout?client_id={client_id}&logout_uri={logout_uri}"
    return RedirectResponse(logout_url)

@app.get("/user-info")
async def user_info(request: Request):
    """(Optional) Endpoint to retrieve user information from the session."""
    try:
        session_data = serializer.loads(request.cookies.get("session-data", ""), max_age=MAX_AGE)
        return {
            "username": session_data.get("username"),
            "email": session_data.get("email"),
        }
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Not authenticated")

# --- GSI Endpoints ---

@app.post("/")
async def receive_game_state(update: GameStateUpdate):
    """Receives and stores game state updates from Dota 2."""
    state_dict = update.dict()
    if not any(state_dict.values()):
        logging.debug("[GSI SERVER] Received empty update")
        return {"status": "empty"}

    logging.debug("[GSI SERVER] Received state update")
    state_manager.update_state(state_dict)
    return {"status": "received"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# --- Chainlit Integration ---

@app.on_event("startup")
async def startup_event():
    """Start Chainlit when the server starts"""
    chainlit_app_path = os.path.join(BASE_DIR, "src/ui/chainlit_app.py")
    subprocess.Popen(
        ["chainlit", "run", chainlit_app_path, "--port", "8000", "--host", "127.0.0.1"],
        env=os.environ.copy(),
        shell=False
    )

@app.get("/app")
async def chainlit_redirect(request: Request):
    """Validate session before redirecting to Chainlit"""
    try:
        serializer.loads(request.cookies.get("session-data", ""), max_age=MAX_AGE)
        return RedirectResponse("http://localhost:8000")
    except (BadSignature, SignatureExpired):
        return RedirectResponse(url="/login/google")

# --- Server Startup ---

def run_server():
    """Starts the FastAPI server (using uvicorn)."""
    logging.info(f"Starting server on port 8000")
    logging.info(f"GSI config path: {GLOBAL_CONFIG['data']['gsi']['dota2']['gsi_config_path']}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    ) 