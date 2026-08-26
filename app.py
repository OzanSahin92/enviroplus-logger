import os

import aws_cdk as cdk

from app.app_stack import EnviroLoggerStack

app = cdk.App()
EnviroLoggerStack(
    app,
    "EnviroLoggerStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
