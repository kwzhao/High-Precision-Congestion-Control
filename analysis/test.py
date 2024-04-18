import pandas as pd
import os
from collections import deque
import numpy as np

def parse_log_entry(line):
    parts = line.split()
    data_pkt = parts[10]=='U' 
    node = int(parts[1].split(':')[1])
    event_type = parts[4]
    if not data_pkt or node != 3 or event_type not in ['Enqu', 'Dequ']:
        return None
    else:
        timestamp = int(parts[0])
        queue_info = parts[2].split(':')
        port = int(queue_info[0])
        queue = int(queue_info[1])
        payload_size = int(parts[-1].split('(')[1].split(')')[0])
        queue_len= int(parts[3])
        return {
            'timestamp': timestamp,
            'node': node,
            'port': port,
            'queue': queue,
            'payload_size': payload_size,
            'event_type': event_type,
            'data_pkt': data_pkt,
            'queue_len': queue_len
        }

def calculate_throughput_and_delay(log_file):
    start_time=None
    end_time=None
    enqu_timestamps = deque()
    total_payload = 0
    queuing_delay_list = []
    queue_len_max=0
    queue_len_min=1000000
    with open(log_file, 'r') as file:
        for line in file:
            entry = parse_log_entry(line)
            if entry:
                assert entry['node'] == 3 and  entry['queue'] == 3
                if start_time is None:
                    start_time = entry['timestamp']
                end_time = entry['timestamp']
                if entry['event_type'] == 'Enqu':
                    enqu_timestamps.append(entry['timestamp'])
                    queue_len_max=max(queue_len_max,entry['queue_len'])
                    queue_len_min=min(queue_len_min,entry['queue_len'])
                elif entry['event_type'] == 'Dequ':
                    total_payload += entry['payload_size']
                    if enqu_timestamps:
                        queuing_delay_list.append(entry['timestamp'] - enqu_timestamps.popleft())

    total_time = end_time - start_time
    throughput = total_payload * 8 / total_time
    average_queuing_delay = np.mean(queuing_delay_list)  if len(queuing_delay_list) > 0 else 0
    return throughput, average_queuing_delay,queuing_delay_list

shard=0
nhosts=3

shard_seed_list=[0]
# nflows_list=[1,50]
# bw_list=[1,5,9]
# pd_list=[1000,5000,9000]
nflows_list=np.arange(1,10,2)
bw_list=np.arange(1,10,2)
pd_list=np.arange(1000,10000,2000)
tr_list=[]

for nflows in nflows_list:
    data_dir=f"/data2/lichenni/path_tc_cc/shard{shard}_nflows{nflows}_nhosts{nhosts}"
    for shard_seed in shard_seed_list:
        for bw in bw_list:
            for pd in pd_list:
                tr_list.append(f"{data_dir}/mix_topo-pl-{nhosts}-{bw}-{pd}_s{shard_seed}.tr")
print(f"{len(tr_list)} tr files to be processed")
for tr_path in tr_list:
    # Read and parse the log file
    log_path = tr_path.replace('.tr', '.log')

    if not os.path.exists(log_path):
        os.system(f"./trace_reader {tr_path} > {log_path}")
        
    throughput, queuing_delay,queuing_delay_list = calculate_throughput_and_delay(log_path)
    print(f"{log_path}. Throughput: {throughput}Gbps, Queuing Delay: {queuing_delay}ns")