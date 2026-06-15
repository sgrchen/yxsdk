# yxsdk

[![PyPI version](https://badge.fury.io/py/yxsdk.svg)](https://pypi.org/project/yxsdk/)
[![Python Version](https://img.shields.io/pypi/pyversions/yxsdk.svg)](https://pypi.org/project/yxsdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python SDK providing common utility wrappers for MySQL, Redis, SQLite, Aliyun SMS, Ollama AI inference, and Redis Streams-based event processing.

## Installation

```bash
pip install yxsdk
```

### Optional dependencies

```bash
# For WeChat AES encryption features
pip install pycryptodome

# For Tencent Cloud services
pip install tencentcloud-sdk-python
```

## Quick Start

```python
import yxsdk

# MySQL
db = yxsdk.MysqlClient(host="localhost", port=3306, user="root", password="pass", database="mydb")
rows = db.query("SELECT * FROM users WHERE status = %s", 1)

# Redis
cache = yxsdk.RedisClient(host="localhost", port=6379, db=0)
cache.set("key", {"name": "value"})

# SQLite
sqlite = yxsdk.SqliteClient("data/app.db")
rows = sqlite.query("SELECT * FROM logs")
```

## Modules

### MysqlClient

MySQL wrapper with auto-reconnect and dictionary-style row access.

```python
from yxsdk import MysqlClient

db = MysqlClient(host="localhost", port=3306, user="root", password="pass", database="mydb")

# Query — returns list of Row objects (supports both dict and attribute access)
rows = db.query("SELECT * FROM users WHERE status = %s", 1)
for row in rows:
    print(row.name, row["email"])

# Get single row (raises if more than one row returned)
user = db.get("SELECT * FROM users WHERE id = %s", 42)

# Insert — returns last inserted id
last_id = db.execute_lastrowid("INSERT INTO users (name) VALUES (%s)", "Alice")

# Update / Delete — returns affected row count
count = db.execute("UPDATE users SET status = %s WHERE id = %s", 0, 42)
```

### RedisClient

Redis wrapper with automatic JSON serialization/deserialization.

```python
from yxsdk import RedisClient

r = RedisClient(host="localhost", port=6379, db=0)

# String operations
r.set("user:1", {"name": "Alice"})          # auto JSON serialized
r.setex("session:abc", {"uid": 1}, seconds=3600)
value = r.get("user:1")                     # auto JSON deserialized

# List operations
r.rpush("queue", {"task": "send_email"})
item = r.lpop("queue")
items = r.lrange("queue", 0, -1)

# Redis Streams
r.xadd("event:app", {"type": "user.login", "payload": "{...}"})
```

### SqliteClient

SQLite wrapper with the same API as `MysqlClient`.

```python
from yxsdk import SqliteClient

db = SqliteClient("data/local.db")
rows = db.query("SELECT * FROM logs WHERE level = ?", "ERROR")
db.execute("INSERT INTO logs (message) VALUES (?)", "started")
```

### EventWorker

Abstract base class for multi-threaded Redis Streams consumer group event processing.

```python
from yxsdk import EventWorker

class MyWorker(EventWorker):
    def process_event(self, consumer_id, message_id, message_data):
        print(f"Consumer {consumer_id} processing: {message_data}")
        return True  # True = acknowledge; False = retry

worker = MyWorker(
    group_name="my-group",
    stream_name="event:app",
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    num_consumers=4,          # number of worker threads
    messages_per_batch=10,    # messages read per poll
    block_timeout=2000,       # milliseconds to block waiting for messages
)
worker.start()
```

### OllamaClient

Client for [Ollama](https://ollama.com) local LLM inference.

```python
from yxsdk import OllamaClient

client = OllamaClient(model="qwen2.5:7b", base_url="http://localhost:11434")

# Chat completion
response = client.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
])
print(response["message"]["content"])

# Text generation
result = client.generate(
    prompt="Summarize the following text: ...",
    temperature=0.3,
    max_tokens=512,
)
print(result["response"])
```

### AliyunClient

Aliyun service client using V3 HMAC-SHA256 signature. Supports SMS and email (DirectMail).

```python
from yxsdk import AliyunClient

client = AliyunClient(
    access_key_id="YOUR_KEY_ID",
    access_key_secret="YOUR_SECRET",
)

# Send SMS
client.send_sms(
    phone_numbers="138xxxxxxxx",
    sign_name="MySign",
    template_code="SMS_12345678",
    template_param={"code": "123456"},
)

# Send single email (DirectMail)
client.send_email(
    account_name="noreply@example.com",
    to_address="user@example.com",
    subject="测试邮件",
    html_body="<h1>Hello</h1>",
    # text_body="Hello",  # 纯文本正文（与 html_body 二选一）
    reply_to_address=False,
)
```

### ProtocolConverterManager / ProtocolConverterInterface

Dynamic protocol converter loader and dispatcher for IoT protocol translation.

```python
from yxsdk import ProtocolConverterManager, ProtocolConverterInterface

# Implement a custom converter
class MyConverter(ProtocolConverterInterface):
    def convert(self, message):
        return transform(message)
    def get_input_protocol(self):
        return "modbus"
    def get_output_protocol(self):
        return "mqtt"

# Load converters by module path and dispatch by protocol pair
manager = ProtocolConverterManager()
manager.load_converters(["mypackage.converters"])
converter = manager.get_converter("modbus", "mqtt")
result = converter.convert(raw_data)
```

### Utility Functions

```python
from yxsdk import datetime_str, log_debug, json_dumps, uuid_generate

# Current datetime string or from Unix timestamp
now = datetime_str()               # "2026-05-16 10:30:00"
ts  = datetime_str(1747358000)     # "2025-05-16 08:13:20"

# Debug log with timestamp prefix
log_debug("MyApp", "Server started")
# [2026-05-16 10:30:00] MyApp: Server started

# JSON serialization preserving non-ASCII characters
text = json_dumps({"name": "张三"})   # '{"name": "张三"}'

# UUID hex string (uppercase)
uid = uuid_generate()  # e.g. "A3F2B1C4D5E6F7A8..."
```

## Development

```bash
# Install build tools
pip install build

# Clean previous build artifacts and rebuild
rmdir /s /q dist build src\yxsdk.egg-info
python -m build
```

## Notes

- Set `sys.dont_write_bytecode = True` to prevent `.pyc` file generation at runtime.
- The package version is read from `src/version.txt`.

## License

MIT
