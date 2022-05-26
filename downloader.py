"""
 * @2022-01-07 17:34:46
 * @Author       : mahf
 * @LastEditTime : 2022-05-26 12:55:55
 * @FilePath     : /downloader/downloader.py
 * @Copyright 2022 mahf, All Rights Reserved.
"""
import asyncio
from json import load
import os
from queue import Queue
import time
import urllib.parse
from asyncio.futures import Future
from typing import List

import aiohttp
import tqdm

from asyncPool import AsyncPool

API_URL = 'http://xiaoapi.cn/api/jingxuanshipin.php?type=热舞'
DEST_DIR = './downloads/'


class downloader(object):

    def __init__(self) -> None:
        super().__init__()

        os.makedirs(DEST_DIR, exist_ok=True)
        self.pool = AsyncPool(5)

        #结果队列
        self.result = self.pool.result_queue

    def shutdown(self):
        self.pool.release()
        self.pool.wait()

    def url_parse(self, data: str):
        data.strip()
        index = data.rfind("http")
        return data[index:]
    
    async def get_url(self, url: str):
        print('开始获取资源地址')
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.text()
                ret = self.url_parse(data)
                return ret

    async def fetch(self, url: str, path: str, flag: str):
        print(flag, ' 开始下载')
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                # print (resp.headers)
                # 不下载大于100M的文件
                length = round(
                    int(resp.headers['Content-Length']) / 1024 / 1024, 2)
                print(f'{flag} size : {length} M')
                if length > 100:
                    return flag
                with open(path, 'wb') as fd:
                    while 1:
                        chunk = await resp.content.read(1024)  # 每次获取1024字节
                        if not chunk:
                            break
                        fd.write(chunk)
            return flag

    async def download(self, url_list: List):
        """参考 弃用"""
        tasks = []
        start = time.time()
        async with aiohttp.ClientSession() as session:
            for url in url_list:
                # 创建路径以及url
                flag = os.path.basename(urllib.parse.urlsplit(url).path)
                path = os.path.join(DEST_DIR, flag)
                # 构造一个协程列表
                tasks.append(asyncio.ensure_future(
                    self.fetch(session, url, path, flag)))
            # 等待返回结果
            tasks_iter = asyncio.as_completed(tasks)
            # 创建一个进度条
            fk_task_iter = tqdm.tqdm(tasks_iter, total=len(url_list))
            for coroutine in fk_task_iter:
                # 获取结果
                res = await coroutine
                print(res, '下载完成')
        end = time.time()
        return "全部下载完成\n用时{}".format(end - start)

    def my_callback(self, fn: Future):
        print("完成 : ", fn.result())

    def add_download_job(self, fn: Future):
        ret = fn.result()
        url = ret['result']
        creater = ret['creater']
        print("url : ", url)
        flag = os.path.basename(urllib.parse.urlsplit(url).path)
        path = os.path.join(DEST_DIR, flag)
        self.pool.submit(self.fetch(url, path, flag), self.my_callback,creater)

    def download_once(self,creater):
        self.pool.submit(self.get_url(API_URL), self.add_download_job,creater,False)


if __name__ == "__main__":
    loader = downloader()
    for i in range(2):
        loader.download_once(f"sdf : {i}")
    loader.shutdown()
    print(loader.result.qsize())

