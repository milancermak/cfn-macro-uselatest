# cfn-macro-uselatest

A Cloudformation macro that ensures you're always using the latest versions of Lambda Layers. It allows you to declare your Layers as `my-layer` instead of `arn:aws:lambda:us-east-1:123456789012:layer:my-layer:24`.

[![Build Status](https://travis-ci.com/milancermak/cfn-macro-uselatest.svg?branch=master)](https://travis-ci.com/milancermak/cfn-macro-uselatest)

# Why it's practical

When adding a Lambda Layer to your Lambda functions, you need to fully qualify it, i.e. specify it using the layer *version*, not just the name. Presuming you always want to use the latest layer version there is, it gets very difficult and error prone to go through all the Cloudformation templates and change the layer version ARN. This macro fixes that.

# How it works

First, you need to declare the macro in the `Transforms` section of the template. It works well together with the `AWS::Serverless-2016-10-31` tranform; it does not matter if it comes before or after it.

Every Lambda Layer you own can henceforth be declared only by its name. When deploying the stack, the macro will call the [ListLayers](https://docs.aws.amazon.com/lambda/latest/dg/API_ListLayers.html) API to fetch the latest available version of your layers and replace the name by a fully qualified layer version ARN.

There are three caveats to be aware of:

  1) If you're already using a fully qualified layer version ARN (in other words, the version is pinned), this macro will not change it to the latest available one. It will be kept as is.

  2) If the layer version is declared using a Cloudformation intrinsic function (e.g. a !Ref or !Sub), it will be kept as is. The macro won't change the value.

  3) Due to the limitations of the API, you can only use the macro on layers you own in your account. There's currently no way how to get the latest available version of a public layer that you do not own.

# Example

The macro can be used in any place where the Layers can be declared - in the [SAM Globals](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md#globals-section) section, or in the Layers section of a `AWS::Serverless::Function` or a `AWS::Lambda::Function` resource.

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform:
  - UseLatest
  - AWS::Serverless-2016-10-31

Globals:
  Function:
    MemorySize: 128
    Runtime: python3.7
    Timeout: 10
    Layers:
      - superlayer # this gets replaced

Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        ZipFile: |
          import superlayer
          def handler(event, context):
              print(event)

      Handler: index.handler
      Layers:
        - superlayer # this gets replaced


  ServerlessFunction:
    Type: AWS::Serverless::Function
    Properties:
      InlineCode: |
          import superlayer
          def handler(event, context):
              print(event)

      Handler: index.handler
      Layers:
        # the first two get replaced, the last one is kept
        # because it's a fully-qualified layer version ARN
        - superlayer
        - arn:aws:lambda:us-east-1:790194644437:layer:superlayer
        - arn:aws:lambda:us-east-1:790194644437:layer:superlayer:1
```

# How to deploy it

I wanted to make the macro available in [SAR](https://serverlessrepo.aws.amazon.com/), sadly, a `AWS::CloudFormation::Macro` is not a supported resource. You'll have to deploy it yourself, using [SAM](https://github.com/awslabs/aws-sam-cli). Just build, package and deploy the `infrastructure/uselatest.yml` template and you're done.
