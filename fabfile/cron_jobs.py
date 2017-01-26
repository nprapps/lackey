#!/usr/bin/env python

"""
Cron jobs
"""

import app_config
import json
import logging
import requests

from datetime import datetime
from fabric.api import local, require, task
from slugify import slugify

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

secrets = app_config.get_secrets()
print(secrets)
WEBHOOK = secrets.get('WEBHOOK')
API_KEY = secrets.get('PROPUBLICA_API_KEY')
BASE_URL = 'https://api.propublica.org/congress/v1/115'
CHAMBERS = ['senate', 'house']
TYPES = ['introduced', 'updated', 'passed']

@task
def get_new_bills():
    for chamber in CHAMBERS:
        for bill_type in TYPES:
            documents = get_documents(chamber, bill_type)
            post_message(documents)

def post_message(documents):
    r = requests.post(WEBHOOK, data=json.dumps(documents))
    print(r.text)

def get_documents(chamber, bill_type):
    bill_date = '2017-01-23'

    bill_attachments = []
    headers = {
        'X-API-Key': API_KEY
    }

    bills = requests.get('{0}/{1}/bills/{2}.json'.format(BASE_URL, chamber, bill_type), headers=headers).json()
    print(bills)
    for bill in bills['results'][0]['bills']:
        if (bill_type == 'introduced' and bill['introduced_date'] == bill_date) or ((bill_type == 'updated' or bill_type == 'passed') and bill['latest_major_action_date'] == bill_date):
            bill_attachments.append(build_attachment(bill))

    return {
        'text': 'The {0} has {1} {2} bills today.'.format(chamber, bill_type, len(bill_attachments)),
        'attachments': bill_attachments
    }

def build_attachment(bill):
    headers = {
        'X-API-Key': API_KEY
    }
    bill_data = requests.get(bill['bill_uri'], headers=headers).json()['results'][0]

    return {
        'fallback': bill_data['title'],
        # 'color': COLORS_DICT[document['type']],
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

def construct_congressperson_url(sponsor, uri):
    base = 'https://projects.propublica.org/represent/members'
    sponsor_slug = slugify(sponsor)
    id = uri.split('/')[-1].split('.')[0]

    return '{0}/{1}-{2}'.format(base, id, sponsor_slug)