# -*- coding: utf-8 -*-

import re

import gitlab
from gitlab.exceptions import GitlabGetError

from mr.feishu import FeiShu


class MR(object):

    def __init__(self):
        self.gl = gitlab.Gitlab.from_config('trigger', [
            '/data/gitlab_push/python-gitlab.cfg'])

    def parse_webhook(self, item: dict):
        kind = item['object_kind']
        if kind == 'note':
            push_data = self.parse_note(item)

        elif kind == 'merge_request':
            push_data = self.parse_merge(item)

        elif kind == 'issue':
            push_data = self.parse_issues(item)
        else:
            return
        if push_data is None:
            return
        fs = FeiShu()
        author = push_data['author']
        push_user = push_data['users']
        try:
            push_user.remove(author)
        except:
            pass

        fs.feishu_notify(push_user, push_data['message'])

    # 评论
    def parse_note(self, item: dict):
        push_detail = self.parse_push_user(item)
        push_user = push_detail['push_user']
        assignees = push_detail['assignees']
        project_id = item['project']['id']
        author = item['user']['name']
        url = item['object_attributes']['url']
        # issues 追加
        if item.get('issue'):
            info = item['issue']
            status = info['state']
            title = info['title']
            # description = info['description']
            description = item['object_attributes']['note']
            issues_id = item['issue']['iid']
            issues_users = self.get_issues_users(project_id, issues_id)
            push_user.extend(issues_users)
            push_message = f'**Action Type: issues** \n' \
                           f'**Comment By: {author}**\n' \
                           f'**Link: {url}** \n**Title: {title}**\n'
            if description and len(description.split('\n')) > 1:
                push_message += f'**Comment:** \n {description}'
            else:
                push_message += f'**Comment: {description}**'
            push_message += f'\n**Status: Add Comment**\n'
            return {
                'users': set(push_user),
                'message': push_message,
                'author': author,
            }

        # 代码评论
        elif item.get('commit'):
            # 提交时的标题
            commit_message = item['commit']['message']
            comment_user = item['user']['username']
            commit_id = item['commit']['id']
            project_id = item['project_id']
            commit_list = self.gl.projects.get(project_id).commits.get(
                commit_id).comments.list()
            user_list = []
            for msg in commit_list:
                user_list.append(msg.author['username'])
            # 谁提交的
            # commit_author = item['commit']['author']
            description = item['object_attributes']['description']
            push_message = f'**Action Type: Comment**\n' \
                           f'**Change By: {author}**\n**Link: {url}**\n' \
                           f'**Commit: {commit_message}**\n'
            if description and len(description.split('\n')) > 1:
                push_message += f'**Description:** \n' \
                                f' {comment_user}: {description}\n'
            else:
                push_message += f'**Description: {comment_user}: ' \
                                f'{description}**\n'
            if item['object_attributes'].get('position'):
                position_path = item['object_attributes']['position'][
                    'old_path']
                position_line = item['object_attributes']['position'][
                    'old_line']
                push_message += f'**Path: {position_path}**\n' \
                                f'**File Line: {position_line}**\n'
            push_message += '**Status: Add Comment**\n'
            return {
                'users': list(set(user_list)),
                'message': push_message,
                'author': author,
            }

        # merge 评论
        elif item.get('merge_request'):
            push_info = self.parse_common(item, 'merge_request')
            description = item['object_attributes']['note']

            mr_id = item['merge_request']['iid']
            get_mr_reviewer = self.get_mr_user(project_id, mr_id)
            push_user.extend(get_mr_reviewer.get('usernames', []))
            push_message = f'**Action Type: Merge Comment**  \n' \
                           f'**Author: {push_info["author"]}**  \n'
            if get_mr_reviewer.get('review_users'):
                review_users = ','.join(get_mr_reviewer.get('review_users'))
                push_message += f'**Reviewers: {review_users}**  \n'
                pass
            if get_mr_reviewer.get('assignee_users'):
                assignee_users = ','.join(
                    get_mr_reviewer.get('assignee_users'))
                push_message += f'**Assignee: {assignee_users}**  \n'
            push_message += f'**Link: {push_info["url"]}**  \n' \
                            f'**Title: {push_info["title"]}**  \n'
            if description and len(description.split('\n')) > 1:
                push_message += f'**Comment:** \n {description}\n' \
                                f'**Status: Add Comment**  \n'
            else:
                push_message += f'**Comment: {description}**\n' \
                                f'**Status: Add Comment**  \n'
            return {
                'users': list(set(push_user)),
                'message': push_message,
                'author': author,
            }
        pass

    def parse_merge(self, item: dict):
        author = item['user']['name']
        push_info = self.parse_common(item)
        info = item['object_attributes']
        source_branch = info['source_branch']
        target_branch = info['target_branch']
        project_id = item['project']['id']
        mr_id = item['object_attributes']['iid']
        get_mr_reviewer = self.get_mr_user(project_id, mr_id)
        push_info['push_user'].extend(get_mr_reviewer.get('usernames', []))
        push_message = f'**Action Type: Merge Requests**  \n' \
                       f'**Author: {push_info["author"]}**  \n'
        if get_mr_reviewer.get('review_users'):
            review_users = ','.join(get_mr_reviewer.get('review_users'))
            push_message += f'**Reviewers: {review_users}**  \n'
            pass
        if get_mr_reviewer.get('assignee_users'):
            assignee_users = ','.join(get_mr_reviewer.get('assignee_users'))
            push_message += f'**Assignee: {assignee_users}**  \n'
        push_message += f'**Link: {push_info["url"]}**  \n' \
                        f'**Title: {push_info["title"]}**  \n'
        description = push_info["description"]
        if description and len(description.split('\n')) > 1:
            push_message += f'**Description:** \n {description}\n'
        else:
            push_message += f'**Description: {description}**\n'
        push_message += f'**Branch From: {source_branch}**  \n**Branch To: ' \
                        f'{target_branch}**  \n' \
                        f'**Status: {push_info["action"]}**  \n'
        return {
            'users': set(push_info['push_user']),
            'message': push_message,
            'author': author
        }

    def parse_issues(self, item: dict):
        author = item['user']['name']
        push_info = self.parse_common(item)
        project_id = push_info['project_id']
        issues_id = item['object_attributes']['iid']
        issues_users = self.get_issues_users(project_id, issues_id)
        push_info['push_user'].extend(issues_users)
        status = push_info['action']
        push_message = f'**Action Type: issues**  \n' \
                       f'**Create By: {push_info["author"]}**  \n' \
                       f'**Link {push_info["url"]}' \
                       f'**  \n**Title: {push_info["title"]}**  \n'
        description = push_info["description"]
        if description and len(description.split('\n')) > 1:
            push_message += f'**Description:**\n {description}\n' \
                            f'**Status: {status}**\n'
        else:
            push_message += f'**Description: {description}**\n' \
                            f'**Status: {status}**\n'
        return {
            'users': set(push_info['push_user']),
            'message': push_message,
            'author': author
        }

    def parse_common(self, item: dict, key='object_attributes'):
        url = item['object_attributes']['url']
        push_detail = self.parse_push_user(item)
        push_user = push_detail['push_user']
        assignees = push_detail['assignees']
        info = item[key]
        author = item['user']['name']
        status = info['state']
        title = info['title']
        description = info['description']
        action = info.get('action')
        project_id = item['project']['id']

        return {
            'push_user': push_user,
            'status': status,
            'title': title,
            'description': description,
            'action': action if action else status,
            'author': author,
            'url': url,
            'assignees': assignees,
            'project_id': project_id
        }

    # 推送的人
    def parse_push_user(self, item: dict):
        push_user = []
        author = item['user']['name']
        author_email = item['user']['email']
        push_user.append(author)
        merge_assignees = item.get('assignees', [])
        assignees = []
        for assignee_user in merge_assignees:
            push_user.append(assignee_user['name'])
            assignees.append(assignee_user['name'])
        push_user = list(set(push_user))
        assignees = ','.join(assignees)
        return {
            'push_user': push_user,
            'assignees': assignees
        }

    # merge的 用户
    def get_mr_user(self, proj_id, mr_id):
        try:
            project = self.gl.projects.get(
                proj_id, retry_transient_errors=True)
            mr_ins = project.mergerequests.get(mr_id)
            reviewers = mr_ins.reviewers
            usernames = [mr_ins.author['username']]
            review_users = []
            for user in reviewers:
                usernames.append(user['username'])
                review_users.append(user['username'])
            assignees = mr_ins.assignees
            assignee_users = []
            for user in assignees:
                assignee_users.append(user['username'])
                usernames.append(user['username'])
            for note in mr_ins.participants():
                usernames.append(note['username'])
            return {
                'usernames': usernames,
                'review_users': review_users,
                'assignee_users': assignee_users,
            }
        # 不存在，被删除
        except GitlabGetError:
            return {}

    # issues 所有回复的用户
    def get_issues_users(self, proj_id, issues_id):
        try:
            project = self.gl.projects.get(
                proj_id, retry_transient_errors=True)
            issues_ins = project.issues.get(issues_id)
            notes = issues_ins.notes.list()
            usernames = [issues_ins.author['username']]
            for note in notes:
                usernames.append(note.author['name'])
                usernames.extend(re.findall(r'@(.*?)\s', note.body))
            if 'all' in usernames:
                usernames = self.get_project_all_users(proj_id)
            return usernames
        except GitlabGetError:
            return []

    # 项目所有人
    def get_project_all_users(self, proj_id):
        project = self.gl.projects.get(
            proj_id, retry_transient_errors=True)

        # users = lambda x: [i.username for i in x]
        # return users(project.members_all.list())
        users = list()
        for user in project.members_all.list():
            users.append(user.username)
        return users
