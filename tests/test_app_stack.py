import aws_cdk as core
from aws_cdk import assertions

from app.app_stack import EnviroLoggerStack


def template() -> assertions.Template:
    app = core.App()
    stack = EnviroLoggerStack(app, "enviroplus-test")
    return assertions.Template.from_stack(stack)


def test_creates_iot_to_timestream_pipeline_with_failure_queue():
    rendered = template()
    rendered.resource_count_is("AWS::IoT::TopicRule", 1)
    rendered.resource_count_is("AWS::Timestream::Database", 1)
    rendered.resource_count_is("AWS::Timestream::Table", 1)
    rendered.resource_count_is("AWS::SQS::Queue", 1)
    rendered.has_resource_properties(
        "AWS::IoT::TopicRule",
        assertions.Match.object_like(
            {
                "TopicRulePayload": assertions.Match.object_like(
                    {
                        "Sql": assertions.Match.string_like_regexp(
                            "enviroplus/.+/telemetry"
                        ),
                        "ErrorAction": assertions.Match.object_like(
                            {"Sqs": assertions.Match.any_value()}
                        ),
                    }
                )
            }
        ),
    )


def test_does_not_create_long_lived_iam_users():
    template().resource_count_is("AWS::IAM::User", 0)
