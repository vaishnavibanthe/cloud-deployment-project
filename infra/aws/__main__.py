import pulumi

from pulumi import Config

import pulumi_aws as aws
 
config = Config()

app_name = config.require("appName")

image_uri = config.require("imageUri")
 
# IAM role for Lambda

lambda_role = aws.iam.Role(

    f"{app_name}-role",

    assume_role_policy="""{

        "Version": "2012-10-17",

        "Statement": [

            {

                "Action": "sts:AssumeRole",

                "Principal": {"Service": "lambda.amazonaws.com"},

                "Effect": "Allow",

                "Sid": ""

            }

        ]

    }"""

)
 
# Attach basic Lambda execution policy

aws.iam.RolePolicyAttachment(

    f"{app_name}-role-policy",

    role=lambda_role.name,

    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

)
 
# Lambda Function

lambda_function = aws.lambda_.Function(

    f"{app_name}-lambda",

    package_type="Image",

    image_uri=image_uri,

    role=lambda_role.arn,

)
 
# HTTP API Gateway

api = aws.apigatewayv2.Api(

    f"{app_name}-api",

    protocol_type="HTTP",

)
 
# Integration

integration = aws.apigatewayv2.Integration(

    f"{app_name}-integration",

    api_id=api.id,

    integration_type="AWS_PROXY",

    integration_uri=lambda_function.arn,

)
 
# Route

route = aws.apigatewayv2.Route(

    f"{app_name}-route",

    api_id=api.id,

    route_key="GET /",

    target=pulumi.Output.concat("integrations/", integration.id),

)
 
# Stage

stage = aws.apigatewayv2.Stage(

    f"{app_name}-stage",

    api_id=api.id,

    name="$default",

    auto_deploy=True

)
 
# Lambda permission for API Gateway

aws.lambda_.Permission(

    f"{app_name}-permission",

    action="lambda:InvokeFunction",

    function=lambda_function.name,

    principal="apigateway.amazonaws.com",

    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*"),

)
 
# Export API endpoint

pulumi.export("endpoint", api.api_endpoint)

 
