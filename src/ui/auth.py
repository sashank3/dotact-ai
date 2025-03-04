"""
Authentication module for handling user login, session management, and UI routing.
This module provides FastAPI routes for authentication flows and redirects to the Chainlit UI.
"""
import os
import logging
import sys
import subprocess
import time
import traceback
import aiohttp
import asyncio
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
import boto3
from botocore.exceptions import ClientError
import base64
import requests
from urllib.parse import urlencode
import json

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import (
    CHAINLIT_APP_PATH, 
    CHAINLIT_PORT, 
    AUTH_PORT, 
    AUTH_REDIRECT_URI, 
    AUTH_SESSION_MAX_AGE,
    AUTH_TOKEN_FILE,
)

# Configure logging
logger = logging.getLogger(__name__)

# Log the loaded configuration
logger.info(f"Using Chainlit app path: {CHAINLIT_APP_PATH}")
logger.info(f"Using Chainlit port: {CHAINLIT_PORT}")
logger.info(f"Using Auth port: {AUTH_PORT}")
logger.info(f"Using Auth redirect URI: {AUTH_REDIRECT_URI}")

# Constants
SECRET_KEY = os.getenv("FASTAPI_SECRET_KEY", "default-secret-key")
MAX_AGE = AUTH_SESSION_MAX_AGE
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = AUTH_REDIRECT_URI

# Cognito configuration
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

# Create serializer for secure cookie data
serializer = URLSafeSerializer(SECRET_KEY)

# Create FastAPI app
auth_app = FastAPI(title="Keenmind Authentication")

# Global variables to track service status
is_chainlit_running = False
chainlit_process = None

# Initialize Cognito client if credentials are available
cognito_client = None
if COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID:
    try:
        cognito_client = boto3.client('cognito-idp', region_name=os.getenv("AWS_REGION", "us-east-2"))
        logger.info("Cognito client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Cognito client: {str(e)}")

@auth_app.get("/")
async def home(request: Request):
    """Home route that redirects to login if no session, or to app if session exists."""
    try:
        # Debug the cookie value
        cookie_value = request.cookies.get("session-data", "")
        logger.debug(f"Cookie value: {cookie_value}")
        
        session_data = serializer.loads(cookie_value, max_age=MAX_AGE)
        logger.info(f"Valid session found for {session_data.get('email')}. Redirecting to app")
        return RedirectResponse(url="/app")
    except (BadSignature, SignatureExpired) as e:
        logger.info(f"No valid session: {str(e)}. Redirecting to login")
        return RedirectResponse(url="/login/google")

@auth_app.get("/login/google")
async def login_google():
    """Initiate Google OAuth login flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(status_code=500, detail="Authentication not configured")
    
    # Google OAuth authorization URL
    auth_url = "https://accounts.google.com/o/oauth2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    # Construct the authorization URL with parameters
    auth_request_url = f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    logger.info(f"Redirecting to Google OAuth: {auth_request_url}")
    
    return RedirectResponse(url=auth_request_url)

@auth_app.get("/callback")
async def oauth_callback(code: str, request: Request, response: Response):
    """Handle the OAuth callback from Google."""
    try:
        # Exchange code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_info = token_response.json()
        
        # Get user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {token_info['access_token']}"}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()
        
        logger.info(f"Google user authenticated: {user_info.get('email')}")
        
        # Check if user exists in Cognito or create a new one
        user_email = user_info.get('email')
        user_name = user_info.get('name', 'User')
        cognito_user_id = None
        cognito_tokens = {}
        
        try:
            # Try to check if user exists in Cognito
            if cognito_client:
                try:
                    # List users with filter by email
                    user_response = cognito_client.list_users(
                        UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                        Filter=f'email = "{user_email}"'
                    )
                    
                    if user_response.get('Users') and len(user_response['Users']) > 0:
                        cognito_user_id = user_response['Users'][0]['Username']
                        logger.info(f"Found existing Cognito user: {cognito_user_id}")
                    else:
                        # Create new user in Cognito
                        try:
                            create_response = cognito_client.admin_create_user(
                                UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                                Username=user_email,
                                UserAttributes=[
                                    {'Name': 'email', 'Value': user_email},
                                    {'Name': 'email_verified', 'Value': 'true'},
                                    {'Name': 'name', 'Value': user_name}
                                ],
                                MessageAction='SUPPRESS'
                            )
                            cognito_user_id = create_response['User']['Username']
                            logger.info(f"Created new Cognito user: {cognito_user_id}")
                            
                            # Set a random password for the new user (required for admin_initiate_auth)
                            import secrets
                            temp_password = secrets.token_urlsafe(16)
                            cognito_client.admin_set_user_password(
                                UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                                Username=cognito_user_id,
                                Password=temp_password,
                                Permanent=True
                            )
                            logger.info(f"Set password for new user: {cognito_user_id}")
                        except cognito_client.exceptions.UsernameExistsException:
                            logger.info(f"User already exists in Cognito: {user_email}")
                            cognito_user_id = user_email
                except Exception as e:
                    logger.error(f"Error checking/creating Cognito user: {str(e)}")
        except Exception as e:
            logger.error(f"Error managing Cognito user: {str(e)}")
        
        # Prepare session data
        session_data = {
            'user_id': cognito_user_id or user_email,
            'email': user_email,
            'name': user_name,
            'google_id_token': token_info.get('id_token'),
            'google_access_token': token_info.get('access_token'),
            'google_refresh_token': token_info.get('refresh_token'),
            'expires_at': int(time.time()) + int(token_info.get('expires_in', 3600))
        }
        
        # Create signed cookie
        cookie_value = serializer.dumps(session_data)
        logger.debug(f"Setting cookie with value: {cookie_value[:20]}...")
        
        # Create a response with the cookie
        redirect_resp = RedirectResponse(url="/app")
        
        # Set the cookie on the response with proper attributes
        redirect_resp.set_cookie(
            key="session-data",
            value=cookie_value,
            httponly=True,
            max_age=MAX_AGE,
            path="/",  # Important: set cookie for all paths
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"  # Important for redirects
        )
        
        logger.info(f"Session created for {user_email}. Redirecting to app.")
        return redirect_resp
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"OAuth callback error: {str(e)}\n{error_details}")
        return HTMLResponse(f"<h1>Authentication Error</h1><p>{str(e)}</p>")

@auth_app.get("/logout")
async def logout(response: Response):
    """Log out the user by clearing the session cookie."""
    response.delete_cookie(key="session-data", path="/")
    logger.info("User logged out")
    return RedirectResponse(url="/")

@auth_app.get("/app")
async def chainlit_redirect(request: Request):
    """Redirect to Chainlit app if authenticated."""
    try:
        cookie_value = request.cookies.get("session-data", "")
        logger.debug(f"Cookie value in /app route: {cookie_value[:20] if cookie_value else 'None'}")
        
        if not cookie_value:
            logger.error("No session cookie found")
            return RedirectResponse(url="/login/google")
        
        try:
            session_data = serializer.loads(cookie_value, max_age=MAX_AGE)
            logger.info(f"Valid session confirmed for {session_data.get('email')}. Redirecting to Chainlit UI")
            
            # Start Chainlit server if needed
            if not is_chainlit_running:
                start_chainlit()
            
            # Encode session data for URL
            encoded_session = base64.urlsafe_b64encode(cookie_value.encode()).decode()
            
            # Write token to file for Chainlit to access
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(AUTH_TOKEN_FILE), exist_ok=True)
                
                # Create token data structure with user info for easier access
                token_data = {
                    "token": encoded_session,
                    "email": session_data.get("email"),
                    "name": session_data.get("name"),
                    "timestamp": int(time.time())
                }
                
                # Write to file
                with open(AUTH_TOKEN_FILE, 'w') as f:
                    json.dump(token_data, f)
                
                logger.info(f"Wrote authentication token to {AUTH_TOKEN_FILE}")
            except Exception as e:
                logger.error(f"Error writing token to file: {str(e)}")
            
            # Set environment variable as backup method
            os.environ["CHAINLIT_AUTH_TOKEN"] = encoded_session
            
            # Use multiple reliable methods to pass the token
            # Method 1: Standard URL parameter with proper encoding
            from urllib.parse import urlencode
            params = {'auth_token': encoded_session}
            chainlit_url = f"http://localhost:{CHAINLIT_PORT}?{urlencode(params)}"
            
            # Method 2: Try setting a cookie that Chainlit might be able to access
            response = RedirectResponse(url=chainlit_url)
            response.set_cookie(
                key="chainlit-auth-token",
                value=encoded_session,
                httponly=False,  # Allow JavaScript access
                max_age=MAX_AGE,
                path="/",
                secure=False,
                samesite="lax"
            )
            
            logger.info(f"Redirecting to Chainlit UI at {chainlit_url}")
            logger.info(f"Auth token length: {len(encoded_session)}")
            logger.debug(f"Auth token (first 20 chars): {encoded_session[:20]}...")
            
            return response
        except (BadSignature, SignatureExpired) as e:
            logger.error(f"Invalid session in /app route: {str(e)}")
            return RedirectResponse(url="/login/google")
    except Exception as e:
        logger.error(f"Error in /app route: {str(e)}")
        return RedirectResponse(url="/login/google")

@auth_app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the server shuts down."""
    global chainlit_process, is_chainlit_running
    if chainlit_process is not None:
        logger.info("Shutting down Chainlit server")
        try:
            chainlit_process.terminate()
            chainlit_process.wait(timeout=5)
            logger.info("Chainlit server terminated")
        except Exception as e:
            logger.error(f"Error terminating Chainlit: {str(e)}")
        finally:
            chainlit_process = None
            is_chainlit_running = False

def start_chainlit():
    """Start the Chainlit server in a subprocess."""
    global chainlit_process, is_chainlit_running
    
    if chainlit_process is not None and chainlit_process.poll() is None:
        # Process already running
        logger.info("Chainlit server already running")
        is_chainlit_running = True
        return
        
    command = f"chainlit run {CHAINLIT_APP_PATH} --port {CHAINLIT_PORT} --headless"
    
    logger.info(f"Starting Chainlit server on port {CHAINLIT_PORT} with app {CHAINLIT_APP_PATH}")
    
    try:
        # Start chainlit in a subprocess
        chainlit_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give Chainlit time to start up
        time.sleep(2)
        
        if chainlit_process.poll() is None:
            # Process is still running, which is good
            is_chainlit_running = True
            logger.info("Chainlit server started")
        else:
            # Process exited already, which is bad
            stdout, stderr = chainlit_process.communicate()
            logger.error(f"Chainlit server failed to start: {stderr}")
            chainlit_process = None
    except Exception as e:
        logger.error(f"Error starting Chainlit: {str(e)}")
        chainlit_process = None

def run_auth_server(host="0.0.0.0", port=None):
    """Start the authentication server."""
    if port is None:
        port = AUTH_PORT
        
    logger.info(f"Starting authentication server on port {port}")
    
    # Use uvicorn.Config and Server classes for thread-safe operation
    config = uvicorn.Config(
        app=auth_app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    server.run() 