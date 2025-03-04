#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { KeenMindBaseStack, KeenMindAuthStack, KeenMindLambdaStack, KeenMindApiStack } from '../lib/infra-stack';

// Load environment variables from .env file
dotenv.config({ path: path.join(__dirname, '../../.env') });
console.log(`COGNITO_USER_POOL_ID=${process.env.COGNITO_USER_POOL_ID || 'not set'}`);

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-2'
};

// Create stacks
const baseStack = new KeenMindBaseStack(app, 'KeenMindBaseStack', { env });
const authStack = new KeenMindAuthStack(app, 'KeenMindAuthStack', { env });
const lambdaStack = new KeenMindLambdaStack(app, 'KeenMindLambdaStack', authStack, { env });
const apiStack = new KeenMindApiStack(app, 'KeenMindApiStack', lambdaStack, authStack, { env });

// Define dependencies - note no circular references
authStack.addDependency(baseStack);
lambdaStack.addDependency(authStack);
apiStack.addDependency(lambdaStack); 
// Do NOT add lambdaStack.addDependency(apiStack)

// Add tags
cdk.Tags.of(app).add('Project', 'Keenmind');
cdk.Tags.of(app).add('Environment', 'Production');
cdk.Tags.of(app).add('ManagedBy', 'CDK');

app.synth();