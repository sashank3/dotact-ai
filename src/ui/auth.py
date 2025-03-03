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
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
import boto3
from botocore.exceptions import ClientError

# Ensure Python can find your "src" folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import global configuration
from src.global_config import (
    CHAINLIT_APP_PATH, 
    CHAINLIT_PORT, 
    AUTH_PORT, 
    AUTH_REDIRECT_URI, 
    AUTH_SESSION_MAX_AGE,
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

# Global variable to track if Chainlit is running
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
    """Handle OAuth callback from Google."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(status_code=500, detail="Authentication not configured")
    
    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Failed to exchange code for token: {error_text}")
                    raise HTTPException(status_code=500, detail="Authentication failed")
                
                token_data = await resp.json()
                
        # Get user info with the access token
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(userinfo_url, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"Failed to get user info: {error_text}")
                    raise HTTPException(status_code=500, detail="Failed to get user info")
                
                user_info = await resp.json()
                
        # Extract user details
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        
        if not email:
            logger.error("No email found in user info")
            raise HTTPException(status_code=500, detail="Email not found in user info")
        
        # Register or authenticate user with Cognito if available
        cognito_token = None
        if cognito_client:
            try:
                # Try to find the user in Cognito
                cognito_user_exists = False
                try:
                    # Check if user exists in Cognito
                    cognito_client.admin_get_user(
                        UserPoolId=COGNITO_USER_POOL_ID,
                        Username=email
                    )
                    cognito_user_exists = True
                    logger.info(f"User {email} found in Cognito")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'UserNotFoundException':
                        logger.info(f"User {email} not found in Cognito, will create")
                    else:
                        logger.error(f"Error checking Cognito user: {str(e)}")
                
                # Create user if they don't exist
                if not cognito_user_exists:
                    try:
                        # Create the user in Cognito
                        cognito_client.admin_create_user(
                            UserPoolId=COGNITO_USER_POOL_ID,
                            Username=email,
                            UserAttributes=[
                                {'Name': 'email', 'Value': email},
                                {'Name': 'email_verified', 'Value': 'true'},
                                {'Name': 'name', 'Value': name or email}
                            ],
                            MessageAction='SUPPRESS'  # Don't send welcome email
                        )
                        logger.info(f"Created user {email} in Cognito")
                    except Exception as e:
                        logger.error(f"Failed to create Cognito user: {str(e)}")
                
                # Get Cognito tokens for the user
                try:
                    # This is a simplified approach - in production, you might want to use
                    # admin_initiate_auth and admin_respond_to_auth_challenge for more control
                    auth_response = cognito_client.admin_set_user_password(
                        UserPoolId=COGNITO_USER_POOL_ID,
                        Username=email,
                        Password=f"Google-{token_data['access_token'][:10]}",  # Temporary password
                        Permanent=True
                    )
                    
                    # Now authenticate the user
                    auth_response = cognito_client.admin_initiate_auth(
                        UserPoolId=COGNITO_USER_POOL_ID,
                        ClientId=COGNITO_CLIENT_ID,
                        AuthFlow='ADMIN_NO_SRP_AUTH',
                        AuthParameters={
                            'USERNAME': email,
                            'PASSWORD': f"Google-{token_data['access_token'][:10]}"
                        }
                    )
                    
                    # Store the Cognito tokens
                    cognito_token = auth_response.get('AuthenticationResult', {}).get('IdToken')
                    logger.info(f"Got Cognito token for user {email}")
                except Exception as e:
                    logger.error(f"Failed to authenticate with Cognito: {str(e)}")
            except Exception as e:
                logger.error(f"Cognito integration error: {str(e)}")
        
        # Create session data
        session_data = {
            "email": email,
            "name": name,
            "picture": picture,
            "cognito_token": cognito_token  # Include Cognito token if available
        }
        
        # Serialize and set cookie
        cookie_value = serializer.dumps(session_data)
        logger.debug(f"Setting cookie with value: {cookie_value}")
        
        # Create redirect response and set cookie
        redirect_response = RedirectResponse(url="/app")
        redirect_response.set_cookie(
            key="session-data", 
            value=cookie_value,
            max_age=MAX_AGE,
            httponly=True,
            path="/",  # Important: make cookie available for all paths
            samesite="lax"
        )
        
        logger.info(f"Authentication successful for {email}")
        return redirect_response
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@auth_app.get("/logout")
async def logout(response: Response):
    """Log out the user by clearing the session cookie."""
    response.delete_cookie(key="session-data", path="/")
    logger.info("User logged out")
    return RedirectResponse(url="/")

@auth_app.get("/app")
async def chainlit_redirect(request: Request):
    """Redirect to Chainlit UI after verifying session."""
    try:
        # Debug the cookie value
        cookie_value = request.cookies.get("session-data", "")
        logger.debug(f"Cookie value in /app route: {cookie_value}")
        
        # Verify session
        try:
            session_data = serializer.loads(cookie_value, max_age=MAX_AGE)
            logger.info(f"Valid session confirmed for {session_data.get('email')}. Redirecting to Chainlit UI")
        except (BadSignature, SignatureExpired) as e:
            logger.warning(f"Invalid session in /app route: {str(e)}")
            return RedirectResponse(url="/")
        
        # Start Chainlit if not already running
        chainlit_started = start_chainlit()
        
        # Wait a moment to ensure Chainlit has time to start
        if chainlit_started:
            await asyncio.sleep(2)
        
        # Redirect to Chainlit UI
        chainlit_url = f"http://localhost:{CHAINLIT_PORT}"
        logger.info(f"Redirecting to Chainlit UI at {chainlit_url}")
        return RedirectResponse(url=chainlit_url)
    except Exception as e:
        logger.error(f"Error in chainlit_redirect: {str(e)}")
        logger.error(traceback.format_exc())
        return RedirectResponse(url="/")

@auth_app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the server shuts down."""
    global chainlit_process
    if chainlit_process is not None:
        logger.info("Shutting down Chainlit process")
        chainlit_process.terminate()
        chainlit_process = None

def start_chainlit():
    """Start the Chainlit server if not already running."""
    global chainlit_process
    
    if chainlit_process is not None:
        logger.info("Chainlit server is already running")
        return True
    
    try:
        logger.info(f"Starting Chainlit server on port {CHAINLIT_PORT} with app {CHAINLIT_APP_PATH}")
        
        # Fix: Use --port instead of -p for Chainlit
        cmd = [
            "chainlit", "run", 
            CHAINLIT_APP_PATH,
            "--port", str(CHAINLIT_PORT),
            "--headless"  # Run without opening browser automatically
        ]
        
        # Start Chainlit as a subprocess
        chainlit_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        logger.info("Chainlit server started")
        return True
    except Exception as e:
        logger.error(f"Failed to start Chainlit: {str(e)}")
        return False

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