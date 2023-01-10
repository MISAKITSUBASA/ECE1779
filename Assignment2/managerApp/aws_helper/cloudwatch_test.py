from datetime import datetime, timedelta
from time import sleep
import boto3
client_watch = boto3.client('cloudwatch', region_name='us-east-1', aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                            aws_secret_access_key='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')


def cloudwatch_missRate(instance_id, miss_rate):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData=[{
            'MetricName': 'missRate',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': miss_rate,
            'Unit': 'Percent',

        }]
    )
    return re


def cloudwatch_hitRate(instance_id, hit_rate):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData=[{
            'MetricName': 'hitRate',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': hit_rate,
            'Unit': 'Percent',

        }]
    )
    return re


def cloudwatch_item_count(instance_id, count):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData=[{
            'MetricName': 'itemInCache',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': count,

        }]
    )
    return re


def cloudwatch_cache_size(instance_id, count):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData=[{
            'MetricName': 'itemInCache',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': count,

        }]
    )
    return re


# cloudwatch_missRate(0, 0.89)
# sleep(1)
# cloudwatch_missRate(0, 0.7)
# sleep(1)
# cloudwatch_missRate(0, 0.2)
# sleep(1)
# cloudwatch_missRate(0, 0.7)
# sleep(1)
# cloudwatch_missRate(0, 0.2)
# sleep(1)
# cloudwatch_missRate(0, 0.89)
# sleep(60)
# sleep(1)
# cloudwatch_missRate(0, 0.7)
# sleep(1)
# cloudwatch_missRate(0, 0.2)
# sleep(1)
# cloudwatch_missRate(0, 0.89)
# sleep(60)
# cloudwatch_missRate(0, 0.89)
# sleep(1)
# cloudwatch_missRate(0, 0.7)
# sleep(1)
# for i in range(30, 0):
#     response = client_watch.get_metric_statistics(
#                     Namespace='memcache',
#                     Dimensions=[
#                         {
#                             'Name': 'InstanceId',
#                             'Value': str(0)
#                         }
#                     ],
#                     MetricName='missRate',
#                     StartTime=datetime.now() - timedelta(seconds=60),
#                     EndTime=datetime.now() - timedelta(seconds=120),
#                     Period=60,
#                     Statistics=[
#                         'Average'
#                     ],
#                     Unit='Percent'
#                 )
#     print(response)
# cloudwatch_hitRate(0, 0.5)
# cloudwatch_hitRate(0, 0.5)
# cloudwatch_hitRate(0, 0.1)
# sleep(60)
# cloudwatch_hitRate(0, 0.5)
# cloudwatch_hitRate(0, 0.6)
# cloudwatch_hitRate(0, 0.8)
# cloudwatch_hitRate(0, 0.9)
# sleep(60)
# cloudwatch_hitRate(0, 0.4)
# cloudwatch_hitRate(0, 0.2)
# sleep(60)
# cloudwatch_hitRate(0, 0.5)
# cloudwatch_hitRate(0, 0.5)

# now = datetime.utcnow()
# response = client_watch.get_metric_statistics(
#     Namespace='memcache',
#     Dimensions=[
#         {
#             'Name': 'InstanceId',
#             'Value': str(0)
#         }
#     ],
#     MetricName='missRate',
#     StartTime= now - timedelta(seconds=1800),
#     EndTime= now,
#     Period=60,
#     Statistics=[
#         'Average'
#     ],
#     Unit='Percent'
# )
# # print(now,"???????", now - timedelta(seconds=30*60))
# # print(response)

# for r in response['Datapoints']:
#         print(r['Average'],"!!!!!!!")
#         print(type(r['Average']))

# response = client_watch.get_metric_statistics(
#     Namespace='memcache',
#     Dimensions=[
#         {
#             'Name': 'InstanceId',
#             'Value': str(0)
#         }
#     ],
#     MetricName='hitRate',
#     StartTime= now - timedelta(seconds=1200),
#     EndTime= now,
#     Period=60,
#     Statistics=[
#         'Average'
#     ],
#     Unit='Percent'
# )
# print(response)


now = datetime(2022, 11, 19, 3, 29)
l_miss_rate_dict = {}
l_miss_rate = []
response = client_watch.get_metric_statistics(
      Namespace='memcache',
      Dimensions=[
           {
                'Name': 'InstanceId',
                'Value': str(0)
            }
           ],
      MetricName='missRate',
      StartTime=now - timedelta(seconds=18000),
      EndTime=now,
      Period=60,
      Statistics=[
           'Average'
           ],
      Unit='Percent'
      )

for r in response['Datapoints']:
    if r['Timestamp'] in l_miss_rate_dict.keys():
        l_miss_rate_dict[r['Timestamp']] = l_miss_rate_dict[r['Timestamp']] + r['Average']
    else:
        l_miss_rate_dict.setdefault(r['Timestamp'], r['Average'])
l = l_miss_rate_dict.keys()

for key in sorted(l):

    l_miss_rate.append([((now - key.replace(tzinfo=None)).seconds//60)% 60 , l_miss_rate_dict[key]])
for timepair in l_miss_rate:
        timepair[1] = timepair[1] / 2

print(l_miss_rate)