import boto3

s3 = boto3.client('s3')
bucket_name = "thisisalovelybuckethahaha"
#create a bucket
response = s3.create_bucket(Bucket = bucket_name)
print(f"all existing buckets: {s3.list_buckets()}")

# store sth in bucket
s3.put_object(Bucket = bucket_name,Key = 'name', Body = 'Bill')

#retrieve sth in bucket
value = s3.get_object(Bucket = bucket_name, Key = 'name')['Body'].read().decode('utf-8')
print(f"value is {value}")

#delete an item in bucket
response = s3.delete_object(Bucket = bucket_name, Key = 'name')

#delete the whole bucket
response = s3.delete_bucket(Bucket = bucket_name)

s3 = boto3.resource(
    service_name='s3',
    region_name='us-east-1',
    aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
    aws_secret_access_key='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'
)