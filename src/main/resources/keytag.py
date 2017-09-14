import boto3
import difflib
import logging
import re
import os


logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""
#Variables for tags
"""
#Default Bucket to contain all the tags, 
bucket_name = ''
#Ignore list for any tag keys to ignore.
ignore_list = []
#Maximum amount of changes to tags to get them to match.
max_changes = 1

"""
#Global Variables, changing these will effect the code structure.
#Do Not Change
"""
all_key_names = []
logger = logging.getLogger()
logger.setLevel(logging.INFO)
all_default_values = []
changed_key = []
major_error = []
region = ''
    #===============================================
    #Init function, checks to see if it has been ran by itself or Autotag
    #===============================================
def lambda_handler(event, context):
    global all_key_names
    global all_default_values
    global major_error
    global changed_key
    global region
    all_key_names = []
    all_default_values = []
    region = event['region']
    try:
        detail = event['detail']
        eventname = detail['eventName']
        princip = detail['userIdentity']['principalId']
        #=====================================================
        #Checks the event trigger for what created the event, if it is anything AutoTag
        #related, it automatically terminates
        #=====================================================
        if 'TagKeyValidator' in princip:
            logger.info('Event triggered by itself- Terminating Function')
            return
        elif 'AutoTag' in princip:
            logger.info('Event triggered by AutoTag- Terminating Function')
            return
        principalId = princip.split(':')[0]
    except Exception as e:
        logger.error('Failed to get Event, Terminating')
    #=======================================================
    #If the event has been triggered by a correct mean, the main function executes
    #=======================================================
    else:
        get_bucket_name()
        get_data_from_files()
        if all_default_values == None or all_key_names == None:
            logger.error('Data not found in Bucket')
        logger.info('Not Triggered by Autotag or KeyValidator')
        ids = []
        try:
        #Gather the Resource ID's bound to the event
            for index, resid in enumerate(detail['requestParameters']['resourcesSet']['items']):
                id = detail['requestParameters']['resourcesSet']['items'][index]['resourceId']
                ids.append(id)
                logger.info(str(ids))
        except Exception as e:
            print(e)
            logger.warn('ResourceId not Detected')
        if ids:
            for resourceid in ids:
                check_keys_for_consistency(resourceid)
                report_func()

    #==================================================
    #Checks the Value under the key for an empty or whitespace filled string
    #==================================================
def check_empty_val(resourceid):
    ec2cli = boto3.client('ec2')
    #Loop through the individual tags to check for whitespace or 'none' 
    for tag in ec2cli.describe_tags(Filters = [{'Name': 'resource-id', 'Values': [resourceid],},],)['Tags']:
        print('Checking empty value on tag: ', tag)
        key = tag['Key']
        value = tag['Value']
        try:
            key_index = all_key_names.index(key)
        except:
            key_index = -1
        #Checks against AWS reserved tags (These cannot be changed regardless)
        if key.startswith('aws:'):
            logger.info('Tag: ',str(key), ' is a reserved tag, excluding from the search')
        else:
            if value.isspace() or value == '' or value == None:
                try:
                    print('Tag: ',key, ' has no value assigned. Assigning default value')
                    if key_index == -1:
                        new_tag = [{'Key':key, 'Value':'DefVal'}]
                    old_tag = [{'Key':key, 'Value': value}]
                    new_tag = [{'Key':key, 'Value':all_default_values[key_index]}]
                    #Delete the active tag
                    ec2cli.delete_tags(Resources = [resourceid], Tags = old_tag)
                    #Replace the deleted tag with a new one under the same Key, but as a default value.
                    ec2cli.create_tags(Resources = [resourceid], Tags = new_tag)
                    message = "<li>Old: - " + str(old_tag) + "  New: -" + str(new_tag) + """  Reason: Value empty or contained just whitespace</li>"""
                    changed_key.append(message)
                except Exception:
                    logger.error('Error when setting default value')
                    message = '<br/><br/> Additional Info: Error when setting default value'
                    major_error.append(message)
        
        
    #==========================================
    #Check keys names against the list
    #==========================================
def check_keys_for_consistency(resourceid):
    global changed_key
    ec2res = boto3.resource('ec2')
    ec2cli = boto3.client('ec2')
    all_key_lowercase_names = []
    key_index = 0
    changed_key = []
    #Remove symbols and change the Keynames to lowercase
    for defkey in all_key_names:
        #Remove all symbols from the default key sfiles
        re.sub("[^a-zA-Z]+", "", defkey)
        #Just incase the filename isn't lowercase
        defkey = defkey.lower()
        all_key_lowercase_names.append(defkey)
    for tag in ec2cli.describe_tags(Filters = [{'Name': 'resource-id', 'Values': [resourceid],},],)['Tags']:
        print('Checking for misspelt or unrecognized name on tag: ', tag)
        key = tag['Key']
        value = tag['Value']
        lower_key = key.lower()
        #Ignore reserved tags as these cannot be changed.
        if key.startswith('aws:'):
            logger.info(str(key), ' is a reserved tag, excluding from the search')
            
            
            
        #=================================================================================
        #Compare unrecognized Key against the listed keys in the S3 bucket
        #=================================================================================
        elif lower_key not in all_key_lowercase_names and key not in ignore_list:
            try:
                #Use the deflib Python library to compare the KeyValue against the entries in the lowercase 
                #Pull any close matches
                matches = difflib.get_close_matches(lower_key, all_key_lowercase_names)  
            except Exception as e:
                logger.error('Error when matching TagName to TagNameList')
                print(e)
            if len(matches) == 1:
                comp = StringComp(str(matches[0]), str(lower_key))
                if comp <= max_changes:
                    #Compare the checked tag against the list of tags from the s3 bucket to get the keyname index
                    key_index = all_key_lowercase_names.index(matches[0])
                    if lower_key == all_key_lowercase_names[key_index]:
                        #Key is as should be, but this code should be unreachable, do nothing.
                        print('\n')
                    else:
                        old_tag = [{'Key':key, 'Value': value}]
                        new_tag = [{'Key':all_key_names[key_index], 'Value':tag['Value']}]
                        #Replace the deleted tag with a new one under the same Key, but as a default value.
                        print('Deleting tags: ', tag, ' on: ', resourceid)
                        ec2cli.delete_tags(Resources = [resourceid], Tags = old_tag)
                        print('Creating tag: ', new_tag, ' on ', resourceid)
                        ec2cli.create_tags(Resources = [resourceid], Tags = new_tag)
                        #Logging line for the email notification
                        message = "<li>Old: -" + str(old_tag) + "  New: - " + str(new_tag) + """   Reason: misspelt or unrecognized name on tag</li>"""
                        changed_key.append(message)
                else:
                    print('Maximum amount of changes exceeded to match keys.')
            elif len(matches) > 1:
                #What to do if multiple matches have been found.
                message = '<br/><br/> Additional Info:  Found multiple matches for tag: ' + tag
                major_error.append(message)
            else: 
                print('No matches found for tag: ', key)

        #========================================================================
        #Do a case sensitive Tag Key check, if it doesn't match then change it.
        #========================================================================
        elif lower_key in all_key_lowercase_names:
            print('Checking keys for matching case')
            key_index = all_key_lowercase_names.index(lower_key)
            temp_key = all_key_names[key_index]
            keys_match = True
            n = 0
            for char in key:
                if ord(key[n]) != ord(temp_key[n]):
                    keys_match = False
                n = n +1
            if keys_match == False:
                old_tag = [{'Key':key, 'Value': value}]
                print('Keys dont match, making changes')
                new_tag = [{'Key': all_key_names[key_index], 'Value':tag['Value']}]
                print('Deleting tags: ', tag, ' on: ', resourceid)
                ec2cli.delete_tags(Resources = [resourceid], Tags = old_tag)
                print('Creating tag: ', new_tag, ' on ', resourceid)
                ec2cli.create_tags(Resources = [resourceid], Tags = new_tag)
                #Logging line for the email notification
                message = "<li>Old: - " + str(old_tag) + "  New: - " + str(new_tag) + """   Reason: Key did not meet case requirements</li>"""
                changed_key.append(message)
    check_empty_val(resourceid)
    #============================================
    #Get the bucket for this particular account
    #============================================
def get_bucket_name():
    global bucket_name
    #Call the sdlc defined by Terraform as an Environment Variable
    acc_sdlc = os.environ['account']
    bucket_region = os.environ['bucket_region']
    local_bucket_name = 'global-variables-'+acc_sdlc+'-'+bucket_region
    bucket_name = local_bucket_name
    #============================================
    #Get all the key names from the S3 Bucket
    #============================================
def get_data_from_files():
    global all_key_names
    global all_default_values
    s3res = boto3.resource('s3')
    key_bod = ''
    def_bod = ''
    try:
        try:
            keys = s3res.Object(bucket_name, key = 'tag-ec2-instance-all-keys.txt')
            key_bod = keys.get()['Body'].read().decode("UTF-8")
        except Exception as e:
            message = "<br/><br/> Error when retrieving tag-ec2-instance-keys.txt reason: " + str(e)
            major_error.append(message)
        c = 0
        for line in key_bod:
            if line == 'null' or None and c == 0:
                return None
            all_key_names.append(line)
            c = c + 1
        if len(all_key_names) <= 0:
            all_key_names = None
        #=====================================================
        #Get all the default values from the key specified
        #=====================================================
        try:
            defaults = s3res.Object(bucket_name, key = 'tag-ec2-instance-default-values.txt')
            def_bod = defaults.get()['Body'].read().decode("UTF-8")
        except Exception as e:
            message = '<br/><br/> Error when retrieving tag-ec2-instance-defaults.txt reason: '+ str(e)
            major_error.append(message)
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
        message = '<br/><br/>Fatal Error when retrieving Keys and/or Defaults. Function Terminated'
        major_error.append(message)
        
        

    #==========================================
    #Reporting function
    #==========================================
def report_func():
    email_body = build_list()
    sescli = boto3.client('ses', region_name = 'us-east-1')
    fromid = "AWS-Alerts-NoReply@tsys.com"
    toids = "tdavey@tsys.com"
    emailsubject = "Tag Key Validation Report - " + str(region)
    if email_body == ' ':
        print('Nothing to report')
        return
    else:
        #Build the email structure
        sesresponse = sescli.send_email(
                        Source = fromid,
                        Destination={
                            'ToAddresses': [
                                toids
                                ],
                            },
                        Message={
                            'Subject': { 
                                'Charset': 'UTF-8',
                                'Data': emailsubject
                            },
                            'Body': {
                                'Html':{
                                        'Charset': 'UTF-8',
                                        'Data': email_body
                                        }
                                    }
                                }
                           )
        print('Emailing response')
        return
    #===========================================================
    #Build the Changed_Key and Major_Error lists in HTML form
    #===========================================================
def build_list():
    html_keys_list = ''
    html_errors_list = ''
    if len(changed_key) > 0:
        for log in changed_key:
            line = log
            html_keys_list = html_keys_list + line
        html_keys_list = html_keys_list
        key_body = '<div><h3>Changed or Modified Tags:</h3>'+html_keys_list +' </div>'
    else:
        key_body = ' '
    if len(major_error) > 0:
        for error in major_error:
            line = error
            html_errors_list = html_errors_list + line
        html_errors_list = html_errors_list
        error_body = '<div><h3> Errors: </h3>'+html_errors_list + '</div>'
    else:
        error_body = ' '
    if len(changed_key) > 0 and len(major_error) > 0:
        email_body = '<html><head><style> ul {padding-left: 10p;x margin: 0; padding: 0; float:left;}</style></head><body><ul>'+key_body+'</ul><br/><br/><ul>'+error_body+'</ul></body></html>'
    elif len(changed_key) > 0 and len(major_error) == 0:
        email_body = '<html><head><style> ul {padding-left: 10p;x margin: 0; padding: 0; float:left;}</style></head><body><ul>'+key_body+'</ul></body></html>'
    elif len(changed_key) == 0 and len(major_error) > 0:
        email_body = '<html><head><style> ul {padding-left: 10p;x margin: 0; padding: 0; float:left;}</style></head><body><ul>'+error_body+'</ul></body></html>'
    else:
        email_body = ' '
    return email_body
    
    
    #===================================================================
    #String comparer for finding difference between two strings
    #===================================================================
def StringComp(str1, str2):
    changes = 0
    str1chars = sorted(str1)
    str2chars = sorted(str2)
    if len(str1) > len(str2):
        if str1chars[:len(str2)] != str2chars:
            changes = changes + 1
    elif len(str2) > len(str1):
        if str2chars[:len(str1)] != str1chars:
            changes = changes + 1
    return changes 
