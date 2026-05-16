import sys
import json
import threading
import time
import requests
from abc import ABC, abstractmethod
from .redis_client import RedisClient

class EventWorker(ABC):
    """
    Redis 消费组事件处理器基类
    """
    
    def __init__(self, group_name, stream_name, redis_host='localhost', 
                 redis_port=6379, redis_db=0, num_consumers=2, 
                 messages_per_batch=5, block_timeout=2000):
        """
        初始化事件处理器
        
        Args:
            group_name: 消费组名称
            stream_name: Redis 流名称
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            redis_db: Redis 数据库编号
            num_consumers: 消费者数量
            messages_per_batch: 每次读取消息数量
            block_timeout: 阻塞时间(毫秒)
        """
        self.group_name = group_name
        self.stream_name = stream_name
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.num_consumers = num_consumers
        self.messages_per_batch = messages_per_batch
        self.block_timeout = block_timeout
        
        # 创建 Redis 客户端
        self.redis_client = RedisClient(
            host=self.redis_host, 
            port=self.redis_port, 
            db=self.redis_db
        )
        
        self.threads = []
        self.running = False
    
    @abstractmethod
    def process_event(self, consumer_id, message_id, message_data):
        """
        处理事件的抽象方法，子类必须实现
        
        Args:
            consumer_id: 消费者ID
            message_id: 消息ID
            message_data: 消息数据
            
        Returns:
            bool: 处理成功返回 True，失败返回 False
        """
        pass
    
    def worker(self, consumer_id):
        """
        工作线程方法
        """
        # 每个工作线程创建独立的 Redis 连接
        worker_redis_client = RedisClient(
            host=self.redis_host, 
            port=self.redis_port, 
            db=self.redis_db
        )
        
        print(f"事件处理工作线程 {consumer_id} 启动，等待消息...")
        
        while self.running:
            try:
                messages = worker_redis_client.xreadgroup(self.stream_name, self.group_name, consumer_id, block=self.block_timeout)
                if messages:
                    for stream_name, message_list in messages:
                        for message_id, message_data in message_list:                            
                            success = self.process_event(consumer_id, message_id, message_data)        
                            if not success:
                                print(f"[消费者 {consumer_id}] 处理消息 {message_id} 失败")
                            worker_redis_client.xack(self.stream_name, self.group_name, message_id)                                
            except Exception as e:
                if self.running:  # 只有在运行状态才打印错误
                    print(f"[消费者 {consumer_id}] 读取消息出错: {e}")
                    time.sleep(5)  # 异常发生时暂停一下再继续
    
    def start(self):
        try:
            self.running = True
            
            # 启动多个工作线程
            for i in range(self.num_consumers):
                t = threading.Thread(target=self.worker, args=(i+1,))
                self.threads.append(t)
                t.daemon = True  # 设置为守护线程
                t.start()
                print(f"启动消费者 {i+1}")
            
            print(f"事件处理器启动完成，共 {self.num_consumers} 个消费者")
            
            # 等待所有线程
            for t in self.threads:
                t.join()
                
        except KeyboardInterrupt:
            print("程序中断，正在退出...")
            self.stop()
    
    def stop(self):
        print("正在停止事件处理器...")
        self.running = False
        
        # 等待所有线程结束
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=5)
        
        print("事件处理器已停止")
