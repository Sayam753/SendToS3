# Path to python3

import os, datetime, logging, boto3, time, zipfile, socket, pathlib, smtplib, io, sys
from botocore.exceptions import ClientError, EndpointConnectionError
from email.message import EmailMessage

'''
Backup system to AWS S3 bucket

When the backup is uploaded, it should be
SITE/TECHNOLOGY/HOSTNAME/YEAR/MONTH

Logs should be created and emailed when the backup is done. 

We want the following parameters to be able to be
configurable in the script:

    1. Site from which logs are to be collected
    2. Hostname for the server
    3. AWS bucket to send to
    4. Absolute paths of all technologies in Key-Value Pairs in TECHNOLOGIES. Key is the path and value is a list ['tech_name', days_to_keep, 'delete/keep']
    5. Number of previous days to check for the files
    6. Sleep Time for the script to avoid network issues
    7. Receiver Email ID
    8. Email credentials to send the email
    9. Mail Server and Port Number for sending the emails
    10. Requirements to be installed
    11. AWS Credentials
    12. Add a cronjob to make this script run daily

Prepare -
10. The only requirement is boto3 library which is used to send files to s3 bucket.
pip install boto3

11. For AWS credentials, create a file ~/.aws/credentials and enter the details in the following format -
[default]
aws_access_key_id=<your-aws-access-key>
aws_secret_access_key=<your-aws-secret-key>

12. Add  an executable permission to the file.
Now add a cronjob.
Eg - 45 23 * * * /path/to/python_file.py
This means the script will run daily at 23:45:00 UTC
'''

# Set up the required parameters
SITE = 'test13'
HOSTNAME = 'my_host' # If default hostname is preferred, leave it as None
BUCKET = 'forsendingtoaws'
TECHNOLOGIES = {
    # 'ABSOLUTE PATH': ['TECHNOLOGY NAME', DAYS_TO_CHECK, 'delete' or 'keep'],
    # '/var/www/httpd/*.gz': ['httpd', 2, 'delete'],
    '/Users/user/Desktop/sem/sem\ 3/oop/assignment-6/*.class': ['java', 90, 'delete'],
}
DAYS_TO_CHECK = 5
SLEEP_TIME = 5
MAIL_TO = 'sayam.k18@iiits.in'
EMAIL_FROM = 'sayamkumar049@gmail.com'
EMAIL_PASSWORD = os.environ.get('pass')
MAIL_SERVER = 'smtp.gmail.com'
PORT_NO = 465

if HOSTNAME is None:
    HOSTNAME = socket.gethostname()

def init():
    '''
    Prepare the environment. For more information on logging - 
    https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
    '''
    output_buffer = io.StringIO()
    logger = logging.getLogger(f'{SITE} backup') # Initialise the logger
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-15s %(message)s', datefmt='%Y-%m-%d %H:%M:%S') # Customer formatter
    handler = logging.StreamHandler(output_buffer)
    handler.setFormatter(formatter) # Add formatter to handler
    logger.addHandler(handler) # Add handler to logger
    return output_buffer, logger

def send_files(TODAY, logger):
    '''
    Send files to s3 bucket
    '''
    total_technologies = len(TECHNOLOGIES)
    successfully_uploaded = 0
    s3_client = boto3.client('s3')
    try: # Check if the bucket exists
        response = s3_client.head_bucket(Bucket=BUCKET)
    except EndpointConnectionError as e: # No internet connection
        logger.error(f'{e} for bucket {BUCKET}')
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 403:
            logger.error(f'Private Bucket {BUCKET}. Forbidden Access!')
        elif error_code == 404:
            logger.error(f'Bucket {BUCKET} Does Not Exist!')
    else:
        if not TECHNOLOGIES: # Dictionary is empty
            logger.error("No technologies specified for backup in the dict TECHNOLOGIES")
            return
        for path in TECHNOLOGIES: # Iterate over all technologies
            file_pattern = os.path.basename(path) # Capture the last regex format
            absolute_path = os.path.dirname(path.replace('\ ', ' ')) # Capture the absolute directory path
            files_list = list(pathlib.Path(absolute_path).glob(file_pattern)) # Cature list of all matched files
            logger.info(f'Starting backup from {absolute_path} for {TECHNOLOGIES[path][0]}')

            if (not isinstance(TECHNOLOGIES[path], list)) or (len(TECHNOLOGIES[path])!=3): # Incorrect list
                logger.error(f'''Incorrect value for {absolute_path}. It should be a list ['tech_name', days_to_keep, 'delete/keep']''')
                continue
            if not os.path.isabs(path): # Incorrect path
                logger.error(f'Incorrect absolute path from {absolute_path} for {TECHNOLOGIES[path][0]}')
                continue
            if not file_pattern: # Incorrect regex format
                logger.error(f'No regex format found from {absolute_path} for {TECHNOLOGIES[path][0]} files')
                continue
            if not files_list: # No files found with given format
                logger.warning(f'No files found from {absolute_path} for {TECHNOLOGIES[path][0]}')
                continue
            
            # Defining variables
            tech_name = TECHNOLOGIES[path][0]
            days = TECHNOLOGIES[path][1]
            if days is None:
                days = DAYS_TO_CHECK
            delete_option = TECHNOLOGIES[path][2]
            files_sent = 0                      # Total number of files successfully sent
            exception_files = 0                 # Total number of files for which exception was raised while uploading
            undeleteable_files = 0              # Total number of files unable to delete

            for file_path in files_list:
                last_modified_date = datetime.datetime.fromtimestamp(os.stat(file_path).st_mtime).date()
                if (TODAY-last_modified_date).days<=days: # File modified under given interval
                    file_name = os.path.basename(file_path)
                    try:
                        destination_folder = os.path.join(SITE, tech_name, HOSTNAME, str(last_modified_date.year), str(last_modified_date.month))
                        s3_client.upload_file(str(file_path), BUCKET, f'{destination_folder}/{file_name}')   
                    except Exception:
                        exception_files += 1 # Exception file found
                        logger.error(f'An error occured while tring to upload {file_name}')
                    else:
                        files_sent += 1 # File successfully sent 
                        if delete_option == 'delete':
                            try:
                                os.remove(file_path)
                            except PermissionError:
                                undeleteable_files += 1 # Unable to delete a file
                                logger.error(f'Permission denied for deleting {file_path}. Delete it manually')
                        time.sleep(SLEEP_TIME)

            if exception_files == 0:
                if files_sent == 0:
                    logger.warning(f'No files found with given modification interval from {absolute_path} for {tech_name}')
                else:
                    if undeleteable_files == 0:
                        successfully_uploaded += 1
                        if delete_option == 'delete':
                            logger.info(f'Successfully uploaded {files_sent} files from {absolute_path} for {tech_name}. Successfully deleted {files_sent} files')
                        else:
                            logger.info(f'''Successfully uploaded {files_sent} files from {absolute_path} for {tech_name}. delete_option='keep\'''')
                    else:
                        logger.warning(f'Successfully uploaded {files_sent} files from {absolute_path} for {tech_name} but error in deleting {undeleteable_files} files')
            else:
                if delete_option == 'delete':
                    logger.warning(f'For {tech_name}: Successful uploading of {files_sent} files, Unsuccessful uploading of {exception_files} files, Undeletable files {undeleteable_files}')
                else:
                    logger.warning(f'''For {tech_name}: Successful uploading of {files_sent} files, Unsuccessful uploading of {exception_files} files, delete_option='keep\'''')

        logger.info(f'Total Technologies: {total_technologies}')
        logger.info(f'Sucessfully uploaded Technologies: {successfully_uploaded}')
        if total_technologies > successfully_uploaded:
            logger.warning(f'Issues in {total_technologies-successfully_uploaded} technologies')
        else:
            logger.info(f'Issues in {total_technologies-successfully_uploaded} technologies')

def close_logger(output_buffer, logger):
    '''
    Close logger and output_buffer
    '''
    logging.shutdown()
    handler = logger.handlers[0] # If added multiple handlers, remove them all
    logger.removeHandler(handler)
    handler.flush()
    handler.close() # Close the StreamHandler
    output_buffer.close() # Close the buffer

def send_email(TODAY, output_buffer, logger):
    '''
    Format and send an email to MAILTO address.
    '''
    is_successful = False
    msg = EmailMessage()
    msg['Subject'] = f'AWS backup for {SITE} dated: {TODAY}'
    msg['From'] = EMAIL_FROM
    msg['To'] = MAIL_TO

    try:
        smtp = smtplib.SMTP_SSL(MAIL_SERVER, PORT_NO)  # Connect to Mail Server
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD) # Login
        msg.set_content(output_buffer.getvalue()) # Set the content
        smtp.send_message(msg) # Send message
        smtp.quit()
        return True
    except socket.gaierror as e:
        logger.error("No internet connection/Invalid host name")
    except TimeoutError:
        logger.error("Operation timed out. Try after some time")
    except smtplib.SMTPAuthenticationError:
        logger.error("The username and/or password you entered is incorrect")
    except Exception as e:
        logger.error(e) # All exceptions derived from base Exception Class
    
    return False

def backup():
    '''
    Take backup and send an email
    '''
    output_buffer, logger = init()
    current_version = sys.version_info # Checking the current version
    if current_version[0] != 3 or current_version[1] < 6:
        logger.error('Required python version should be at least 3.6. Version found %d.%d.%d' % (current_version[0], current_version[1], current_version[2]))
        logger.error('0 backup files sent to the bucket')
    else:
        logger.info("Successfully created the environment")
        TODAY = datetime.date.today() # Today's date
        send_files(TODAY, logger) # send_files utility
    logger.info(f'Sending email to {MAIL_TO}')
    is_success = send_email(TODAY, output_buffer, logger)
    if not is_success:
        logger.error("Unable to send email. Printed all the logs on the console")
        print(output_buffer.getvalue())
    else:
        print(f'Executed the backup script and sent an email to {MAIL_TO}')
    close_logger(output_buffer, logger)

backup()