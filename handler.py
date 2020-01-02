import json
import boto3
from botocore.exceptions import ClientError
import os
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def partitionextension(event, context):
    logger.info('## ENVIRONMENT VARIABLES')
    logger.info(os.environ)
    logger.info('## EVENT')
    logger.info(event)

    ec2 = boto3.resource('ec2')
    ssm = boto3.client('ssm')

    if 'ModifyVolumeResponse' not in event['detail']['responseElements'].keys():
        logger.info('No responseElements. Exiting')
        return False

    origVolSize = event['detail']['responseElements']['ModifyVolumeResponse']['volumeModification']['originalSize']
    targVolSize = event['detail']['responseElements']['ModifyVolumeResponse']['volumeModification']['targetSize']
    volumeID = event['detail']['responseElements']['ModifyVolumeResponse']['volumeModification']['volumeId']

    # Recognize that the changed volume is bigger than previously
    if origVolSize < targVolSize:
        logger.info('origVolSize: %s is smaller than targVolSize: %s. Expanding partition',
                    origVolSize, targVolSize)
        volSizeIncrease = True
    elif origVolSize > targVolSize:
        logger.info('origVolSize: %s is larger than targVolSize: %s. Stopping',
                    origVolSize, targVolSize)
        volSizeIncrease = False
        return None
    else:
        logger.warn('Here be dragons.')
        volSizeIncrease = 'Unknown'
        return None

    if volSizeIncrease == True:
        volume = ec2.Volume(volumeID)

    # Get InstanceID of volume
    try:
        instanceID = volume.attachments[0]['InstanceId']

        logger.info(volume.attachments)
        logger.info('Volume %s found. Attached to Instance %s',
                    volumeID, instanceID)
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
            logger.error('Volume %s does not exist.', volumeID)
        else:
            logger.error("Unexpected error: %s" % e)
        return None

    # Get OS of volume
    try:
        ssmInfo = ssm.describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [instanceID, ]}, ])

        logger.info(ssmInfo)
        instancePlatform = ssmInfo['InstanceInformationList'][0]['PlatformName']
        logger.info('Instance %s has operating system %s',
                    instanceID, instancePlatform)
    except ClientError as e:
        logger.error("Unexpected error: %s" % e)
        return None

    if "windows" in instancePlatform.lower():
        logger.info('Platform: Windows')
        runCommand = True

    elif "ubuntu" in instancePlatform or \
            "rhel" in instancePlatform or \
            "cent" in instancePlatform or \
            "amazon" in instancePlatform or \
            "ubuntu" in instancePlatform:
        logger.info('Platform: Unix')
        logger.warn('Unix Platform not yet supported.')
        runCommand = False
        return None
    else:
        logger.error("Unknown Platform: %s", instancePlatform)
        runCommand = False
        return None

    if runCommand == True:
        logger.info('Running expansion %s on instance %s',
                    os.environ['VolumeDocumentWin'], instanceID)
        try:
            executeCommand = ssm.send_command(InstanceIds=[instanceID, ],
                                              DocumentName=os.environ['VolumeDocument'],)
            logger.info(executeCommand)
            logger.info(executeCommand['Command']['CommandId'])

        except ClientError as e:
            logger.error("Unexpected error: %s" % e)

    getCommand = ssm.list_commands(CommandId=executeCommand['Command']['CommandId'],
                                   InstanceId=instanceID, MaxResults=1)
    getCommandStatus = getCommand['Commands'][0]['Status']

    logger.info(getCommand)

    while getCommandStatus == "Pending" or getCommandStatus == "InProgress":
        logger.info('waiting for %s to complete',
                    getCommand['Commands'][0]['DocumentName'])
        time.sleep(5)

        getCommand = ssm.list_commands(CommandId=executeCommand['Command']['CommandId'],
                                       InstanceId=instanceID, MaxResults=1)
        getCommandStatus = getCommand['Commands'][0]['Status']
    else:
        if getCommandStatus == "Success":
            logger.info("SSM job %s completed successfully.",
                        getCommand['Commands'][0]['DocumentName'], )
        else:
            logger.error("SSM job %s failed. Reason: %s",
                         getCommand['Commands'][0]['DocumentName'], getCommand['Commands'][0]['StatusDetails'])
