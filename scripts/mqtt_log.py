#!/usr/bin/env python3
import json
import logging
import argparse
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import threading
import time

# ---- Command line args ----
parser = argparse.ArgumentParser(description="MQTT subscriber logger")
parser.add_argument("--broker", default="localhost", help="MQTT broker address")
parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
parser.add_argument("--topic", default="test/msg", help="MQTT topic to subscribe")
parser.add_argument("--logfile", default="mqtt_messages.json", help="Path to log file")
parser.add_argument("--username", help="MQTT username")
parser.add_argument("--password", help="MQTT password")
args = parser.parse_args()

# ---- Logger ----
logging.basicConfig(
    filename=args.logfile,
    level=logging.INFO,
    format="%(message)s"
)

# ---- Stats ----
latencies = []
payload_bytes = 0
message_count = 0
lock = threading.Lock()

# ---- MQTT callbacks ----
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(args.topic)

def on_message(client, userdata, msg):
    global message_count, payload_bytes
    try:
        payload_str = msg.payload.decode()
        payload = json.loads(payload_str)
        msg_ts = payload.get("timestamp")
        msg_id = payload.get("id")
        if msg_ts and msg_id:
            msg_time = datetime.fromisoformat(msg_ts.replace("Z", "+00:00"))
            latency_ms = (datetime.now(timezone.utc) - msg_time).total_seconds() * 1000

            with lock:
                message_count += 1
                latencies.append(latency_ms)
                payload_bytes += len(msg.payload)

            log_entry = {
                "time": datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
                "timestamp": msg_ts,
                "id": msg_id,
                "latency_ms": latency_ms,
                "payload_size": len(msg.payload),
            }
            logging.info(json.dumps(log_entry))
    except Exception as e:
        logging.error(json.dumps({"error": str(e), "raw": msg.payload.decode()}))

# ---- Stats printer ----
def print_stats(interval=5):
    global latencies, payload_bytes, message_count
    while True:
        time.sleep(interval)
        with lock:
            count = message_count
            total_bytes = payload_bytes
            avg_latency = sum(latencies)/len(latencies) if latencies else 0
            # Calculate throughput in Mbps
            throughput_mbps = (total_bytes * 8) / (interval * 1_000_000)  # bits/sec -> Mbps
            # Reset counters for next interval
            latencies.clear()
            payload_bytes = 0
            message_count = 0
        print(f"[{datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')}] "
              f"Avg Latency: {avg_latency:.3f} ms, "
              f"Throughput: {throughput_mbps:.3f} Mbps, "
              f"Messages: {count}")

# ---- MQTT client ----
client = mqtt.Client()
if args.username and args.password:
    client.username_pw_set(args.username, args.password)
client.on_connect = on_connect
client.on_message = on_message

# ---- Start stats thread ----
stats_thread = threading.Thread(target=print_stats, daemon=True)
stats_thread.start()

try:
    client.connect(args.broker, args.port, 60)
    client.loop_forever()
except KeyboardInterrupt:
    client.disconnect()
    print("Shutting down...")

