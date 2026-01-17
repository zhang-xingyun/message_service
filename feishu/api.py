import os
import sys
import json
from flask import Flask, request
from concurrent.futures import ThreadPoolExecutor
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils.log_utils import log
from handle_ph import main

APP_ID = "xxx"
APP_SECRET = "xxx"

executor = ThreadPoolExecutor(4)
app = Flask(__name__)


@app.route('/ph_message', methods=['POST'])
def index():
    data = request.json
    try:
        phid = data['object']['phid']
        tr_ids = list()
        for i in data['transactions']:
            tr_ids.append(i['phid'])
        try:
            # users = main(phid, tr_ids)
            executor.submit(main, phid, tr_ids)
        except Exception as err:
            log(json.dumps(data), 'ph_webhook.log')
            log(err, 'ph_webhook.log')
    except Exception as err:
        log(json.dumps(data), 'ph_webhook_data.log')
        log(err, 'ph_webhook_data.log')
    return 'hello world !'


@app.route('/feishu', methods=['POST'])
def feishu():
    data = request.json
    users = data.get('user', '')
    if isinstance(users, str):
        users = users.split(',')
    if len(users) == 0:
        return
    content = data.get('content', '')
    access_token = gettoken_feishu()
    msg_type = data.get('msg_type', '')
    for user in users:
        if '@test.com' not in user:
            user = f"{user}@test.com"
        try:
            feishu_send(access_token, user, content, msg_type)
        except Exception as e:
            print(e)
            log(e, 'feishu')
    return 'ok'


def feishu_send(access_token, email, content, msg_type):
    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    headers = {
        "Authorization": ' '.join(['Bearer', access_token]),
        "Content-Type": "application/json"
    }
    data = dict()
    data["email"] = email
    if msg_type == "text":
        data["msg_type"] = "text"
        data["content"] = content
    elif msg_type == "mark_down":
        data["msg_type"] = "interactive"
        data["card"] = content
    else:
        return
    req = requests.post(url=url, json=data,
                        headers=headers,
                        timeout=60)
    req_json = req.json()


def gettoken_feishu():
    url = "https://open.feishu.cn/open-apis/auth/v3/" \
          "tenant_access_token/internal/"
    headers = {
        "Content-Type": "application/json"
    }
    req_body = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    req = requests.post(url=url, json=req_body,
                        headers=headers,
                        timeout=60)
    req_json = req.json()
    return req_json['tenant_access_token']


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
