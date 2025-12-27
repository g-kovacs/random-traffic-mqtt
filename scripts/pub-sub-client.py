#!/usr/bin/python3

import json
import logging
import argparse
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import threading
import time
import uuid
import random
import base64
import os

# ---- Command line args ----
parser = argparse.ArgumentParser(
    description="MQTT pub-sub client for throughput testing"
)
parser.add_argument("--broker", default="localhost")
parser.add_argument("--port", type=int, default=1883)
parser.add_argument("--topic", default="test/msg")
parser.add_argument("--freq", type=int, default=10, help="Messages per second")
parser.add_argument("--msg-size", type=int, default=600, help="Payload size in bytes")
parser.add_argument("--log-prefix", default="mqtt")
parser.add_argument("--username")
parser.add_argument("--password")
parser.add_argument("--stats-interval", type=int, default=5)
args = parser.parse_args()

# ---- Loggers ----
tx_logger = logging.getLogger("tx")
rx_logger = logging.getLogger("rx")

tx_handler = logging.FileHandler(f"{args.log_prefix}_tx.jsonl")
rx_handler = logging.FileHandler(f"{args.log_prefix}_rx.jsonl")

for h in (tx_handler, rx_handler):
    h.setFormatter(logging.Formatter("%(message)s"))

tx_logger.addHandler(tx_handler)
rx_logger.addHandler(rx_handler)

tx_logger.setLevel(logging.INFO)
rx_logger.setLevel(logging.INFO)

# ---- Stats ----
latencies = []
payload_bytes = 0
message_count = 0
lock = threading.Lock()

client_id = f"mqtt-test-{uuid.uuid4()}"


# ---- MQTT callbacks ----
def on_connect(client, userdata, flags, rc):
    print(f"Connected as {client_id}, rc={rc}")
    client.subscribe(args.topic)


def on_message(client, userdata, msg):
    global message_count, payload_bytes
    try:
        payload = json.loads(msg.payload.decode())
        msg_ts = payload["timestamp"]
        msg_id = payload["id"]

        msg_time = datetime.fromisoformat(msg_ts.replace("Z", "+00:00"))
        latency_ms = (datetime.now(timezone.utc) - msg_time).total_seconds() * 1000

        with lock:
            message_count += 1
            latencies.append(latency_ms)
            payload_bytes += len(msg.payload)

        rx_logger.info(
            json.dumps(
                {
                    "time": now_iso(),
                    "timestamp": msg_ts,
                    "id": msg_id,
                    "latency_ms": latency_ms,
                    "payload_size": len(msg.payload),
                }
            )
        )
    except Exception as e:
        rx_logger.error(json.dumps({"error": str(e)}))


# ---- Helpers ----
def now_iso():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


# ---- Publisher thread ----
def publisher():
    interval = 1 / args.freq

    while True:
        msg = {
            "id": str(uuid.uuid4()),
            "timestamp": now_iso(),
            "payload": new_message(),
        }

        encoded = json.dumps(msg).encode()
        client.publish(args.topic, encoded, qos=0)

        tx_logger.info(
            json.dumps(
                {
                    "time": now_iso(),
                    "id": msg["id"],
                    "payload_size": len(encoded),
                }
            )
        )

        time.sleep(interval)


def new_message():
    mean = args.msg_size
    stddev = max(1, mean * 0.1)
    size = int(random.normalvariate(mean, stddev))
    size = max(1, size)

    return base64.b64encode(os.urandom(size)).decode()


# ---- Stats printer ----
def print_stats():
    global latencies, payload_bytes, message_count

    while True:
        time.sleep(args.stats_interval)
        with lock:
            count = message_count
            total_bytes = payload_bytes
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            throughput_mbps = (total_bytes * 8) / (args.stats_interval * 1_000_000)

            latencies.clear()
            payload_bytes = 0
            message_count = 0

        print(
            f"[{now_iso()}] "
            f"Avg Latency: {avg_latency:.3f} ms | "
            f"Throughput: {throughput_mbps:.3f} Mbps | "
            f"Messages: {count}"
        )


# ---- MQTT client ----
client = mqtt.Client(client_id=client_id)
if args.username and args.password:
    client.username_pw_set(args.username, args.password)

client.on_connect = on_connect
client.on_message = on_message

# ---- Threads ----
stats_thread = threading.Thread(target=print_stats, daemon=True)
pub_thread = threading.Thread(target=publisher, daemon=True)

stats_thread.start()
pub_thread.start()

# ---- Run ----
try:
    client.connect(args.broker, args.port, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("Shutting down...")
    client.disconnect()
