#!/usr/bin/env python

"""
Cron jobs
"""
import app_config
import json
import logging
import os
import requests

from datetime import datetime
from fabric.api import local, require, task
from slugify import slugify

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

secrets = app_config.get_secrets()
WEBHOOK = secrets.get('WEBHOOK')
API_KEY = secrets.get('PROPUBLICA_API_KEY')
BASE_URL = 'https://api.propublica.org/congress/v1/115'
CHAMBERS = ['senate', 'house']
DATA_TYPES = ['introduced', 'updated', 'passed']

@task
def get_new_bills():
    for chamber in CHAMBERS:
        for data_type in DATA_TYPES:
            documents = get_documents(chamber, data_type)
            if len(documents['attachments']) > 0:
                post_message(documents)

def post_message(documents):
    r = requests.post(WEBHOOK, data=json.dumps(documents))
    print(r.text)

def get_documents(chamber, data_type):
    bill_attachments = []
    headers = {
        'X-API-Key': API_KEY
    }

    stop_bill = get_previous_first_bill(chamber, data_type)

    bills = requests.get('{0}/{1}/bills/{2}.json'.format(
        BASE_URL, 
        chamber, 
        data_type
    ), headers=headers).json()

    save_first_result(bills['results'][0]['bills'][0], chamber, data_type)

    for bill in bills['results'][0]['bills']:
        if stop_bill and stop_bill == bill['title']:
            break    
        
        bill_attachments.append(build_attachment(bill))

    return {
        'text': 'The {0}\'s {1} new {2} bills.'.format(
            bills['results'][0]['chamber'], 
            bills['results'][0]['num_results'], 
            data_type
        ),
        'attachments': bill_attachments
    }

def build_attachment(bill):
    headers = {
        'X-API-Key': API_KEY
    }
    bill_data = requests.get(bill['bill_uri'], headers=headers).json()['results'][0]

    return {
        'fallback': bill_data['title'],
        'author_name': bill_data['sponsor'],
        'author_link': construct_congressperson_url(bill_data['sponsor'], bill_data['sponsor_uri']),
        'title': bill_data['title'],
        'title_link': bill_data['gpo_pdf_uri'],
        'fields': [
            {
                'title': 'Latest Major Action',
                'value': bill_data['latest_major_action']
            }
        ],
    }

def get_previous_first_bill(chamber, data_type):
    if os.path.exists('data/{0}-{1}.json'.format(chamber, data_type)):
        with open('data/{0}-{1}.json'.format(chamber, data_type)) as f:
            bill = json.load(f)
            return bill['title']


def save_first_result(bill, chamber, data_type):
    with open('data/{0}-{1}.json'.format(chamber, data_type), 'w') as f:
        json.dump(bill, f)

def construct_congressperson_url(sponsor, uri):
    base = 'https://projects.propublica.org/represent/members'
    sponsor_slug = slugify(sponsor)
    id = uri.split('/')[-1].split('.')[0]

    return '{0}/{1}-{2}'.format(base, id, sponsor_slug)