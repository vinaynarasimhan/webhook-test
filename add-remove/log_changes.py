#!/usr/bin/env python3
from datetime import datetime

def log_event():
    with open('/home/admin/git/webhook-test/add-remove/log.txt', 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f'[{timestamp}] CSV file change detected and handled successfully\n')

if __name__ == '__main__':
    log_event()