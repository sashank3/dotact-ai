/**
 * Lambda authorizer function for API Gateway that validates:
 * 1. Cognito tokens from our user pool
 * 2. Google OAuth tokens for users who authenticated with Google
 */
// Only import what we need rather than entire clients/libraries
const { CognitoIdentityProviderClient, GetUserCommand } = require('@aws-sdk/client-cognito-identity-provider');
const { decode, verify } = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

// Initialize clients only when needed (lazy loading)
let cognitoClient;
function getCognitoClient() {
  if (!cognitoClient) {
    cognitoClient = new CognitoIdentityProviderClient();
  }
  return cognitoClient;
}

// Google OAuth2 configuration - initialize only when needed
let googleJwksClientInstance;
function getGoogleJwksClient() {
  if (!googleJwksClientInstance) {
    googleJwksClientInstance = jwksClient({
      jwksUri: 'https://www.googleapis.com/oauth2/v3/certs',
      cache: true,
      rateLimit: true,
    });
  }
  return googleJwksClientInstance;
}

// Helper function to get a Google signing key
const getGoogleSigningKey = (kid) => {
  return new Promise((resolve, reject) => {
    getGoogleJwksClient().getSigningKey(kid, (err, key) => {
      if (err) {
        return reject(err);
      }
      const signingKey = key.getPublicKey();
      resolve(signingKey);
    });
  });
};

// Helper function to verify Google token
const verifyGoogleToken = async (token) => {
  try {
    // First, decode the token without verification to get the header with kid
    const decoded = decode(token, { complete: true });
    
    if (!decoded || !decoded.header || !decoded.header.kid) {
      console.error('Invalid token format or missing kid');
      return null;
    }
    
    console.log('Token header kid:', decoded.header.kid);
    
    // Get the signing key for this specific token
    const signingKey = await getGoogleSigningKey(decoded.header.kid);
    
    // Verify the token with the proper key
    return verify(token, signingKey, { algorithms: ['RS256'] });
  } catch (error) {
    console.error('Error verifying Google token:', error.message);
    return null;
  }
};

/**
 * Generate IAM policy
 */
function generatePolicy(principalId, effect, resource) {
  const authResponse = { principalId };
  
  if (effect && resource) {
    authResponse.policyDocument = {
      Version: '2012-10-17',
      Statement: [
        {
          Action: 'execute-api:Invoke',
          Effect: effect,
          Resource: resource
        }
      ]
    };
  }
  
  // Optional: include additional info in the context
  authResponse.context = {
    userId: principalId,
    timestamp: new Date().toISOString()
  };
  
  return authResponse;
}

/**
 * Main handler function
 */
exports.handler = async (event) => {
  console.log('Received event:', JSON.stringify(event, null, 2));
  
  try {
    // Get the Authorization header from the request
    const authHeader = event.headers.Authorization || event.headers.authorization;
    const authSource = event.headers['X-Auth-Source'] || event.headers['x-auth-source'];
    
    if (!authHeader) {
      console.error('Missing Authorization header');
      return generatePolicy('user', 'Deny', event.methodArn);
    }
    
    // Extract the token from the Authorization header
    const match = authHeader.match(/^Bearer (.*)$/);
    if (!match || match.length < 2) {
      console.error('Invalid Authorization header format');
      return generatePolicy('user', 'Deny', event.methodArn);
    }
    
    const token = match[1];
    
    // If X-Auth-Source is Google, verify with Google
    if (authSource && authSource.toLowerCase() === 'google') {
      console.log('Verifying Google token');
      
      const decodedToken = await verifyGoogleToken(token);
      if (!decodedToken) {
        console.error('Invalid Google token');
        return generatePolicy('user', 'Deny', event.methodArn);
      }
      
      const userId = decodedToken.sub || decodedToken.email;
      console.log('Google authentication successful for user:', userId);
      return generatePolicy(userId, 'Allow', event.methodArn);
    }
    
    // Default to Cognito token verification
    console.log('Verifying Cognito token');
    const getUserCommand = new GetUserCommand({
      AccessToken: token
    });
    
    const userData = await getCognitoClient().send(getUserCommand);
    
    if (!userData || !userData.Username) {
      console.error('Failed to get user data from Cognito token');
      return generatePolicy('user', 'Deny', event.methodArn);
    }
    
    console.log('Cognito authentication successful for user:', userData.Username);
    return generatePolicy(userData.Username, 'Allow', event.methodArn);
    
  } catch (error) {
    console.error('Error in Lambda authorizer:', error);
    return generatePolicy('user', 'Deny', event.methodArn);
  }
};