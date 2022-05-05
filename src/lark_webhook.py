# -*- coding: UTF-8 -*-
# import os, sys; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import datetime
import requests
import json
from flask import Flask, Response, request, abort
from config.settings import APP_ID, APP_NAME, URLS, PORT, NICK_NAME
from src.public_func import bot_msg_talking, empty_dialogue
from open_api.bot_message import reply_meg
from utils.decrypt_key import parse_event
from utils.nt_hash import nt


def start(port: int):
    app = Flask(__name__)

    @app.route(URLS['events'], methods=['POST'])
    def callback_event():
        if (request.method == 'POST'):
            # Received event ciphertext
            encrypt = request.json.get('encrypt')

            # Ciphertext parsing
            data = parse_event(encrypt)

            # Verify challenge (first conn)
            challenge = data.get('challenge')
            if challenge:
                data = {'challenge': challenge}
                return Response(json.dumps(data), status=200, content_type='application/json')

            # Get header info    
            header_data = data.get('header')

            # Verify app_id
            app_id = header_data.get('app_id')
            if app_id != APP_ID:
                # HTTP 400 Bad Request.
                abort(400)
    
            # Verify event_type
            event_type = header_data.get('event_type')
            if event_type == "im.message.receive_v1":
                # Verify event_data
                event_data = data.get('event')

                # get message content
                content = json.loads(event_data.get('message').get('content'))
                meg_id = event_data.get('message').get('message_id')

                # hook chat bot message type
                chat_type = event_data.get('message').get('chat_type')
                data = {}
                # hook private chat bot message
                if chat_type == "p2p":
                    data = bot_msg_talking(content, 1)

                # messages in the hook group
                elif chat_type == "group":
                    mention_bot = event_data.get('message').get('mentions')
                    # @bot msg
                    if mention_bot:
                        for i in mention_bot:
                            if i['name'] == APP_NAME:
                                if content.get('text').strip() != i['key']:
                                    data = bot_msg_talking(content, 1)
                                else:
                                    data = {'text': empty_dialogue()}
                    # no @bot msg
                    else:
                        data = bot_msg_talking(content, 0)

                # send meg
                reply_meg(meg_id, msg_type="text", content=data)

                return Response('"{}"', status=200, content_type='application/json')
            else:
                # HTTP 403 Forbidden.
                abort(403)
        else:
            # HTTP 405 Method Not Allowed.
            abort(405)


    @app.route(URLS['larkbot'], methods=['POST'])
    def callback_bot():
        if (request.method != 'POST'):
            abort(405)
        else:
            challenge = request.json.get('challenge')
            if not challenge:
                abort(400)
            else:
                data = {'challenge': challenge}
                return Response(json.dumps(data), status=200, content_type='application/json')


    @app.route(URLS['yuque'], methods=['POST'])
    def callback_hook():
        if (request.method != 'POST'):
            abort(405)
        else:
            yq_data = request.json.get('data')
            webhook_type = yq_data.get('webhook_subject_type')
            # 当语雀用户发布或更新一篇文章
            if webhook_type in ("publish", "update"):
                # format yuque time
                yq_time_utc = yq_data.get('content_updated_at')
                yq_datetime = datetime.datetime.strptime(yq_time_utc, '%Y-%m-%dT%H:%M:%S.000Z')
                yq_time_local = (yq_datetime + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

                # yuque basic info
                yq_title = yq_data.get('title')
                yq_wiki = yq_data.get('user').get('name')
                yq_url = "https://field.yuque.com/" + yq_data.get('path')

                # format yuque action
                if webhook_type == "publish":
                    yq_type = "初次发布"
                elif webhook_type == "update":
                    yq_type = "更新"

                # data processing
                data_filter = {
                    'title': yq_title,
                    'belong_wiki': yq_wiki,
                    'address_url': yq_url,
                    'update_time': yq_time_local,
                    'action_type': yq_type
                }
                print(f"这是一条来自{NICK_NAME}的温馨提醒呦～\n北京时间 [{data_filter['update_time']}] 收录于 \'{data_filter['belong_wiki']}\' 中的《{data_filter['title']}》已完成{data_filter['action_type']}。")

            # 当语雀用户发表/更新/回复一条评论
            elif webhook_type in ("comment_create", "comment_update", "comment_reply_create"):
                # format yuque time
                yq_time_utc = yq_data.get('commentable').get('content_updated_at')
                yq_datetime = datetime.datetime.strptime(yq_time_utc, '%Y-%m-%dT%H:%M:%S.000Z')
                yq_time_local = (yq_datetime + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

                # yuque basic info
                yq_user = yq_data.get('user').get('name')
                yq_title = yq_data.get('commentable').get('title')
                yq_url = "https://field.yuque.com/" + yq_data.get('path')

                # format yuque action
                if webhook_type == "comment_create":
                    yq_type = "新增评论+1"
                elif webhook_type == "comment_update":
                    yq_type = "更新评论"
                elif webhook_type == "comment_reply_create":
                    yq_type = "回复评论"

                # data processing
                data_filter = {
                    'title': yq_title,
                    'user': yq_user,
                    'address_url': yq_url,
                    'update_time': yq_time_local,
                    'action_type': yq_type
                }
                print(f"这是一条来自{NICK_NAME}的温馨提醒呦～\n北京时间 [{data_filter['update_time']}]  用户 \'{data_filter['user']}\' 在《{data_filter['title']}》下方进行了留言（{data_filter['action_type']}）。")
            else:
                # print(request.json)
                abort(403)
            
            print(data_filter)
            return Response(json.dumps({}), status=200, content_type='application/json')


    app.run(host='0.0.0.0', debug=True, port=port)


if __name__ == '__main__':
    start(port=PORT)

