from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_iot as iot,
)
from aws_cdk import (
    aws_sqs as sqs,
)
from aws_cdk import (
    aws_timestream as timestream,
)
from constructs import Construct


class EnviroLoggerStack(Stack):
    """Serverless ingestion path for Enviro+ telemetry.

    Device identities and X.509 certificates are deliberately provisioned outside
    this stack so private keys are generated and retained on the device.
    """

    TOPIC_FILTER = "enviroplus/+/telemetry"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        database = timestream.CfnDatabase(
            self, "TelemetryDatabase", database_name="enviroplus-telemetry"
        )
        table = timestream.CfnTable(
            self,
            "TelemetryTable",
            database_name=database.database_name,
            table_name="readings",
            retention_properties=timestream.CfnTable.RetentionPropertiesProperty(
                memory_store_retention_period_in_hours="24",
                magnetic_store_retention_period_in_days="365",
            ),
        )
        table.add_dependency(database)

        ingestion_failures = sqs.Queue(
            self,
            "IngestionFailures",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
            enforce_ssl=True,
        )

        rule_role = iam.Role(
            self,
            "IoTRuleRole",
            assumed_by=iam.ServicePrincipal("iot.amazonaws.com"),
            description="Least-privilege role used by the Enviro+ IoT topic rule",
        )
        rule_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:WriteRecords"], resources=[table.attr_arn]
            )
        )
        rule_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:DescribeEndpoints"], resources=["*"]
            )
        )
        ingestion_failures.grant_send_messages(rule_role)

        topic_rule = iot.CfnTopicRule(
            self,
            "TelemetryRule",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                aws_iot_sql_version="2015-10-08",
                description="Validate and route versioned Enviro+ readings to Timestream",
                sql=(
                    "SELECT schema_version, temperature_c, pressure_hpa, "
                    "humidity_pct, illuminance_lux, proximity, oxidising_ohm, "
                    "reducing_ohm, nh3_ohm, sampled_at_ms "
                    f"FROM '{self.TOPIC_FILTER}' WHERE schema_version = 1"
                ),
                actions=[
                    iot.CfnTopicRule.ActionProperty(
                        timestream=iot.CfnTopicRule.TimestreamActionProperty(
                            database_name=database.database_name,
                            table_name=table.table_name,
                            role_arn=rule_role.role_arn,
                            dimensions=[
                                iot.CfnTopicRule.TimestreamDimensionProperty(
                                    name="device_id", value="${topic(2)}"
                                ),
                                iot.CfnTopicRule.TimestreamDimensionProperty(
                                    name="schema_version", value="${schema_version}"
                                ),
                            ],
                            timestamp=iot.CfnTopicRule.TimestreamTimestampProperty(
                                value="${sampled_at_ms}", unit="MILLISECONDS"
                            ),
                        )
                    )
                ],
                error_action=iot.CfnTopicRule.ActionProperty(
                    sqs=iot.CfnTopicRule.SqsActionProperty(
                        queue_url=ingestion_failures.queue_url,
                        role_arn=rule_role.role_arn,
                        use_base64=False,
                    )
                ),
                rule_disabled=False,
            ),
        )
        topic_rule.node.add_dependency(table, rule_role, ingestion_failures)

        CfnOutput(self, "TelemetryTopic", value="enviroplus/<device-id>/telemetry")
        CfnOutput(self, "FailureQueueUrl", value=ingestion_failures.queue_url)
