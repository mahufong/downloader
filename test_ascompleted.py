"""
 * @2022-01-06 19:56:00
 * @Author       : mahf
 * @LastEditTime : 2022-01-07 13:41:30
 * @FilePath     : /downloader/test_ascompleted.py
 * @Copyright 2022 mahf, All Rights Reserved.
"""
import asyncio
import time


async def task_func(n):
    print(n)
    await asyncio.sleep(n)
    return f"task{n}"


async def main():
    # 同样需要传递一个列表, 里面同样可以指定超时时间
    completed = asyncio.as_completed([task_func(2), task_func(1), task_func(3), task_func(4)])
    #遍历每一个task，进行await，哪个先完成，就先返回
    for task in completed:
        print(task)
        res = await task
        #print(res)


start = time.perf_counter()
asyncio.run(main())
print(f"总用时：{time.perf_counter() - start}")