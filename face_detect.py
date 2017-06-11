import cv2
import sys
import os
import boto3
import smtplib
import json
import logging

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename
from email.mime.image import MIMEImage


logging.basicConfig(filename='/var/log/face_detect.log',level=logging.DEBUG)
# Connect to Amazon S3
s3 = boto3.resource('s3')
rek = boto3.client('rekognition')
cascPath = "/home/pi/haarcascade_frontalface_default.xml"
# Create the haar cascade
faceCascade = cv2.CascadeClassifier(cascPath)


# Loop through all new motioneye camera images
motionEyeDir = '/var/lib/motioneye/Camera1'

def send_mail(send_to, subject, text, file=None):
    msg = MIMEMultipart()
    msg['From'] = 'bink114@gmail.com'
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    if file:
        image = MIMEImage(open(motionEyeDir + '/' + directory +'/' + filename, 'rb').read())
        msg.attach(image)

    smtp = smtplib.SMTP()
    smtp.connect("smtp.gmail.com", 587)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login("bink114@gmail.com", "")
    smtp.sendmail(msg['From'], send_to, msg.as_string())
    smtp.close()

for directory in os.listdir(motionEyeDir):
    if os.path.isdir(motionEyeDir + '/' + directory):
        for filename in os.listdir(motionEyeDir + '/' + directory):
            if filename.endswith('.jpg') or filename.endswith('.png'):
                logging.info(motionEyeDir + '/' + directory + '/' +filename)

                # Read the image
                image = cv2.imread(motionEyeDir + '/' + directory +'/' + filename)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                # Detect faces in the image
                faces = faceCascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(30, 30),
                    flags = cv2.CASCADE_SCALE_IMAGE)

                if len(faces) != 0:
                    logging.info('Face detected, checking for matches')
                    # upload to s3 so we can use it on rekognition!
                    data = open(motionEyeDir + '/' + directory +'/' + filename, 'rb')
                    s3.Bucket('gentry-camera').put_object(Key=filename, Body=data)
                    # Lets see if it is a match for someone
                    try:
                        matchResponse = rek.search_faces_by_image(
                                    CollectionId='friends',
                                    FaceMatchThreshold=95,
                                    Image={
                                        'S3Object': {
                                            'Bucket' : 'gentry-camera',
                                            'Name' : filename
                                        }
                                    },
                                    MaxFaces=5
                                )
                    except Exception as e:
                        matchResponse = ""
                        logging.error("Face search Exception")
                    # grab some labels to help us know what is going on
                    labelResponse = rek.detect_labels(
                                Image={
                                    'S3Object': {
                                        'Bucket': 'gentry-camera',
                                        'Name': filename
                                    },
                                },
                                MaxLabels=123,
                                MinConfidence=60,
                            )

                    # email the results for the image
                    matchResponsePretty = json.dumps(matchResponse,
                                                    sort_keys=True,
                                                    indent=4,
                                                    separators=(',', ': '))

                    labelResponsePretty = json.dumps(labelResponse,
                                                    sort_keys=True,
                                                    indent=4,
                                                    separators=(',', ': '))
                    logging.info(matchResponsePretty)
                    logging.info(labelResponsePretty)

                    # send an email!
                    send_mail(
                        'gentry.jake@outlook.com',
                        'Camera Alert',
                        matchResponsePretty + labelResponsePretty,
                        data
                        )
                # now delete the image
                logging.info("Deleting image")
                os.remove(motionEyeDir + '/' + directory +'/' + filename)
