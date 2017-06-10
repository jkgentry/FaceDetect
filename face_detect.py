import cv2
import sys
import os
import boto3
import smtplib

# Get current working directory
cwd = os.getcwd()

# Connect to Amazon S3
s3 = boto3.resource('s3')
rek = boto3.client('rekognition')

# smtp so we can email
# smtp = smtplib.SMTP("localhost")
sender = 'home@gentry.com'
receivers = ['gentry.jake@outlook.com']


cascPath = "haarcascade_frontalface_default.xml"
# Create the haar cascade
faceCascade = cv2.CascadeClassifier(cascPath)


# Loop through all new motioneye camera images
motionEyeDir = '/var/lib/motioneye/Camera1'

for directory in os.listdir(motionEyeDir):
    if os.path.isdir(motionEyeDir + '/' + directory):
        for filename in os.listdir(motionEyeDir + '/' + directory):
            if filename.endswith('.jpg') | filename.endswith('.png'):
                print(filename)
                # Read the image
                image = cv2.imread(filename)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                    # Detect faces in the image
                faces = faceCascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                    flags = cv2.CASCADE_SCALE_IMAGE
                )

                if len(faces) != 0:
                    # upload to s3 so we can use it on rekognition!
                    data = open(filename, 'rb')
                    s3.Bucket('gentry-camera').put_object(Key=filename, Body=data)
                    # Lets see if it is a match for someone
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


                    #email the results for the image
                    print(matchResponse)
                    print(labelResponse)
                    # smtp.sendmail(sender, receivers, matchResponse + labelResponse)
                    # now delete the image
        os.remove(motionEyeDir + '/' + directory +'/' +filename)
