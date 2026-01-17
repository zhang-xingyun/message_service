# -*- coding: utf-8 -*-

import json
import web
from mr.gitlab_mr import MR

from utils.log_utils import log

urls = (
    '/push_message', 'GitLab',
    '/ph_message', 'PHMessage',
)
app = web.application(urls, globals())


class GitLab:
    def GET(self, name=None):
        return web.input()

    def POST(self):
        receive = web.data()
        log(receive.decode())
        message = json.loads(receive.decode())
        try:
            mr = MR()
            mr.parse_webhook(message)

        except Exception as err:
            log(receive.decode())
            log(err)
        return web.data()


class PHMessage(object):
    def GET(self, name=None):
        return web.input()

    def POST(self, name=''):
        data = json.loads(web.data().decode())
        try:
            phid = data['object']['phid']
            tr_ids = list()
            for i in data['transactions']:
                tr_ids.append(i['phid'])
            try:
                # users = main(phid, tr_ids)
                users = []
                log(web.data(), 'ph_user')
                log(json.dumps(users), 'ph_user')
            except Exception as err:
                log(web.data(), 'ph_webhook.log')
                log(err, 'ph_webhook.log')
        except Exception as err:
            log(web.data(), 'ph_webhook_data.log')
            log(err, 'ph_webhook_data.log')
        return 'Hello, ' + name + '!'


if __name__ == "__main__":
    app.run()
