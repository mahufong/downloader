"""
asyncio 协程介绍:
    - 动态添加任务：
        - 方案是创建一个线程，使事件循环在线程内永久运行
        - 设置守护进程，随着主进程一起关闭
    - 自动停止任务
    - 阻塞任务完成
    - 协程池
        - asyncio.Semaphore() 进行控制
"""

import asyncio
import logging
import sys
import threading
import time
from queue import Queue
from threading import Thread
from functools import partial

import aiohttp


class MySnow(object):
    """雪花算法生产唯一id"""

    def __init__(self, datacenter_id, worker_id):
        # 初始毫秒级时间戳（2022-01-01）
        self.initial_time_stamp = int(time.mktime(time.strptime(
            '2022-01-01 00:00:00', "%Y-%m-%d %H:%M:%S")) * 1000)
        # 机器 ID 所占的位数
        self.worker_id_bits = 5
        # 数据表示 ID 所占的位数
        self.datacenter_id_bits = 5
        # 支持的最大机器 ID，结果是 31（这个位移算法可以很快的计算出几位二进制数所能表示的最大十进制数）
        # 2**5-1 0b11111
        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        # 支持最大标识 ID，结果是 31
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)
        # 序列号 ID所占的位数
        self.sequence_bits = 12
        # 机器 ID 偏移量（12）
        self.workerid_offset = self.sequence_bits
        # 数据中心 ID 偏移量（12 + 5）
        self.datacenterid_offset = self.sequence_bits + self.datacenter_id_bits
        # 时间戳偏移量（12 + 5 + 5）
        self.timestamp_offset = self.sequence_bits + \
            self.datacenter_id_bits + self.worker_id_bits
        # 生成序列的掩码，这里为 4095（0b111111111111 = 0xfff = 4095）
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        # 初始化日志
        self.logger = logging.getLogger('snowflake')

        # 数据中心 ID（0 ~ 31）
        if datacenter_id > self.max_datacenter_id or datacenter_id < 0:
            err_msg = 'datacenter_id 不能大于 %d 或小于 0' % self.max_worker_id
            self.logger.error(err_msg)
            sys.exit()
        self.datacenter_id = datacenter_id
        # 工作节点 ID（0 ~ 31）
        if worker_id > self.max_worker_id or worker_id < 0:
            err_msg = 'worker_id 不能大于 %d 或小于 0' % self.max_worker_id
            self.logger.error(err_msg)
            sys.exit()
        self.worker_id = worker_id
        # 毫秒内序列（0 ~ 4095）
        self.sequence = 0
        # 上次生成 ID 的时间戳
        self.last_timestamp = -1

    def _gen_timestamp(self):
        """
        生成整数毫秒级时间戳
        :return: 整数毫秒级时间戳
        """
        return int(time.time() * 1000)

    def next_id(self):
        """
        获得下一个ID (用同步锁保证线程安全)
        :return: snowflake_id
        """
        timestamp = self._gen_timestamp()
        # 如果当前时间小于上一次 ID 生成的时间戳，说明系统时钟回退过这个时候应当抛出异常
        if timestamp < self.last_timestamp:
            self.logger.error('clock is moving backwards. Rejecting requests until {}'.format(
                self.last_timestamp))
        # 如果是同一时间生成的，则进行毫秒内序列
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            # sequence 等于 0 说明毫秒内序列已经增长到最大值
            if self.sequence == 0:
                # 阻塞到下一个毫秒,获得新的时间戳
                timestamp = self._til_next_millis(self.last_timestamp)
        else:
            # 时间戳改变，毫秒内序列重置
            self.sequence = 0

        # 上次生成 ID 的时间戳
        self.last_timestamp = timestamp

        # 移位并通过或运算拼到一起组成 64 位的 ID
        new_id = ((timestamp - self.initial_time_stamp) << self.timestamp_offset) | \
                 (self.datacenter_id << self.datacenterid_offset) | \
                 (self.worker_id << self.workerid_offset) | \
            self.sequence
        return new_id

    def _til_next_millis(self, last_timestamp):
        """
        阻塞到下一个毫秒，直到获得新的时间戳
        :param last_timestamp: 上次生成 ID 的毫秒级时间戳
        :return: 当前毫秒级时间戳
        """
        timestamp = self._gen_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._gen_timestamp()
        return timestamp


"""
if __name__ == '__main__':
    mysnow = MySnow(1, 2)
    id = mysnow.next_id()
    print(id)
"""


class AsyncPool(object):
    """
    1. 支持动态添加任务
    2. 支持自动停止事件循环
    3. 支持最大协程数
    """

    def __init__(self, maxsize=1, loop=None, datacenter_id=1, worker_id=1):
        """
        初始化
        :param loop:
        :param maxsize: 默认为1
        :param datacenter_id: 默认为1  数据表示id
        :param worker_id: 默认为1  机器id
        """
        # 在jupyter需要这个，不然asyncio运行出错
        # import nest_asyncio
        # nest_asyncio.apply()

        # 队列，先进先出，根据队列是否为空判断，退出协程
        # 也许应该用 asyncio.queue
        # 这个多线程应该有竞争 查了之后是线程安全的不用改
        self.task = Queue()

        # 协程池
        self.loop, _ = self.start_loop(loop)
        # 限制并发量为500
        # asyncio.Semaphore(maxsize) 会默认获取当前循环
        # 在这个上下文中 它应该阻塞 新线程中的任务
        # self.semaphore = asyncio.Semaphore(maxsize)
        self.semaphore = self._set_concurrent(maxsize)

        # 结果队列 用于存储 任务的结果
        self.result_queue = Queue()

        self.task_id = MySnow(datacenter_id, worker_id)

    def task_add(self, item=1):
        """
        添加任务
        :param item:
        :return:
        """
        self.task.put(item)

    def task_done(self, fn,need):
        """
        任务完成
        回调函数
        :param fn:
        :param need: 是否需要结果
        :return:
        """
        if fn and need:
            self.result_queue.put(fn.result())
        self.task.get()
        self.task.task_done()

    def wait(self):
        """
        等待任务执行完毕
        :return:
        """
        self.task.join()

    @property
    def running(self):
        """
        获取当前线程数
        :return:
        """
        return self.task.qsize()

    @staticmethod
    def _start_thread_loop(loop):
        """
        运行事件循环
        :param loop: loop以参数的形式传递进来运行
        :return:
        """
        # 将当前上下文的事件循环设置为循环。
        asyncio.set_event_loop(loop)
        # 开始事件循环
        loop.run_forever()

    async def _stop_thread_loop(self, loop_time=1):
        """
        停止协程
        关闭线程
        :return:
        """
        while True:
            if self.task.empty():
                # 停止协程
                self.loop.stop()
                break
            await asyncio.sleep(loop_time)

    def _set_concurrent(self, maxsize) -> asyncio.Semaphore:
        """
        设置最大并发量
        :notice: syncio.Semaphore(maxsize) 会默认获取当前循环
                 在这个上下文中 它应该阻塞 新线程中的任务
                 所以采用asyncio.run_coroutine_threadsafe
                 在新线程的循环中调用
        :param maxsize: 最大并发量
        :return:
        """
        async def set_concurrent(maxsize):
            return asyncio.Semaphore(maxsize)

        future = asyncio.run_coroutine_threadsafe(
            set_concurrent(maxsize), self.loop)
        return future.result()

    def start_loop(self, loop):
        """
        运行事件循环
        开启新线程
        :param loop: 协程
        :return:
        """
        # 获取一个事件循环
        if not loop:
            loop = asyncio.new_event_loop()

        loop_thread = Thread(target=self._start_thread_loop, args=(loop,))
        # 设置守护进程
        loop_thread.setDaemon(True)
        # 运行线程，同时协程事件循环也会运行
        loop_thread.start()

        return loop, loop_thread

    def stop_loop(self, loop_time=1):
        """
        队列为空，则关闭线程
        :param loop_time:
        :return:
        """
        # 关闭线程任务
        asyncio.run_coroutine_threadsafe(
            self._stop_thread_loop(loop_time), self.loop)

    def release(self, loop_time=1):
        """
        释放线程
        :param loop_time:
        :return:
        """
        self.stop_loop(loop_time)

    async def async_semaphore_func(self, func, id=None, creater=None):
        """
        信号包装
        同时包装 任务id 和 创建者
        :param func:
        :return:
        """
        async with self.semaphore:
            ret = await func
            return {"id": id, "creater": creater, "result": ret}

    def submit(self, func, callback=None, creater=None,need=True):
        """
        提交任务到事件循环
        :param func: 异步函数对象
        :param callback: 回调函数
        :param creater : 任务创建者
        :param need : 是否需要结果
        :return:
        """
        self.task_add()
        # 将协程注册一个到运行在线程中的循环，thread_loop 会获得一个环任务
        # 注意：run_coroutine_threadsafe 这个方法只能用在运行在线程中的循环事件使用
        # future = asyncio.run_coroutine_threadsafe(func, self.loop)
        future = asyncio.run_coroutine_threadsafe(
            self.async_semaphore_func(func,self.task_id.next_id(),creater), self.loop)

        # 添加回调函数,添加顺序调用
        future.add_done_callback(callback)
        future.add_done_callback(partial(self.task_done,need=need))

async def thread_example(i):
    url = f"http://127.0.0.1:8080/app04/async4?num={i}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            # print(res.status)
            # print(res.content)
            return await res.text()


def my_callback(future):
    result = future.result()
    print('返回值: ', result)


def main():
    # 任务组， 最大协程数
    pool = AsyncPool(maxsize=10)

    # 插入任务任务
    for i in range(10):
        pool.submit(get_url(API_URL), my_callback)

    print("等待子线程结束1...")
    # 停止事件循环
    pool.release()

    # 获取线程数
    print("协程数 : ", pool.running)
    print("等待子线程结束2...")
    # 等待
    pool.wait()
    print("结果队列 : ",pool.result_queue.qsize())

    print("等待子线程结束3...")


API_URL = 'http://xiaoapi.cn/api/jingxuanshipin.php?type=热舞'


def url_parse(data: str):
    data.strip()
    index = data.rfind("http")
    return data[index:]


async def get_url(url: str):
    print('开始获取资源地址')
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.text()
            ret = url_parse(data)
            print("里 线程: ", threading.currentThread())
            return ret

if __name__ == '__main__':
    start_time = time.time()
    main()
    # mysnow = MySnow(1, 2)
    # for _ in range(10000):
    #     id = mysnow.next_id()
    #     print(id)
    end_time = time.time()
    print("run time: ", end_time - start_time)

    # pool = AsyncPool(maxsize=3)

