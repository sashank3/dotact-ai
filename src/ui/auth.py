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
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
import boto3
import base64
import requests
import json
import webbrowser
import threading

# Simple, reliable path handling
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    # Running in development environment
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, root_dir)

# Import configuration
from src.config import config
from src.bootstrap import is_frozen

# Configure logging
logger = logging.getLogger(__name__)

# Log the loaded configuration
logger.info(f"Using Chainlit app path: {config.chainlit_app_path}")
logger.info(f"Using Chainlit port: {config.chainlit_port}")
logger.info(f"Using Auth port: {config.auth_port}")
logger.info(f"Using Auth redirect URI: {config.auth_redirect_uri}")

# Create serializer for secure cookie data
serializer = URLSafeSerializer(config.fastapi_secret_key)

# Create FastAPI app
auth_app = FastAPI(title="Keenplay Authentication")

# Global variables to track service status
is_chainlit_running = False
chainlit_process = None

# Initialize Cognito client if credentials are available
cognito_client = None
if config.cognito_user_pool_id and config.cognito_client_id:
    try:
        # Create session with explicit credentials from config
        session = boto3.Session(
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            region_name=config.aws_region
        )
        cognito_client = session.client('cognito-idp')
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
        
        session_data = serializer.loads(cookie_value, max_age=config.auth_session_max_age)
        logger.info(f"Valid session found for {session_data.get('email')}. Redirecting to app")
        return RedirectResponse(url="/app")
    except (BadSignature, SignatureExpired) as e:
        logger.info(f"No valid session: {str(e)}. Redirecting to login")
        return RedirectResponse(url="/direct-login")

@auth_app.get("/login/google")
async def login_google(clear_cookies: bool = False, response: Response = None):
    """Initiate Google OAuth login flow."""
    if not config.google_client_id or not config.google_client_secret:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(status_code=500, detail="Authentication not configured")
    
    # Clear cookies if requested
    if clear_cookies and response:
        logger.info("Clearing existing session cookies")
        response.delete_cookie(key="session-data", path="/")
        response.delete_cookie(key="chainlit-auth-token", path="/")
    
    # Google OAuth authorization URL
    auth_url = "https://accounts.google.com/o/oauth2/auth"
    params = {
        "client_id": config.google_client_id,
        "redirect_uri": config.auth_redirect_uri,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent",  # Force prompt to ensure we get a refresh token
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
            "client_id": config.google_client_id,
            "client_secret": config.google_client_secret,
            "code": code,
            "redirect_uri": config.auth_redirect_uri,
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
                        UserPoolId=config.cognito_user_pool_id,
                        Filter=f'email = "{user_email}"'
                    )
                    
                    if user_response.get('Users') and len(user_response['Users']) > 0:
                        cognito_user_id = user_response['Users'][0]['Username']
                        logger.info(f"Found existing Cognito user: {cognito_user_id}")
                    else:
                        # Create new user in Cognito
                        try:
                            create_response = cognito_client.admin_create_user(
                                UserPoolId=config.cognito_user_pool_id,
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
                                UserPoolId=config.cognito_user_pool_id,
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
            max_age=config.auth_session_max_age,
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
            return RedirectResponse(url="/direct-login")
        
        try:
            # Load session data
            session_data = serializer.loads(cookie_value, max_age=config.auth_session_max_age)
            
            # Additional check for token expiration
            current_time = int(time.time())
            token_expiry = session_data.get('expires_at', 0)
            
            # If token is expired or will expire soon (within 5 minutes)
            if current_time > (token_expiry - 300):
                logger.warning(f"Auth token expired or expiring soon. Current time: {current_time}, Expiry: {token_expiry}")
                # Redirect to direct login which clears cookies and redirects to Google login
                return RedirectResponse(url="/direct-login")
                
            logger.info(f"Valid session confirmed for {session_data.get('email')}. Redirecting to Chainlit UI")
            
            # Start Chainlit server if needed
            if not is_chainlit_running:
                start_chainlit()
            
            # Encode session data for URL
            encoded_session = base64.urlsafe_b64encode(cookie_value.encode()).decode()
            
            # Write token to file for Chainlit to access
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(config.auth_token_file), exist_ok=True)
                
                # Create token data structure with user info for easier access
                token_data = {
                    "token": encoded_session,
                    "email": session_data.get("email"),
                    "name": session_data.get("name"),
                    "timestamp": int(time.time())
                }
                
                # Write to file
                with open(config.auth_token_file, 'w') as f:
                    json.dump(token_data, f)
                
                logger.info(f"Wrote authentication token to {config.auth_token_file}")
            except Exception as e:
                logger.error(f"Error writing token to file: {str(e)}")
            
            # Set environment variable as backup method
            os.environ["CHAINLIT_AUTH_TOKEN"] = encoded_session
            
            # Use multiple reliable methods to pass the token
            # Method 1: Standard URL parameter with proper encoding
            from urllib.parse import urlencode
            params = {'auth_token': encoded_session}
            chainlit_url = f"http://localhost:{config.chainlit_port}?{urlencode(params)}"
            
            # Method 2: Try setting a cookie that Chainlit might be able to access
            response = RedirectResponse(url=chainlit_url)
            response.set_cookie(
                key="chainlit-auth-token",
                value=encoded_session,
                httponly=False,  # Allow JavaScript access
                max_age=config.auth_session_max_age,
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

@auth_app.get("/direct-login")
async def direct_login():
    """
    Clear cookies via response headers and redirect directly to Google login.
    This provides a clean entry point when the app launches.
    """
    logger.info("Direct login requested - clearing cookies and redirecting to Google authentication")
    
    # Create response that redirects to Google login
    response = RedirectResponse(url="/login/google")
    
    # Clear known cookies via response headers
    response.delete_cookie(key="session-data", path="/")
    response.delete_cookie(key="chainlit-auth-token", path="/")
    response.delete_cookie(key="session-data", path="/app")
    response.delete_cookie(key="chainlit-auth-token", path="/app")
    
    # Also try wider path clearing
    for path in ["/", "/app", "/login", "/callback"]:
        response.delete_cookie(key="session-data", path=path)
        response.delete_cookie(key="chainlit-auth-token", path=path)
    
    # Return the redirect response with cleared cookies
    return response

@auth_app.on_event("shutdown")
async def shutdown_event():
    global chainlit_process, is_chainlit_running
    if chainlit_process is not None:
        logger.info("Attempting to shut down Chainlit server...")
        try:
            if chainlit_process.poll() is None: # Check if it's still running
                 chainlit_process.terminate()
                 chainlit_process.wait(timeout=5) # Wait briefly for termination
                 logger.info("Chainlit server terminated.")
            else:
                 logger.info("Chainlit server process was already terminated.")
        except subprocess.TimeoutExpired:
             logger.warning("Chainlit server did not terminate within timeout, attempting to kill.")
             chainlit_process.kill()
             chainlit_process.wait(timeout=2)
             logger.info("Chainlit server killed.")
        except Exception as e:
            logger.error(f"Error during Chainlit shutdown: {e}", exc_info=True)
        finally:
            chainlit_process = None
            is_chainlit_running = False

def start_chainlit():
    """Start the Chainlit server correctly, avoiding re-launching the main app."""
    global chainlit_process, is_chainlit_running

    if chainlit_process is not None and chainlit_process.poll() is None:
        logger.info("Chainlit server already running.")
        is_chainlit_running = True
        return

    logger.info(f"Preparing to start Chainlit server on port {config.chainlit_port} with app {config.chainlit_app_path}")

    try:
        # Use the same executable for both dev and prod, but with different args
        python_executable = sys.executable
        
        if is_frozen():
            # In frozen mode, use the same executable but with the helper script path
            # This will trigger our special mode in main.py
            helper_script_path = os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else '', 
                                            'src', 'utils', 'run_chainlit_entry.py')
            
            if not os.path.exists(helper_script_path):
                logger.warning(f"Helper script not found at {helper_script_path}, falling back to relative path")
                helper_script_path = 'src/utils/run_chainlit_entry.py'
            
            command = [
                python_executable,  # The main exe will detect these args and run in Chainlit-only mode
                helper_script_path,
                config.chainlit_app_path,
                str(config.chainlit_port)
            ]
        else:
            # Development mode - use standard chainlit module approach
            command = [
                python_executable,
                "-m",
                "chainlit",
                "run",
                config.chainlit_app_path,
                "--port", str(config.chainlit_port),
                "--headless"
            ]

        logger.info(f"Executing command: {' '.join(command)}")

        # Set up process creation flags for Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW
        
        # Create environment with SESSION_DIR for proper logging
        chainlit_env = os.environ.copy()
        
        # Start the process
        chainlit_process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=chainlit_env,
            creationflags=creationflags
        )

        # Wait briefly to allow immediate failure detection
        time.sleep(1)
        
        if chainlit_process.poll() is None:
            is_chainlit_running = True
            logger.info(f"Chainlit server process started successfully (PID: {chainlit_process.pid}).")
        else:
            # Process error handling
            try:
                stdout, stderr = chainlit_process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "Process did not terminate."
                chainlit_process.kill()
                stdout, stderr = chainlit_process.communicate()
                
            logger.error(f"Chainlit server failed to start. Return code: {chainlit_process.returncode}")
            if stdout: logger.error(f"Chainlit stdout:\n{stdout.strip()}")
            if stderr: logger.error(f"Chainlit stderr:\n{stderr.strip()}")
            chainlit_process = None
            is_chainlit_running = False
            
    except FileNotFoundError:
        logger.error(f"Error starting Chainlit: Could not find executable", exc_info=True)
        chainlit_process = None
        is_chainlit_running = False
    except Exception as e:
        logger.error(f"An unexpected error occurred starting Chainlit: {e}", exc_info=True)
        chainlit_process = None
        is_chainlit_running = False

def run_auth_server(
    host="0.0.0.0",
    port=None,
    shutdown_event: threading.Event = None,
    server_instance_wrapper: list = None
):
    """Start the authentication server and handle graceful shutdown."""
    port = port or config.auth_port

    logger.info(f"Starting authentication server on port {port}")

    # --- Browser opening logic (Keep as is) ---
    browser_opened = False
    def open_browser():
        nonlocal browser_opened
        # Check if the shutdown event is already set before opening
        if shutdown_event and shutdown_event.is_set():
             logger.info("Shutdown initiated before browser could open.")
             return
        time.sleep(1.5)  # Give the server a moment to start
         # Double check shutdown event *after* sleep
        if shutdown_event and shutdown_event.is_set():
             logger.info("Shutdown initiated before browser could open (post-sleep).")
             return
        url = f"http://localhost:{port}/direct-login"
        logger.info(f"Opening browser to: {url}")
        try:
            webbrowser.open(url)
            browser_opened = True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")

    # Start browser thread only if not shutting down
    if not (shutdown_event and shutdown_event.is_set()):
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    else:
        logger.info("Skipping browser opening due to immediate shutdown signal.")
    # --- End Browser Opening ---

    # Configure Uvicorn server instance
    config_uvicorn = uvicorn.Config(
        app=auth_app, # Use the instance directly
        host=host,
        port=port,
        log_level="info",
        access_log=False, # Keep logs cleaner
        reload=False, # Important
        log_config=config.uvicorn_log_config # Use your custom log config
    )
    server = uvicorn.Server(config_uvicorn)

    # Store the server instance if a wrapper is provided
    if server_instance_wrapper is not None:
        server_instance_wrapper.append(server)

    # Start the server - this blocks until shutdown is triggered
    try:
        server.run()
        logger.info("[Auth Server] Uvicorn server stopped.")
    except Exception as e:
        logger.exception(f"CRITICAL ERROR during Auth server run() execution: {e}")
    finally:
        # Clean up the reference in the wrapper if it exists
        if server_instance_wrapper is not None and server in server_instance_wrapper:
            server_instance_wrapper.remove(server)
        logger.info("run_auth_server function finished.")