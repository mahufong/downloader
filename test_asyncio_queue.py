"""
 * @2022-01-11 10:53:25
 * @Author       : mahf
 * @LastEditTime : 2022-01-11 11:07:36
 * @FilePath     : /downloader/test_asyncio_queue.py
 * @Copyright 2022 mahf, All Rights Reserved.
"""
import asyncio
import time


async def consumer(q: asyncio.Queue, n):
    print(f"消费者{n}号 开始")
    async for item in q:
        await gen.sleep(2)
        if item is None:
            q.task_done()
            break
        print(f"消费者{n}号: 消费元素{item}")
        q.task_done()
 


async def producer(q: asyncio.Queue, consumer_num):
    print(f"生产者 开始")
    for i in range(1, 2):
        #await q.put(i)
        print(f"生产者: 生产元素{i}, 并放在了队列里")
    # 为了让消费者停下来, 我就把None添加进去吧
    # 开启几个消费者, 就添加几个None
    for i in range(consumer_num):
        #await q.put(None)
        print("1")

    # 等待所有消费者执行完毕
    # 只要unfinished_tasks不为0，那么q.join就会卡住，直到消费者全部消费完为止
    await q.join()
    print("生产者生产的东西全被消费者消费了")


async def main(consumer_num):
    q = asyncio.Queue()
    consumers = [consumer(q, i) for i in range(consumer_num)]
    await asyncio.wait(consumers + [producer(q, consumer_num)])


start = time.perf_counter()
asyncio.run(main(3))
print(f"总用时：{time.perf_counter() - start}")

