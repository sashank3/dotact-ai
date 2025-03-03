#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { KeenMindBaseStack, KeenMindAuthStack, KeenMindLambdaStack, KeenMindApiStack } from '../lib/infra-stack';

const app = new cdk.App();

// Create the base stack
const baseStack = new KeenMindBaseStack(app, 'KeenMindBaseStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-2' 
  },
});

// Create the auth stack
const authStack = new KeenMindAuthStack(app, 'KeenMindAuthStack', {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-2' 
  },
});

// Create the Lambda stack
const lambdaStack = new KeenMindLambdaStack(app, 'KeenMindLambdaStack', authStack, {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-2' 
  },
});

// Create the API stack
const apiStack = new KeenMindApiStack(app, 'KeenMindApiStack', lambdaStack, authStack, {
  env: { 
    account: process.env.CDK_DEFAULT_ACCOUNT, 
    region: process.env.CDK_DEFAULT_REGION || 'us-east-2' 
  },
});

// Add dependencies
lambdaStack.addDependency(authStack);
apiStack.addDependency(lambdaStack);
apiStack.addDependency(authStack);

// Add tags to all resources
cdk.Tags.of(app).add('Project', 'Keenmind');
cdk.Tags.of(app).add('Environment', 'Production');
cdk.Tags.of(app).add('ManagedBy', 'CDK');

app.synth();