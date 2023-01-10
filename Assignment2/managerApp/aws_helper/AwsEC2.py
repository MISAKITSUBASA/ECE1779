import boto3
import random
import requests
user_data = '''#!/bin/sh
cd /home/ubuntu
git clone https://BillZou123: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@github.com/xius666/ece1779_A2.git
cd ece1779_A2
python3 -m venv venv
source venv/bin/activate
sudo pip3 install -r requirements.txt
sudo python3 run.py'''

class AwsEC2():
    '''
        a class for managing the ec2 on AWS
    '''

    def __init__(self, client):
        self.ec2Dict = {}  # dict of all the ec2 instances
        self.client = client
        self.corespond = []

    def getAllIps(self):
        ips = []
        for key, value in self.ec2Dict.items():
            if value['PublicIpAddress'] != "":
                ips.append(value['PublicIpAddress'])
        return ips

    def getInstancesCount(self):
        return len(self.ec2Dict.values())

    def updateAndRefreshDictInfo(self, new_create= None):
        """
            refresh the ec2 dictionary with the new info fetched
        """
        try:
            flag = 0
            while flag == 0:
                flag = 1
                self.ec2Dict.clear()
                response = self.client.describe_instances()
                for instance in response['Reservations']:
                    for i in instance['Instances']:
                        if 'State' in i.keys() and i['InstanceId'] != "i-05ccfbbdde95ebd29":
                            # print("id,  ", i['InstanceId'],"state ", i['State']['Name'])
                            if  i['State']['Name'] == 'running' or i['State']['Name'] == 'pending':
                                if 'PublicIpAddress' in i.keys():
                                    self.ec2Dict.setdefault(i['InstanceId'], {
                                        'Status': i['State']['Name'], "PublicIpAddress": i["PublicIpAddress"] 
                                        })
                                else:
                                    flag = 0
                                    self.ec2Dict.setdefault(i['InstanceId'], {
                                        'Status': i['State']['Name'], "PublicIpAddress": "" 
                                        } )
                if (new_create != None and new_create not in self.ec2Dict.keys()):
                    flag = 0
                elif new_create != None and new_create in self.ec2Dict.keys() and self.ec2Dict[new_create]["Status"]=="pending":
                    flag = 0
                # for id in self.ec2Dict.keys():
                #     if self.ec2Dict[id] == "":
                #         flag == 0
                # print(self.ec2Dict)
                        
        except Exception as error:
            print(error)

    def createNewInstance(self):
        # TODO: add UserData parameter
        response = self.client.run_instances(
            ImageId='ami-080ff70d8f5b80ba5',
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            KeyName="memCache",
            UserData=user_data
        )
        # print("create success")
        InstanceId = response["Instances"][0]["InstanceId"]
        self.updateAndRefreshDictInfo(InstanceId)
        
        # print(response["Instances"][0]["InstanceId"])
        # ip = self.ec2Dict[InstanceId]

        # re2 = requests.get("http://"+ ip["PublicIpAddress"] +":5000/backEnd/runjob")
        return response

    def stopInstance(self, instance_id):
        response = self.client.stop_instances(InstanceIds=[instance_id])
        return response

    def startInstance(self, instance_id):
        # TODO: add UserData parameter if restarting a created instance does not automatically run memcache code
        response = self.client.start_instances(InstanceIds=[instance_id])
        return response

    def terminateInstance(self, terminate_id):
        # self.updateAndRefreshDictInfo()
        response = self.client.terminate_instances(InstanceIds=[terminate_id])
        return response

    def __len__(self):
        return len(self.ec2Dict.values())

