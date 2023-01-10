import boto3

# connect to ec2 instance created
ec2 = boto3.client(service_name='ec2',
                   region_name='us-east-1',
                   aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                   aws_secret_access_key='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')

# create a new ec2 instance and delete it

user_data = '''#!/bin/sh
cd /home/ubuntu
git clone https://BillZou123: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@github.com/xius666/ece1779_A2.git
cd ece1779_A2
python3 -m venv venv
source venv/bin/activate
sudo pip3 install -r requirements.txt
sudo python3 run.py'''

new_instances = ec2.run_instances(
    ImageId='ami-080ff70d8f5b80ba5',
    MinCount=1,
    MaxCount=1,
    InstanceType="t2.micro",
    KeyName="memCache",
    SecurityGroupIds=[
        'sg-0573fc5ab6ff250e9'
    ],
    UserData=user_data
)


