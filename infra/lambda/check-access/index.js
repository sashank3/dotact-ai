cat > infra/lambda/check-access/index.js << 'EOF'
exports.handler = async (event) => {
  const user = event.requestContext.authorizer?.claims;
  
  // Log query with user details
  console.log('Query:', {
    user: {
      cognito_id: user.sub,
      email: user.email
    },
    query: event.body
  });

  return {
    statusCode: 200,
    body: JSON.stringify({ 
      message: 'Access granted',
      user: user.email
    }),
  };
};
EOF