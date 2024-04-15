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
        return {
            'timestamp': timestamp,
            'node': node,
            'port': port,
            'queue': queue,
            'payload_size': payload_size,
            'event_type': event_type,
            'data_pkt': data_pkt
        }

def calculate_throughput_and_delay(log_file):
    start_time=None
    end_time=None
    enqu_timestamps = deque()
    packet_count = 0
    total_payload = 0
    total_queuing_delay = 0
    
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
                elif entry['event_type'] == 'Dequ':
                    total_payload += entry['payload_size']
                    packet_count += 1
                    if enqu_timestamps:
                        total_queuing_delay += entry['timestamp'] - enqu_timestamps.popleft()

    total_time = end_time - start_time
    throughput = total_payload*8 / total_time
    average_queuing_delay = total_queuing_delay / packet_count if packet_count > 0 else 0

    return throughput, average_queuing_delay

shard=0
nhosts=3

shard_seed_list=[0]
nflows_list=[1]
bw_list=[1]
pd_list=[1000]
# nflows_list=np.arange(1,10,2)
# bw_list=np.arange(10,60,10)
# pd_list=np.arange(1000,6000,1000)
tr_list=[]

for nflows in nflows_list:
    data_dir=f"/data2/lichenni/path_tc_cc/shard{shard}_nflows{nflows}_nhosts{nhosts}"
    for shard_seed in shard_seed_list:
        for bw in bw_list:
            for pd in pd_list:
                tr_list.append(f"{data_dir}/mix_topo-pl-{nhosts}-{bw}-{pd}_s{shard_seed}.tr")
# Calculate stats using a 1ms window
window_size_ns = 20*1e6  # 1ms in nanoseconds

flow_rate_top=10
flow_rate_bottom=0
queue_size_top=40
queue_size_bottom=0
ecn_mark_top = 1.0  # Maximum value for the y-axis
ecn_mark_bottom = 0.0  # Minimum value for the y-axis
pfc_top = 0.2  # Maximum value for the y-axis
pfc_bottom = 0.0  # Minimum value for the y-axis
drop_top = 1000  # Maximum value for the y-axis
drop_bottom = 0.0  # Minimum value for the y-axis
print(f"{len(tr_list)} tr files to be processed")
for tr_path in tr_list:
    # Read and parse the log file
    log_path = tr_path.replace('.tr', '.log')

    if not os.path.exists(log_path):
        os.system(f"./trace_reader {tr_path} > {log_path}")
        
    throughput, queuing_delay = calculate_throughput_and_delay(log_path)
    print(f"{log_path}. Throughput: {throughput}Gbps, Queuing Delay: {queuing_delay}s")