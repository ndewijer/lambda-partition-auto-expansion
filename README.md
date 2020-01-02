# lambda-partition-auto-expansion

When expanding a Elastic Block Storage (EBS) volume connected to an Elastic Compute Cloud (Ec2) instance, be it through automation of manually through the AWS Console, there was a manual step to go into the operating system and expand the partition to take advantage of the newly allocated space. 

With this Lambda, this is now automated.

## Functionality
1. Something triggers the modification of an EBS Volume
2. Like any API call, the ModifyVolume call gets logged in Cloudtrail.
3. Cloudwatch events has a rule that triggers on a certain event and starts a lambda function.
4. The Lambda function
    * Checks if a change has been made to the volume's size. If not, it stops.
    * It finds the Instance connected to the volume being modified.
    * It will find the OS of the instance
    * It will trigger the right System Manger document to run against the instance
5. The document scans for changes to it's attached storage and expands any volume that has more partition-able space than is in use.

## To-Do
* Linux support


## CLI 


### Deploy project remotely

```bash
    $ sls deploy
```

### Deploy a function remotely

```bash
    $ sls deploy function -f partitionextension --region eu-west-1 
```

### UnDeploy or Destroy Lambda Deployment

```bash
    $ sls remove
```
