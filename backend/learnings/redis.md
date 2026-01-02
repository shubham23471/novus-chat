# 1. The Core: Data Structures


| Structure      | What it is                                         | Common Use Case                                      |
|----------------|----------------------------------------------------|------------------------------------------------------|
| Strings        | Simple text or binary data (up to 512MB).          | Caching HTML, session tokens, counters.              |
| Hashes         | Maps of field-value pairs (like a Python Dict).    | Storing "User" objects (name, age, email).           |
| Lists          | Collections of strings sorted by insertion order.  | Task queues (LPUSH/RPOP), recent activity feeds.     |
| Sets           | Unordered collections of unique elements.          | Tracking unique visitors, tagging systems.           |
| Sorted Sets    | Sets where every member has a "score."             | Leaderboards, rate limiters (sliding window).        |
| Streams        | Append-only log for message history.               | Activity tracking, modern message brokers.           |
| Bitmaps / HLL  | Specialized tools for massive data.                | "Has this user logged in today?" (uses tiny memory). |


# 2. Persistence: How it saves data
Because Redis is in-memory, if the power goes out, the data is gone—unless you use persistence.

- RDB (Snapshotting): Saves a "point-in-time" snapshot of your data every X minutes. It’s fast to restart but you might lose a few minutes of data.

- AOF (Append Only File): Logs every single write command as it happens. It’s much safer (minimal data loss) but creates larger files.

- Hybrid: Most modern setups (like the one in your Docker file) use a mix of both.

# 3. Caching & Memory Management
If your RAM fills up, Redis needs to know what to delete to make room for new data.

- TTLs (Time To Live): You can set a key to "self-destruct" after 60 seconds or 1 hour.

- Eviction Policies:

    - LRU (Least Recently Used): Toss out the stuff no one has touched in a while.

    - LFU (Least Frequently Used): Toss out the stuff that is rarely used.

# 4. Messaging Patterns
Redis is often used to let different parts of an application talk to each other.

- Pub/Sub: "Fire and forget." A publisher sends a message to a channel, and subscribers hear it. If a subscriber is offline, they miss the message.

- Streams/Queues: "Durable messaging." Messages are stored until a worker processes them. This is what you would use for a background job system (like Celery).

# 5. High Availability (Scaling)
When your app gets huge, one Redis instance isn't enough.

- Replication: One "Primary" (writes) and multiple "Replicas" (reads).

- Sentinel: A "watchdog" system that automatically promotes a Replica to Primary if the Primary crashes.

- Cluster: Splits your data across 10 or 100 different servers so you can store terabytes of data in RAM.

# 6. Modern Redis (Redis 8.0+)
In 2026, Redis has evolved into a "Real-time Data Platform."

- Search & Query: You can now run complex searches (like SQL WHERE clauses) over your Redis Hashes and JSON.

- Vector Database: Used heavily in AI. You can store "embeddings" (mathematical representations of text/images) and perform similarity searches for LLM memory.

---
