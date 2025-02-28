#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { KeenMindAuthStack } from '../lib/infra-stack';

const app = new cdk.App();
new KeenMindAuthStack(app, 'KeenMindAuthStack', {
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  env: { account: '474668394137', region: 'us-east-2' }
});