#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { KeenMindBaseStack, KeenMindAuthStack, KeenMindLambdaStack, KeenMindApiStack } from '../lib/infra-stack';

// Check if this is a destroy operation
const isDestroy = process.argv.includes('destroy');
// Check if we want to preserve existing resources
const preserveResources = process.env.PRESERVE_RESOURCES === 'true';

// Load environment variables from .env file
dotenv.config({ path: path.join(__dirname, '../../.env') });
console.log(`COGNITO_USER_POOL_ID=${process.env.COGNITO_USER_POOL_ID || 'not set'}`);
console.log(`COGNITO_CLIENT_ID=${process.env.COGNITO_CLIENT_ID || 'not set'}`);
console.log(`API_GATEWAY_ID=${process.env.API_GATEWAY_ID || 'not set'}`);
console.log(`API_ROOT_RESOURCE_ID=${process.env.API_ROOT_RESOURCE_ID || 'not set'}`);

// Log Lambda function ARNs
console.log(`PROCESS_QUERY_FUNCTION_ARN=${process.env.PROCESS_QUERY_FUNCTION_ARN || 'not set'}`);
console.log(`CHECK_ACCESS_FUNCTION_ARN=${process.env.CHECK_ACCESS_FUNCTION_ARN || 'not set'}`);

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-2'
};

// Log operation mode
if (isDestroy) {
  console.log('🔴 DESTROY MODE: Removing CloudFormation stacks');
  if (preserveResources) {
    console.log('🛡️ PRESERVE RESOURCES: Critical resources will be retained');
  }
} else {
  console.log('🟢 DEPLOY MODE: Creating or updating CloudFormation stacks');
}

// Create stacks - no direct dependencies passed between them
const baseStack = new KeenMindBaseStack(app, 'KeenMindBaseStack', { env });
const authStack = new KeenMindAuthStack(app, 'KeenMindAuthStack', { env });
const lambdaStack = new KeenMindLambdaStack(app, 'KeenMindLambdaStack', { env });
const apiStack = new KeenMindApiStack(app, 'KeenMindApiStack', { env });

// Define deployment order through dependencies
// This doesn't create CloudFormation dependencies, just controls deployment order
if (!isDestroy) {
  // Only add dependencies for deployment operations
  authStack.addDependency(baseStack);
  lambdaStack.addDependency(authStack);
  apiStack.addDependency(lambdaStack);
  apiStack.addDependency(authStack);
  console.log('✅ Stack dependencies set for deployment order');
} else {
  console.log('⚠️ Not setting stack dependencies for destroy operation');
}

// Add tags
cdk.Tags.of(app).add('Project', 'Keenmind');
cdk.Tags.of(app).add('Environment', 'Production');
cdk.Tags.of(app).add('ManagedBy', 'CDK');

app.synth();