import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

// Base stack with shared resources and outputs
export class KeenMindBaseStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // Base stack is now empty as resources have been moved to their respective stacks
  }
}

// Auth stack
export class KeenMindAuthStack extends cdk.Stack {
  public readonly userPool: cognito.IUserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly userPoolDomain: cognito.IUserPoolDomain;
  private readonly isExistingUserPool: boolean;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Check if we should use an existing user pool
    const existingUserPoolId = process.env.COGNITO_USER_POOL_ID;
    this.isExistingUserPool = !!existingUserPoolId;

    // Import Google OAuth credentials from Secrets Manager
    const googleAuthSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 
      'GoogleAuthSecret', 
      'keenmind/GoogleOAuth'
    );

    if (this.isExistingUserPool) {
      // Import existing user pool
      console.log(`Importing existing user pool: ${existingUserPoolId}`);
      this.userPool = cognito.UserPool.fromUserPoolId(this, 'ImportedUserPool', existingUserPoolId!);
      
      // Import existing domain
      const domainPrefix = process.env.COGNITO_DOMAIN?.split('.')[0];
      if (domainPrefix) {
        this.userPoolDomain = cognito.UserPoolDomain.fromDomainName(this, 'ImportedDomain', domainPrefix);
      } else {
        throw new Error('COGNITO_DOMAIN environment variable is required when using an existing user pool');
      }
    } else {
      // Create a new user pool
      console.log('Creating new user pool');
      const newUserPool = new cognito.UserPool(this, 'KeenMindUserPool', {
        userPoolName: 'KeenMindUserPool',
        selfSignUpEnabled: true,
        signInAliases: {
          email: true,
        },
        autoVerify: {
          email: true,
        },
        standardAttributes: {
          email: {
            required: true,
            mutable: true,
          },
          givenName: {
            required: true,
            mutable: true,
          },
          familyName: {
            required: true,
            mutable: true,
          },
        },
        passwordPolicy: {
          minLength: 8,
          requireLowercase: true,
          requireUppercase: true,
          requireDigits: true,
          requireSymbols: false,
        },
        accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
        removalPolicy: cdk.RemovalPolicy.RETAIN, // RETAIN to prevent accidental deletion
      });
      
      this.userPool = newUserPool;
      
      // Create a domain for the new user pool
      this.userPoolDomain = newUserPool.addDomain('KeenMindUserPoolDomain', {
        cognitoDomain: {
          domainPrefix: 'keenmind-app-auth',
        },
      });
      
      // Add Google as an identity provider for the new user pool using credentials from Secrets Manager.
      const googleProvider = new cognito.CfnUserPoolIdentityProvider(this, 'GoogleProvider', {
        userPoolId: newUserPool.userPoolId,
        providerName: 'Google',
        providerType: 'Google',
        providerDetails: {
          client_id: googleAuthSecret.secretValueFromJson('GOOGLE_CLIENT_ID').unsafeUnwrap(),
          client_secret: googleAuthSecret.secretValueFromJson('GOOGLE_CLIENT_SECRET').unsafeUnwrap(),
          authorize_scopes: 'profile email openid',
        },
        attributeMapping: {
          email: 'email',
          given_name: 'given_name',
          family_name: 'family_name',
        },
      });
      
      // Create a client for the new user pool
      this.userPoolClient = new cognito.UserPoolClient(this, 'KeenMindUserPoolClient', {
        userPool: newUserPool,
        authFlows: {
          userPassword: true,
          userSrp: true,
          adminUserPassword: true,
        },
        oAuth: {
          flows: {
            authorizationCodeGrant: true,
          },
          scopes: [
            cognito.OAuthScope.EMAIL,
            cognito.OAuthScope.OPENID,
            cognito.OAuthScope.PROFILE,
          ],
          callbackUrls: [
            'http://localhost:8000/oauth/callback',
            'https://keenmind-app-auth.auth.us-east-2.amazoncognito.com/oauth2/idpresponse',
          ],
          logoutUrls: [
            'http://localhost:8000/logout',
          ],
        },
        supportedIdentityProviders: [
          cognito.UserPoolClientIdentityProvider.GOOGLE,
        ],
      });
      
      // Make sure the client depends on the Google provider
      this.userPoolClient.node.addDependency(googleProvider);
    }
    
    // If we're using an existing user pool, create a client for it
    if (this.isExistingUserPool) {
      // For existing user pools, we create a client without specifying identity providers
      this.userPoolClient = new cognito.UserPoolClient(this, 'KeenMindUserPoolClient', {
        userPool: this.userPool,
        authFlows: {
          userPassword: true,
          userSrp: true,
          adminUserPassword: true,
        },
        oAuth: {
          flows: {
            authorizationCodeGrant: true,
          },
          scopes: [
            cognito.OAuthScope.EMAIL,
            cognito.OAuthScope.OPENID,
            cognito.OAuthScope.PROFILE,
          ],
          callbackUrls: [
            'http://localhost:8000/oauth/callback',
            'https://keenmind-app.auth.us-east-2.amazoncognito.com/oauth2/idpresponse',
          ],
          logoutUrls: [
            'http://localhost:8000/logout',
          ],
        },
      });
    }

    // Output the user pool ID and client ID
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'The ID of the Cognito User Pool',
      exportName: 'KeenmindUserPoolId',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'The ID of the Cognito User Pool Client',
      exportName: 'KeenmindUserPoolClientId',
    });

    if (!this.isExistingUserPool) {
      new cdk.CfnOutput(this, 'CognitoDomain', {
        value: `keenmind-app-auth.auth.${this.region}.amazoncognito.com`,
        description: 'The domain of the Cognito User Pool',
        exportName: 'KeenmindCognitoDomain',
      });
    } else {
      new cdk.CfnOutput(this, 'CognitoDomain', {
        value: process.env.COGNITO_DOMAIN || '',
        description: 'The domain of the Cognito User Pool',
        exportName: 'KeenmindCognitoDomain',
      });
    }
  }
}

// Lambda functions stack
export class KeenMindLambdaStack extends cdk.Stack {
  public readonly processQueryFunction: lambda.Function;
  public readonly checkAccessFunction: lambda.Function;
  public readonly llmSecrets: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Always use environment variables - no direct stack dependencies
    const userPoolId = process.env.COGNITO_USER_POOL_ID;
    if (!userPoolId) {
      throw new Error('COGNITO_USER_POOL_ID environment variable is required');
    }

    const userPoolClientId = process.env.COGNITO_CLIENT_ID;
    if (!userPoolClientId) {
      throw new Error('COGNITO_CLIENT_ID environment variable is required');
    }

    // Import the existing LLMCredentials secret
    this.llmSecrets = secretsmanager.Secret.fromSecretNameV2(this, 'LLMCredentials', 'LLMCredentials');
    console.log('Imported existing LLMCredentials secret');

    // Create Lambda execution role with permissions to access Secrets Manager
    const lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Grant the Lambda role read access to the secrets
    this.llmSecrets.grantRead(lambdaExecutionRole);

    // Create the check-access Lambda function
    this.checkAccessFunction = new lambda.Function(this, 'CheckAccessFunction', {
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../infra/lambda/check-access'), {
        bundling: {
          image: lambda.Runtime.NODEJS_18_X.bundlingImage,
          local: {
            tryBundle(outputDir: string) {
              try {
                require('esbuild').buildSync({
                  entryPoints: [path.join(__dirname, '../../infra/lambda/check-access/index.js')],
                  bundle: true,
                  platform: 'node',
                  target: 'node18',
                  external: [], // Don't exclude any dependencies
                  outfile: path.join(outputDir, 'index.js'),
                });
                return true;
              } catch (e) {
                console.error('esbuild failed: ', e);
                return false;
              }
            }
          }
        }
      }),
      environment: {
        USER_POOL_ID: userPoolId,
        CLIENT_ID: userPoolClientId,
        COGNITO_ISSUER: `https://cognito-idp.${this.region}.amazonaws.com/${userPoolId}`,
        GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID || ''
      },
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
      role: lambdaExecutionRole,
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Apply RETAIN removal policy to Lambda
    const cfnCheckAccessFunction = this.checkAccessFunction.node.defaultChild as lambda.CfnFunction;
    cfnCheckAccessFunction.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

    // Create a Lambda Layer for Python dependencies
    const processingLayer = new lambda.LayerVersion(this, 'ProcessingDependenciesLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../../infra/lambda/process-query'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_9.bundlingImage,
          command: [
            'bash', '-c', [
              'pip install -r requirements.txt -t /tmp/python',
              'mkdir -p /asset-output/python',
              'cp -r /tmp/python/* /asset-output/python'
            ].join(' && ')
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: 'Dependencies for process-query Lambda function',
    });

    // Create the process-query Lambda function
    this.processQueryFunction = new lambda.Function(this, 'ProcessQueryFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../infra/lambda/process-query'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_9.bundlingImage,
          command: [
            'bash', '-c', [
              'mkdir -p /asset-output',
              'cp *.py /asset-output'
            ].join(' && ')
          ],
        },
      }),
      layers: [processingLayer],
      environment: {
        USER_POOL_ID: userPoolId,
        LLM_PROVIDER: 'sambanova',
        API_KEY: this.llmSecrets.secretValueFromJson('API_KEY').unsafeUnwrap(),
        DEPLOYMENT_TIMESTAMP: Date.now().toString(), // Force update
      },
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
      role: lambdaExecutionRole,
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Apply RETAIN removal policy to Lambda
    const cfnProcessQueryFunction = this.processQueryFunction.node.defaultChild as lambda.CfnFunction;
    cfnProcessQueryFunction.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

    // Add permissions for making HTTP requests to verify Google tokens
    this.checkAccessFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['execute-api:Invoke'],
      resources: ['*'],
    }));
    
    // Export the Lambda function ARNs as CloudFormation outputs
    new cdk.CfnOutput(this, 'ProcessQueryFunctionArn', {
      value: this.processQueryFunction.functionArn,
      description: 'ARN of the Process Query Lambda Function',
      exportName: 'KeenMindProcessQueryFunctionArn',
    });

    new cdk.CfnOutput(this, 'CheckAccessFunctionArn', {
      value: this.checkAccessFunction.functionArn,
      description: 'ARN of the Check Access Lambda Function',
      exportName: 'KeenMindCheckAccessFunctionArn',
    });
  }
}

// API Gateway stack
export class KeenMindApiStack extends cdk.Stack {
  public readonly apiEndpoint: apigateway.RestApi | apigateway.IRestApi;
  private readonly isExistingApi: boolean;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Check if we should use an existing API Gateway
    const existingApiId = process.env.API_GATEWAY_ID;
    const existingRootResourceId = process.env.API_ROOT_RESOURCE_ID;
    this.isExistingApi = !!(existingApiId && existingRootResourceId);

    // Import user pool from environment variable
    const userPoolId = process.env.COGNITO_USER_POOL_ID;
    if (!userPoolId) {
      throw new Error('COGNITO_USER_POOL_ID environment variable is required');
    }
    const userPool = cognito.UserPool.fromUserPoolId(this, 'ImportedUserPool', userPoolId);

    // Get Lambda ARNs from environment variables only
    const processQueryFunctionArn = process.env.PROCESS_QUERY_FUNCTION_ARN;
    const checkAccessFunctionArn = process.env.CHECK_ACCESS_FUNCTION_ARN;
    
    // Handle missing Lambda ARNs when not using an existing API
    if (!this.isExistingApi && (!processQueryFunctionArn || !checkAccessFunctionArn)) {
      console.warn('WARNING: PROCESS_QUERY_FUNCTION_ARN and/or CHECK_ACCESS_FUNCTION_ARN environment variables are missing.');
      console.warn('Creating a mock API with dummy methods for validation purposes.');
      
      // Create a mock/placeholder API with dummy methods to pass validation
      const mockApi = new apigateway.RestApi(this, 'MockApi', {
        restApiName: 'Mock API - For Validation Only',
        deploy: false // Don't deploy this API
      });
      
      // Add a dummy resource and method to pass validation
      const dummyResource = mockApi.root.addResource('dummy');
      dummyResource.addMethod('GET', new apigateway.MockIntegration({
        integrationResponses: [{
          statusCode: '200',
          responseTemplates: {
            'application/json': '{"message": "This is a mock API"}'
          },
        }],
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': '{"statusCode": 200}'
        },
      }), {
        methodResponses: [{ statusCode: '200' }],
      });
      
      this.apiEndpoint = mockApi;
      
      // Exit early so we don't try to create a real API
      console.warn('Exiting early from API Gateway stack - using mock API for synth only');
      return;
    }

    if (this.isExistingApi) {
      // Import existing API Gateway
      console.log(`Importing existing API Gateway: ${existingApiId}`);
      this.apiEndpoint = apigateway.RestApi.fromRestApiAttributes(this, 'ImportedAPI', {
        restApiId: existingApiId!,
        rootResourceId: existingRootResourceId!
      });
      
      // For existing APIs, we don't add resources or methods
      console.log('Using existing API resources and methods');
      
      // Output the existing API URL
      new cdk.CfnOutput(this, 'ApiUrl', {
        value: `https://${existingApiId}.execute-api.${this.region}.amazonaws.com/prod`,
        description: 'The URL of the API Gateway',
        exportName: 'KeenmindApiUrl',
      });
      return; // Return early, we don't need to create a new API
    }

    // This code only runs if we're creating a new API and we have all required ARNs
    console.log("Creating new API Gateway with Lambda integrations");
      
    // Create API Gateway with all the original logic from your code
    const api = new apigateway.RestApi(this, 'KeenMindApi', {
      restApiName: 'KeenMind API',
      description: 'API for KeenMind',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization', 'X-Auth-Source'],
      },
      deployOptions: {
        stageName: 'prod',
      }
    });

    // Apply RETAIN removal policy to all API Gateway resources
    const cfnRestApi = api.node.defaultChild as apigateway.CfnRestApi;
    cfnRestApi.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);
    
    // Ensure deployment and stage are also retained
    const deployment = api.latestDeployment;
    const stage = api.deploymentStage;
    
    if (deployment) {
      const cfnDeployment = deployment.node.defaultChild as apigateway.CfnDeployment;
      cfnDeployment?.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);
    }
    
    if (stage) {
      const cfnStage = stage.node.defaultChild as apigateway.CfnStage;
      cfnStage?.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);
    }

    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [userPool]
    });
    
    // Make sure we have valid Lambda ARNs - this should always be true at this point
    if (!processQueryFunctionArn || !checkAccessFunctionArn) {
      console.error('Missing Lambda ARNs, cannot create API resources');
      return;
    }
    
    try {
      // Import Lambda functions to avoid circular dependencies
      const processQueryFn = lambda.Function.fromFunctionArn(
        this, 'ProcessQueryFunctionRef', processQueryFunctionArn
      );
      
      const checkAccessFn = lambda.Function.fromFunctionArn(
        this, 'CheckAccessFunctionRef', checkAccessFunctionArn
      );
      
      // Create Lambda integrations
      const processQueryIntegration = new apigateway.LambdaIntegration(processQueryFn);
      const checkAccessIntegration = new apigateway.LambdaIntegration(checkAccessFn);
      
      // Create Custom Authorizer for API Gateway
      const customAuthorizer = new apigateway.RequestAuthorizer(this, 'CustomAuthorizer', {
        handler: checkAccessFn,
        identitySources: [apigateway.IdentitySource.header('Authorization')],
        resultsCacheTtl: cdk.Duration.minutes(5)
      });

      // Create API Gateway resource and method for processing queries
      const processQueryResource = api.root.addResource('process-query');
      processQueryResource.addMethod('POST', processQueryIntegration, {
        authorizer: customAuthorizer,
        authorizationType: apigateway.AuthorizationType.CUSTOM,
      });
      
      // Ensure resource is retained
      const cfnResource = processQueryResource.node.defaultChild as apigateway.CfnResource;
      cfnResource?.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

      // Create API Gateway resource and method for checking access
      const checkAccessResource = api.root.addResource('check-access');
      checkAccessResource.addMethod('GET', checkAccessIntegration, {
        authorizationType: apigateway.AuthorizationType.COGNITO,
        authorizer: cognitoAuthorizer,
      });
      
      // Ensure resource is retained
      const cfnCheckResource = checkAccessResource.node.defaultChild as apigateway.CfnResource;
      cfnCheckResource?.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

      // Create permissions for Lambda functions to be invoked by API Gateway
      new lambda.CfnPermission(this, 'ProcessQueryPermission', {
        action: 'lambda:InvokeFunction',
        functionName: processQueryFunctionArn,
        principal: 'apigateway.amazonaws.com',
      });
      
      new lambda.CfnPermission(this, 'CheckAccessPermission', {
        action: 'lambda:InvokeFunction',
        functionName: checkAccessFunctionArn,
        principal: 'apigateway.amazonaws.com',
      });
      
      // Store the API Gateway ID and Root Resource ID in outputs
      const apiId = new cdk.CfnOutput(this, 'ApiGatewayId', {
        value: api.restApiId,
        description: 'The ID of the API Gateway',
        exportName: 'KeenmindApiGatewayId',
      });
      
      const rootResourceId = new cdk.CfnOutput(this, 'ApiRootResourceId', {
        value: api.root.resourceId,
        description: 'The ID of the API Gateway Root Resource',
        exportName: 'KeenmindApiRootResourceId',
      });
      
    } catch (error) {
      console.error('Error setting up API Gateway:', error);
      // Return a minimal API for synthesis so the destroy operation can proceed
      this.apiEndpoint = api;
      return;
    }
    
    // Set this.apiEndpoint
    this.apiEndpoint = api;
  }
}