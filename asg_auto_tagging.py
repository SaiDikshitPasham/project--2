from __future__ import print_function
import json
import boto3
import logging
import os
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    #logger.info('Event: ' + str(event))
    asg_client = boto3.client('autoscaling')

    try:
        region = event['region']
        detail = event['detail']
        eventname = detail['eventName']
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        userType = detail['userIdentity']['type']
        #logger.info(str(detail))
        acc_sdlc = '1111111111'       #need to be cahnged as per your file

        if userType == 'IAMUser':
            user = detail['userIdentity']['userName']
        else:
            try:
                user = principal.split(':')[1]
            except:
                user = principal

        logger.info('principalId: ' + str(principal))
        logger.info('region: ' + str(region))
        logger.info('eventName: ' + str(eventname))
        #logger.info('detail: ' + str(detail))
        # Get the resourceid
        resourceid = detail['requestParameters']['autoScalingGroupName']
        logger.info('Writig tags To ASG ')
        default_tags = [{'Key': 'Owner', 'Value': user,'ResourceId': resourceid, 'ResourceType': 'auto-scaling-group', 'PropagateAtLaunch':False},
                                            {'Key': 'PrincipalId', 'Value': user, 'ResourceId': resourceid, 'ResourceType': 'auto-scaling-group', 'PropagateAtLaunch':False},
                                            {'Key': 'Region', 'Value': region, 'ResourceId': resourceid, 'ResourceType': 'auto-scaling-group', 'PropagateAtLaunch':False},
                                            {'Key': 'Account', 'Value': acc_sdlc, 'ResourceId': resourceid, 'ResourceType': 'auto-scaling-group', 'PropagateAtLaunch':False}]

        asg_client.create_or_update_tags(Tags = default_tags)
        logger.info('Writig tags To ASG  Completed ')
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return False
