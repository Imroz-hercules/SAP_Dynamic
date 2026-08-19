#!/usr/bin/env python3
from services.system_logger import system_logger

print("Checking current logs in database...")
logs = system_logger.get_logs(limit=10)
print(f"Total logs found: {len(logs)}")

if logs:
    print("\nRecent logs:")
    for i, log in enumerate(logs[:5], 1):
        print(f"{i}. {log['timestamp']} | {log['source']} | {log['action']} | {log['status']}")
else:
    print("No logs found in database")
