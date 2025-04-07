#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import { KeenMindBaseStack, KeenMindAuthStack, KeenMindLambdaStack, KeenMindApiStack } from '../lib/infra-stack';

// --- Load Configuration from YAML ---
const configDir = path.join(__dirname, '../../config'); // Path to your config directory
const cloudConfigPath = path.join(configDir, 'cloud_config.yaml');
let cloudConfig: any = {};

try {
  cloudConfig = yaml.load(fs.readFileSync(cloudConfigPath, 'utf8')) as any;
  console.log('✅ Loaded configuration from config/cloud_config.yaml');
} catch (e) {
  console.error(`❌ Error loading configuration from ${cloudConfigPath}:`, e);
  process.exit(1); // Exit if essential config is missing
}
// --- End Load Configuration ---

// --- Set Environment Variables from Loaded Config ---
// Use values from YAML, allowing overrides from actual environment variables if needed
process.env.COGNITO_USER_POOL_ID = process.env.COGNITO_USER_POOL_ID || cloudConfig?.cognito?.user_pool_id;
process.env.COGNITO_CLIENT_ID = process.env.COGNITO_CLIENT_ID || cloudConfig?.cognito?.client_id;
process.env.COGNITO_DOMAIN = process.env.COGNITO_DOMAIN || cloudConfig?.cognito?.domain;
process.env.API_GATEWAY_ID = process.env.API_GATEWAY_ID || cloudConfig?.api_gateway?.id;
process.env.API_ROOT_RESOURCE_ID = process.env.API_ROOT_RESOURCE_ID || cloudConfig?.api_gateway?.root_resource_id;
process.env.PROCESS_QUERY_FUNCTION_ARN = process.env.PROCESS_QUERY_FUNCTION_ARN || cloudConfig?.lambda?.process_query_arn;
process.env.CHECK_ACCESS_FUNCTION_ARN = process.env.CHECK_ACCESS_FUNCTION_ARN || cloudConfig?.lambda?.check_access_arn;
process.env.CDK_DEFAULT_REGION = process.env.CDK_DEFAULT_REGION || cloudConfig?.aws?.region || 'us-east-2';

// Log the final values being used *after* potentially combining YAML and process.env
console.log('--- CDK Environment Configuration ---');
console.log(`COGNITO_USER_POOL_ID: ${process.env.COGNITO_USER_POOL_ID || 'not set'}`);
console.log(`COGNITO_CLIENT_ID: ${process.env.COGNITO_CLIENT_ID || 'not set'}`);
console.log(`COGNITO_DOMAIN: ${process.env.COGNITO_DOMAIN || 'not set'}`);
console.log(`API_GATEWAY_ID: ${process.env.API_GATEWAY_ID || 'not set'}`);
console.log(`API_ROOT_RESOURCE_ID: ${process.env.API_ROOT_RESOURCE_ID || 'not set'}`);
console.log(`PROCESS_QUERY_FUNCTION_ARN: ${process.env.PROCESS_QUERY_FUNCTION_ARN || 'not set'}`);
console.log(`CHECK_ACCESS_FUNCTION_ARN: ${process.env.CHECK_ACCESS_FUNCTION_ARN || 'not set'}`);
console.log(`CDK_DEFAULT_REGION: ${process.env.CDK_DEFAULT_REGION}`);
console.log(`CDK_DEFAULT_ACCOUNT: ${process.env.CDK_DEFAULT_ACCOUNT || 'not set (from AWS context)'}`);
console.log('------------------------------------');
// --- End Set Environment Variables ---


// Check if this is a destroy operation
const isDestroy = process.argv.includes('destroy');
// Check if we want to preserve existing resources (can also be moved to config)
const preserveResources = process.env.PRESERVE_RESOURCES === 'true';
const app = new cdk.App();

// Environment configuration using the variables set above
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION
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

// Create stacks - they will use the process.env values set previously
const baseStack = new KeenMindBaseStack(app, 'KeenMindBaseStack', { env });
const authStack = new KeenMindAuthStack(app, 'KeenMindAuthStack', { env });
const lambdaStack = new KeenMindLambdaStack(app, 'KeenMindLambdaStack', { env });
const apiStack = new KeenMindApiStack(app, 'KeenMindApiStack', { env });

// Define deployment order through dependencies
if (!isDestroy) {
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
cdk.Tags.of(app).add('Environment', 'Production'); // Consider making this configurable via YAML too
cdk.Tags.of(app).add('ManagedBy', 'CDK');

app.synth();