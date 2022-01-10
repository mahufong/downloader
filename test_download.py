"""
 * @2022-01-06 14:36:55
 * @Author       : mahf
 * @LastEditTime : 2022-01-07 14:40:31
 * @FilePath     : /downloader/test_download.py
 * @Copyright 2022 mahf, All Rights Reserved.
"""
import asyncio
from json import load
import os
import time
import urllib.parse
from typing import List
import threading

import aiohttp
import tqdm
from yarl import URL

API_URL = 'http://xiaoapi.cn/api/jingxuanshipin.php?type=热舞'
DEST_DIR = './downloads/'  # 保存目录
TEST_LIST = ['http://cdn.video.picasso.dandanjiang.tv/5ae0378d0422087736e9526b.mp4?sign=85337b344d2e36985544ef53525dedb8&t=61d6f9ce', ]
# 'http://cdn.video.picasso.dandanjiang.tv/59abbbd731f6133a6f1b0893.mp4?sign=08a8be78c521f2bceb25bae4c33c56ee&t=61d6c7b9']
# 获取链接,下载文件


class downloader(object):
    def __init__(self) -> None:

        def start_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        super().__init__()
        self.new_loop = asyncio.new_event_loop()  # 在当前线程下创建时间循环，（未启用），在start_loop里面启动它
        self.thread = threading.Thread(target=start_loop, args=(
            self.new_loop,))  # 通过当前线程开启新的线程去启动事件循环
        self.thread.start()
        # 创建目录
        os.makedirs(DEST_DIR, exist_ok=True)
        self.sem = asyncio.Semaphore(3)

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

    async def fetch(self, session: aiohttp.ClientSession, url: str, path: str, flag: str):
        print(flag, ' 开始下载')
        async with session.get(url) as resp:
            #print (resp.headers)
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

    async def begin_download(self, sem, session: aiohttp.ClientSession, url: str, path: str, flag: str):
        # 控制协程并发数量
        async with sem:
            return await self.fetch(session, url, path, flag)

    async def download(self, sem: asyncio.Semaphore, url_list: List):
        tasks = []
        start = time.time()
        async with aiohttp.ClientSession() as session:
            for url in url_list:
                # 创建路径以及url
                flag = os.path.basename(urllib.parse.urlsplit(url).path)
                path = os.path.join(DEST_DIR, flag)
                # 构造一个协程列表
                tasks.append(asyncio.ensure_future(
                    self.begin_download(sem, session, url, path, flag)))
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

    def start_download(self, url_list: List):
        result = asyncio.run_coroutine_threadsafe(
            self.download(self.sem, url_list), self.new_loop)
        print(result.result())
        return result

    def add_job(self):
        result = asyncio.run_coroutine_threadsafe(
            self.get_url(API_URL), self.new_loop)
        print(result.result())
        return result

    def stop(self):
        self.new_loop.stop()
        self.new_loop.close()


if __name__ == "__main__":
    #     url = ['http://cdn.video.picasso.dandanjiang.tv/5c0e711d0422084e3ce71d1c.mp4?newver=0.92090061967&sign=800fb5a9d0a755c6de890e4dd2419f22&t=61d70266',

    # 'http://cdn.video.picasso.dandanjiang.tv/5d28225731f6136b076f21c2.mp4?sign=8af047831a514f66e0d1291df45582a7&t=61d70267',]
    url = []
    loader = downloader()
    # ll = loader.start_download(TEST_LIST)
    # loader.stop()
    for _ in range(5):
        tmp = loader.add_job()
        url.append(tmp.result())

    print(url)

    loader.start_download(url)
