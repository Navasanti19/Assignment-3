import json
import boto3
import os
import base64
import uuid
import logging

# Initialize AWS clients
s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')
es_client = boto3.client('opensearch')

def lambda_handler(event, context):
    #Get S3 Bucket and key from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    #Get image from S3
    image = get_image_from_S3(bucket, key)

    # Get metadata from the S3 object
    metadata = get_s3_metadata(bucket, key)


    # Detect labels in the image
    labels_response = detect_labels(image)

    if not labels_response:
    return {
        'statusCode': 200,
        'body': json.dumps('No labels detected')
    }   

    labels = metadata.get('customLabels', []) + [label['Name'] for label in labels_response]

    store_in_es(bucket, key, labels, metadata.get("createdTimestamp"))

    return {
        'statusCode': 200,
        'body': json.dumps('Labels stored in es')
    }

def get_image_from_s3(bucket, key):
    "Get image from S3 bucket"
    response = s3_client.get_object(Bucket=bucket, Key=key)
    image_content = response['Body'].read()
    return {
        'Bytes': image_content
    }

def get_s3_metadata(bucket, key):
    "Get metadata from S3 object"
    response = s3_client.head_object(Bucket=bucket, Key=key)
    metadata = response.get('Metadata', {})
    
    #Get timestamp
    timestamp = response.get('LastModified')
    timestamp = timestamp.isoformat()

    #Get labels
    custom_labels = metadata.get('x-amz-meta-customlabels', '')
    custom_labels = custom_labels.split(',') if custom_labels else []
    return {
        "customLabels": custom_labels,
        "createdTimestamp": created_timestamp
    }

def detect_labels(image):
    "Detect labels in the image using Amazon Rekognition"
    response = rekognition_client.detect_labels(
        Image=image
    )
    return response.get('Labels', [])

def store_in_es(bucket, key, labels, timestamp):
    "Store the image metadata and labels in ElasticSearch"
    # Create the JSON object
    document = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": timestamp,
        "labels": labels
    }
    
    # Index the document
    es_client.index(
        Index='photos',
        Document=document,
        Id=key 
    )