# -*- coding: utf-8 -*-
import json
import threading
import time
from functools import partial
from queue import Queue
from threading import Thread
import os 

import websocket

import downloader
from downloader import DEST_DIR

#SERVER = 'ws://192.168.9.113:5555'
SERVER = 'ws://192.168.10.20:5555'

HEART_BEAT = 5005
RECV_TXT_MSG = 1
RECV_PIC_MSG = 3
USER_LIST = 5000
GET_USER_LIST_SUCCSESS = 5001
GET_USER_LIST_FAIL = 5002
TXT_MSG = 555
PIC_MSG = 500
AT_MSG = 550
CHATROOM_MEMBER = 5010
CHATROOM_MEMBER_NICK = 5020
PERSONAL_INFO = 6500
DEBUG_SWITCH = 6000
PERSONAL_DETAIL = 6550
DESTROY_ALL = 9999
ATTATCH_FILE = 5003


# def getid():
#     id = int(time.time() * 1000)
#     return id


def getid():
    id = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
    return id


def get_chat_nick_p(roomid):
    qs = {
        'id': getid(),
        'type': CHATROOM_MEMBER_NICK,
        'content': roomid,
        'wxid': 'ROOT',
    }
    s = json.dumps(qs)
    return s


def debug_switch():
    qs = {
        'id': getid(),
        'type': DEBUG_SWITCH,
        'content': 'off',
        'wxid': 'ROOT',
    }
    s = json.dumps(qs)
    return s


def handle_nick(j):
    data = j.content
    i = 0
    for d in data:
        print(d.nickname)
        i += 1


def hanle_memberlist(j):
    data = j.content
    i = 0
    for d in data:
        print(d.roomid)
        i += 1


def get_chatroom_memberlist():
    qs = {
        'id': getid(),
        'type': CHATROOM_MEMBER,
        'wxid': 'null',
        'content': 'op:list member ',
    }
    s = json.dumps(qs)
    return s


def send_at_meg():
    qs = {
        'id': getid(),
        'type': AT_MSG,
        'roomid': 'Your roomid',  # not null
        'content': '我能吞下玻璃而不伤身体',
        'nickname': '[微笑]Python',
    }
    s = json.dumps(qs)
    return s


def destroy_all():
    qs = {
        'id': getid(),
        'type': DESTROY_ALL,
        'content': 'none',
        'wxid': 'node',
    }
    s = json.dumps(qs)
    return s

def send_attatch(wxid, con,roomid=''):
    qs = {
        'id': getid(),
        'type': ATTATCH_FILE,
        'content': con,
        'wxid': wxid,
        'roomid': roomid,
        'nickname': '',
        'ext': '',
    }
    s = json.dumps(qs)
    return s

def send_pic_msg(wxid, con,roomid=''):
    qs = {
        'id': getid(),
        'type': PIC_MSG,
        'content': con,
        'wxid': wxid,
        'roomid': roomid,
        'nickname': '',
        'ext': '',
    }
    s = json.dumps(qs)
    return s


def get_personal_detail():
    qs = {
        'id': getid(),
        'type': PERSONAL_DETAIL,
        'content': 'op:personal detail',
        'wxid': '获取的wxid',
    }
    s = json.dumps(qs)
    return s


def get_personal_info():
    qs = {
        'id': getid(),
        'type': PERSONAL_INFO,
        'content': 'op:personal info',
        'wxid': 'ROOT',
    }
    s = json.dumps(qs)
    return s


def send_txt_msg(wxid):
    '''
    发送消息给好友
    '''
    qs = {
        'id': getid(),
        'type': TXT_MSG,
        'content': 'test string',  # 文本消息内容
        'wxid': wxid,   # wxid,
        'roomid': '',
        'nickname': '',
        'ext': '',
    }
    s = json.dumps(qs)
    return s


def send_wxuser_list():
    '''
    获取微信通讯录用户名字和wxid
    '''
    qs = {
        'id': getid(),
        'type': USER_LIST,
        'content': 'user list',
        'wxid': 'null',
    }
    s = json.dumps(qs)
    return s


def handle_wxuser_list(j):
    j_ary = j['content']
    i = 0
    # 微信群
    for item in j_ary:
        i += 1
        id = item['wxid']
        m = id.find('@')
        if m != -1:
            print(i, id, item['name'])
    # 微信其他好友，公众号等
    for item in j_ary:
        i += 1
        id = item['wxid']
        m = id.find('@')
        if m == -1:
            print(i, id, item['name'])


def handle_recv_msg(j):
    print(j)
    wxid = j['wxid']
    print('wxid is : ', wxid)
    if j['content'] == '扭一扭':
        loader.download_once(wxid)
    return wxid
    # return send_pic_msg(wxid)
    # return send_txt_msg(wxid)


def heartbeat(j):
    #print(j['content'])
    pass


def on_open(ws, result: Queue):
    def run(*arg):
        ws.send(send_wxuser_list())     # 获取微信通讯录好友列表
        while True:
            task_rsp = result.get()
            print("get one respone : ",task_rsp)
            
            path = os.path.abspath(os.path.join(DEST_DIR,task_rsp['result']))
            sdata = send_attatch("21245374923@chatroom", path)
            ws.send(sdata)
            result.task_done()  
    Thread(target=run).start()

    # ws.send(send_txt_msg())     # 向你的好友发送微信文本消息


def on_message(ws,message):
    # print(ws)
    j = json.loads(message)
    # print(j)
    resp_type = j['type']
    # switch结构
    action = {
        CHATROOM_MEMBER_NICK: handle_nick,
        PERSONAL_DETAIL: print,
        AT_MSG: print,
        DEBUG_SWITCH: print,
        PERSONAL_INFO: print,
        TXT_MSG: print,
        PIC_MSG: print,
        CHATROOM_MEMBER: hanle_memberlist,
        RECV_PIC_MSG: handle_recv_msg,
        RECV_TXT_MSG: handle_recv_msg,
        HEART_BEAT: heartbeat,
        USER_LIST: handle_wxuser_list,
        GET_USER_LIST_SUCCSESS: handle_wxuser_list,
        GET_USER_LIST_FAIL: handle_wxuser_list,
    }
    ret = action.get(resp_type, print)(j)
    return ret


def on_error(ws, error):
    print(ws)
    print(error)


def on_close(ws):
    print(ws)
    print("closed")


# async def main(websocket):
#     # async with websockets.connect(SERVER) as websocket:
#     while True:
#         rdata = await websocket.recv()
#         wxid = on_message(rdata)
#         print("main wxid", wxid)
#         #await deal_result(wxid, websocket)


# async def deal_result(websocket):
#     while True:
#         if not loader.result.empty():
#             ret = loader.result.get()
#             wxid = ret['creater']
#             print("deal ", wxid)
#             file_url = DEST_DIR + ret['result']
#             rdata = send_pic_msg(wxid, file_url)
#             print("send : ", rdata)
#             await websocket.send(rdata)
#             loader.result.task_done()
#         asyncio.sleep(1)


if __name__ == "__main__":

    loader = downloader.downloader()

    websocket.enableTrace(True)
    on_open = partial(on_open,result = loader.result)
    ws = websocket.WebSocketApp(SERVER,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
