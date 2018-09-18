from __future__ import print_function
import json
import boto3
import logging
import os
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

mandatory_keys = 'tagging-VPC-mandatory-keys.txt'
mandatory_key_values = 'tagging-VPC-mandatory-key-values.txt'
'''
#This function is executed when the events CreateVolume, CreateSnapshot, CreateImage, RunInstances are detected.
#Once executed it scans across the tags bound to the resource, and if it lacks any of the default tags, it adds them with default values.
#This function ignores any user-set tags
#It also ignores any similar default values,  if they do not match it will add the default Key and Value.
'''
all_default_values = []
all_key_names = []
bucket_name = ''

def lambda_handler(event, context):

    # logger.info('Event: ' + str(event))
    # print('Received event: ' + json.dumps(event, indent=2))

    ids = []
    client = boto3.client('elbv2')

    try:
        region = event['region']
        detail = event['detail']
        eventname = detail['eventName']
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        userType = detail['userIdentity']['type']
        acc_sdlc = 'ptype'
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
        logger.info('detail: ' + str(detail))

        if not detail['responseElements']:
            logger.warning('Not responseElements found')
            if detail['errorCode']:
                logger.error('errorCode: ' + detail['errorCode'])
            if detail['errorMessage']:
                logger.error('errorMessage: ' + detail['errorMessage'])
            return False


        if eventname == 'CreateLoadBalancer':
            ids.append(detail['requestParameters']['loadBalancerName'])
            logger.info(ids)

        else:
            logger.warning('Not supported action')

        """
        Default tags list to add more automated tags to resources
        To add additional tags, add to the end of the list separated by a comma.
        MAXIMUM of 50 Tags TOTAL including ones already set.
        {'Key': '******','Value': ******}
        """


        if ids:
            get_bucket_name()
            get_data_from_files()
            for resourceid in ids:
                try:
                    princip = principal.split(':')[0]
                except:
                    princip = principal
                    res_list = [resourceid]
                print('Tagging resource ' + resourceid)
                #========================
                #Default tags list to add more automated tags to resources
                #To add additional tags, add to the end of the list separated by a comma.
                #MAXIMUM of 50 Tags TOTAL including ones already set.
                #{'Key': '******','Value': ******}
                #========================
                default_tags = [{'Key': 'Owner','Value': user}, {'Key': 'PrincipalId','Value': princip}, {'Key': 'Region', 'Value': region}, {'Key': 'Account', 'Value': acc_sdlc}]
                if len(all_key_names) > 0:
                    c = 0
                    for key in all_key_names:
                        default_tags.append({'Key': key, 'Value': all_default_values[c]})
                        c = c+1

                """
                If statements for individual resources, from top to bottom- Instances- Images- Volumes- Snapshots
                """

                if eventname == 'CreateLoadBalancer':
                    print('Attempting to bind tags to elb: ', resourceid)
                    for ec2ELB in client.describe_load_balancers(Names=[{'Name': 'loadBalancerName', 'Values': [resourceid]}])['LoadBalancers']:
                        if 'Tags' in ec2ELB :
                            #Pass all elb tags in to tag_gen
                            tags = ec2ELB['Tags']
                            tag_gen(tags, res_list,default_tags)
                        else:
                            #If no tags are found, add the defaults
                            client.add_tags(Resources=res_list, Tags=default_tags)
                else:
                    logger.warning('Unrecognised Event')
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return False



"""
Function for scanning and applying new tags (if any)
"""
def tag_gen(tags, res_list,default_tags):
    client = boto3.client('elbv2')
    new_tags_list = []
    #Add any current tags to the new tag list (newtags)
    for tag in tags:
        name = tag['Key']
        try:
            #Checks to see if the tag name is reserved
            #Create_tags disallows any changes if reserved tags are used
            if name.startswith('aws:'):
                print(name, ' is a reserved tag, excluding from creation.')
            else:
                print(name, ' is not a reserved tag')
                new_tag = {'Key': tag['Key'], 'Value': tag['Value']}
                print('Detected tag, adding to new dict ', new_tag)
                new_tags_list.append(new_tag)
        except Exception as e:
            print(e)
    """
    Calls add_default_tags to add any default tags it is missing.
    """
    final_tags = add_default_tags(default_tags, new_tags_list)
    print('Tags to add: ',final_tags)
    """
    Creates the tag for the resource
    """
    try:
        #Create the tags for the resource.
        print('Creating tags')
        print('Resource: ', res_list, 'Adding tags: ', final_tags)
        ec2.create_tags(Resources=res_list, Tags=final_tags)
    except Exception as e:
        print('Error when creating tags on Resource: ', res_list, '\n', e)

"""
Function for checking the new tag list for the default tags
"""
def add_default_tags(default_tags, new_tags_list):
    print('Comparing default_tags and new_tags_list for any missing tags')
    missing_tags_list = []
    final_tags_list = []
    #Loop through default tags

    try:
        for x in default_tags:
            in_list = False
        #Check against all tags in new_tags_list
            for y in new_tags_list:
                if x['Key'] == y['Key']:
                    #If in list, set to true.
                    in_list = True
        #Set to false if not in the list and append to the end.
            if in_list == False:
                new_tag = {'Key': x['Key'], 'Value': x['Value']}
                print('Missing default tag ',new_tag)
                missing_tags_list.append(new_tag)
        #Checks to see if any tags were missed.
        if len(missing_tags_list) > 0:
            print('Combining lists ', missing_tags_list, '  ' , new_tags_list)
            final_tags_list = missing_tags_list + new_tags_list
        else:
            final_tags_list = new_tags_list
            return final_tags_list
    except Exception as e:
        print('Error when comparing lists for default tags')
        print(e)
    return final_tags_list
    #============================================
    #Get bucket name to pull the tag files from
    #============================================
def get_bucket_name():
    global bucket_name
    logger.info('Getting bucket details')
    #Call the sdlc defined by Terraform as an Environment Variable
    acc_sdlc = 'ptype'
    bucket_region = 'us-east-1'
    local_bucket_name = 'global-variables-'+acc_sdlc+'-'+bucket_region
    bucket_name = local_bucket_name
    #============================================
    #Get all the key names from the S3 Bucket
    #============================================
def get_data_from_files():
    logger.info('Getting Data from files')
    global all_key_names
    global all_default_values
    s3res = boto3.resource('s3')
    key_bod = ''
    def_bod = ''
    all_key_names = []
    all_default_values = []
    found_key = False
    try:
        try:
            keys = s3res.Object(bucket_name, key = mandatory_keys)
            key_bod = keys.get()['Body'].read().decode("UTF-8")
        except Exception as e:
            logger.error("Error when retrieving "+ str(mandatory_keys) + ' reason: ' + str(e))
            return
        if len(key_bod) > 0:
            c = 0
            for line in key_bod:
                if line == 'null' or None and c == 0:
                    return None
                all_key_names.append(line)
                c = c + 1
            if len(all_key_names) <= 0:
                all_key_names = None
            found_key = True
        #=====================================================
        #Get all the default values from the key specified
        #=====================================================
        try:
            defaults = s3res.Object(bucket_name, key = mandatory_key_values)
            def_bod = defaults.get()['Body'].read().decode("UTF-8")
        except Exception as e:
            logger.error('Error when retrieving ' + str(mandatory_key_values) + ' reason: '+ str(e))
            return
        if len(def_bod) > 0:
            d = 0
            for line in def_bod:
                if line == 'null' or None and d == 0:
                    return None
                all_default_values.append(line)
                d = d + 1
            if len(all_default_values) <= 0:
                all_default_values = None
        #============================================================
        #Parse Files and convert single characters to string values
        #============================================================
        if found_key == True:
            d = ''
            k = ''
            for c in all_key_names:
                k = k + c
            for c in all_default_values:
                d = d + c
            temp_key_names = []
            temp_def_vals = []
            temp_key_names.append(k.splitlines())
            temp_def_vals.append(d.splitlines())
            all_key_names = temp_key_names[0]
            all_default_values = temp_def_vals[0]

    except:
        logger.error('Error when retrieving Keys and/or Defaults. Function Terminated')
        return