## Import VMWare VM image for EC2
1. Prep Linux VM
   * GRUB or GRUB2 for bootloader
   * / FS type must be: EXT[234], BTRFS, JFS or XFS
   * Remove VMWare tools
   * Disable anti-virus or IDS.
   * Disconnect CD-ROM drives
   * Configure network to use DHCP
   * Enable SSH. Enable public key only, non-root user.
   * Shutdown the VM
1. Export VM in OVA format
1. Upload image to S3. Note bucket and key
1. Create vmimport IAM role. [https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-image-import.html]
1. Create containers.json file to reference the S3 OVA file
    ```javascript
    [
      {
        "Description": "VM description",
        "Format": "ova",
        "UserBucket": {
          "S3Bucket": "vmimages",
          "S3Key": "myvm.ova"
        }
    }]
    ```
1. From AWSCLI 
    `aws ec2 import-image --description "VM Description" --license-type BYOL --disk-containers file://containers.json`
1. Check status of the (async) import 
    `aws ec2 describe-import-image-tasks` 
    Output looks like: 
```
    {
        "ImportImageTasks": [
            {
                "Status": "completed", 
                "LicenseType": "BYOL", 
                "Description": "VM Description", 
                "ImageId": "ami-c377ffa2", 
                "Platform": "Linux", 
                "Architecture": "x86_64", 
                "SnapshotDetails": [
                    {
                        "UserBucket": {
                            "S3Bucket": "vmimages", 
                            "S3Key": "myvm.ova"
                        }, 
                        "DeviceName": "/dev/sda1", 
                        "DiskImageSize": 629867008.0, 
                        "SnapshotId": "snap-0febe74db7b23ce82", 
                        "Format": "VMDK"
                    }
                ], 
                "ImportTaskId": "import-ami-ffvhx7fj"
            }, 
            {
                "Status": "completed", 
                "LicenseType": "BYOL", 
                "Description": "VM Description", 
                "ImageId": "ami-4c129a2d", 
                "Platform": "Linux", 
                "Architecture": "x86_64", 
                "SnapshotDetails": [
                    {
                        "UserBucket": {
                            "S3Bucket": "vmimages", 
                            "S3Key": "myvm.ova"
                        }, 
                        "DeviceName": "/dev/sda1", 
                        "DiskImageSize": 1536385536.0, 
                        "SnapshotId": "snap-0b1a1352354876400", 
                        "Format": "VMDK"
                    }
                ], 
                "ImportTaskId": "import-ami-fg4a4qgf"
            }
        ]
    }
```
  
### CloudInit UserData

Use the following line in a bash script to redirect output to console to be readable via the aws CLI
```exec > >(logger -t user-data -s 2>/dev/console) 2>&1```
read with ```aws ec2 get-console-output --instance-id <instID>```

```
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash -xe
          # move ssh port to 80
          /usr/sbin/semanage port -m -t ssh_port_t -p tcp 80
          /usr/bin/firewall-offline-cmd --add-port=80/tcp
          /usr/bin/sed -i '/^Port *[0-9]/d' /etc/ssh/sshd_config
          echo -e "\nPort 80" >>/etc/ssh/sshd_config
          /usr/bin/systemctl restart sshd
          sleep 10; /usr/bin/firewall-cmd --reload
          echo "UserData script completed."
```
