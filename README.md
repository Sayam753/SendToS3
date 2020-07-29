# SendToS3

* Written a python script to send backup files to AWS S3 bucket using Boto3.
* Searched the files within a given time interval along with regex.
* Implemented logging to collect errors and sent results via email using smtplib module.

## Backup system to AWS S3 bucket

When the backup is uploaded, it should be
SITE/TECHNOLOGY/HOSTNAME/YEAR/MONTH

Logs should be created and emailed when the backup is done.

We want the following parameters to be able to be
configurable in the script:

    1. Site from which logs are to be collected
    2. Hostname for the server
    3. AWS bucket to send to
    4. Absolute paths of all technologies in Key-Value Pairs in TECHNOLOGIES.
       Key is the path and value is a list ["tech_name", days_to_keep, "delete/keep"]
    5. Number of previous days to check for the files
    6. Sleep Time for the script to avoid network issues
    7. Receiver Email ID
    8. Email credentials to send the email
    9. Mail Server and Port Number for sending the emails
    10. Requirements to be installed
    11. AWS Credentials
    12. Add a cronjob to make this script run daily

### Prepare 10

The only requirement is boto3 library which is used to send files to s3 bucket.

    ```bash
    pip install boto3
    ```

### Prepare 11

For AWS credentials, create a file ~/.aws/credentials and
enter the details in the following format -

    ```none
    [default]
    aws_access_key_id=<your-aws-access-key>
    aws_secret_access_key=<your-aws-secret-key>
    ```

### Prepare 12

Add  an executable permission to the file.
Now add a cronjob.

    ```none
    45 23 * * * /path/to/python_file.py
    ```

This means the script will run daily at 23:45:00 UTC
