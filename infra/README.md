# Keenmind Infrastructure

This directory contains the AWS CDK infrastructure code for the Keenmind Dota 2 Assistant application.

## Architecture

The infrastructure is organized into multiple stacks:

1. **Base Stack** - Contains shared resources like API Gateway and Secrets Manager
2. **Auth Stack** - Manages Cognito User Pool for authentication
3. **Lambda Stack** - Contains Lambda functions for processing queries and checking access
4. **API Stack** - Configures API Gateway endpoints with Lambda integrations and Cognito authorization

## Prerequisites

- Node.js 14.x or later
- AWS CLI configured with appropriate credentials
- AWS CDK installed globally (`npm install -g aws-cdk`)

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-2
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Directory Structure

```
infra/
├── bin/                # CDK app entry point
├── lib/                # Stack definitions
├── lambda/             # Lambda function code
│   ├── process-query/  # Python Lambda for processing queries
│   └── check-access/   # Node.js Lambda for checking access
├── cdk.json            # CDK configuration
└── package.json        # Node.js dependencies
```

## Deployment

1. Install dependencies:
   ```
   npm install
   ```

2. Bootstrap your AWS environment (first time only):
   ```
   cdk bootstrap
   ```

3. Deploy the stacks:
   ```
   cdk deploy --all
   ```

4. To deploy a specific stack:
   ```
   cdk deploy KeenMindBaseStack
   ```

## Useful Commands

* `npm run build` - Compile TypeScript to JavaScript
* `npm run watch` - Watch for changes and compile
* `npm run test` - Perform the Jest unit tests
* `cdk diff` - Compare deployed stack with current state
* `cdk synth` - Emits the synthesized CloudFormation template
* `cdk deploy` - Deploy this stack to your default AWS account/region

## Security

- Secrets are stored in AWS Secrets Manager
- API endpoints are protected with Cognito authentication
- Lambda functions have minimal IAM permissions

## Monitoring and Logging

- Lambda functions log to CloudWatch Logs
- API Gateway has request logging enabled
- CloudWatch alarms can be added for monitoring (see commented code)
