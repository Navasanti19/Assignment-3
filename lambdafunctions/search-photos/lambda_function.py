import json
import requests
from requests_aws4auth import AWS4Auth
import boto3
import os

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                   region, service, session_token=credentials.token)

ES_HOST = 'https://vpc-photos-aizmp46fou5sw4iypyncrsfmse.us-east-1.es.amazonaws.com'
INDEX = 'photos'

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))

    # Detectar si viene de Lex o API Gateway
    if 'inputTranscript' in event:
        # Lex
        query = event['inputTranscript']
        response_format = 'lex'
    elif "queryStringParameters" in event and event["queryStringParameters"]:
        # API Gateway
        query = event["queryStringParameters"].get("q", "")
        response_format = 'api'
    else:
        # Fallback si viene vacío
        query = ""
        response_format = 'api'

    keywords = query.lower().split()

    search_query = {
        "query": {
            "bool": {
                "should": [{"match": {"labels": k}} for k in keywords]
            }
        }
    }

    url = f"{ES_HOST}/{INDEX}/_search"
    headers = {"Content-Type": "application/json"}
    response = requests.get(url, auth=awsauth, headers=headers, json=search_query)
    results = response.json()

    hits = results.get('hits', {}).get('hits', [])
    photos = [
        f"https://{hit['_source']['bucket']}.s3.amazonaws.com/{hit['_source']['objectKey']}"
        for hit in hits
    ]

    # Retornar según el tipo de invocador
    if response_format == 'lex':
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": "SearchIntent",
                    "state": "Fulfilled"
                }
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "\n".join(photos) if photos else "No photos found."
                }
            ]
        }
    else:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(photos if photos else ["No photos found."])
        }
