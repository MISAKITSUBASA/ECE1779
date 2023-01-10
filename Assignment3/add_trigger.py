import boto3
client_s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)
client_lambda = boto3.client(
    "lambda",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)
bucket_name = 'e455dbc6-5d8d-4928-b958-f31d098127f6billzou'
# add the permission to the lamda
client_lambda.add_permission(
     FunctionName="photoApplicationTest",
     StatementId='1',
     Action='lambda:InvokeFunction',
     Principal='s3.amazonaws.com',
     SourceArn="arn:aws:s3:::e455dbc6-5d8d-4928-b958-f31d098127f6billzou",
 )
response = client_s3.put_bucket_notification_configuration(
    Bucket = bucket_name,
    NotificationConfiguration= 
    {'LambdaFunctionConfigurations':
        [
            {'LambdaFunctionArn': 'arn:aws:lambda:us-east-1:295822090241:function:photoApplicationTest', 
            'Events': ['s3:ObjectCreated:*']
            }
        ]
    }
)
