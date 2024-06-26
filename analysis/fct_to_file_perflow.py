import subprocess
import argparse
import numpy as np
import os
import numpy as np
from os.path import abspath, dirname
from enum import Enum
from collections import deque

cur_dir=dirname(abspath(__file__))
os.chdir(cur_dir)

class QueueEvent(Enum):
    ARRIVAL_FIRST_PKT = 1
    ARRIVAL_LAST_PKT = 2
    QUEUE_START = 3
    QUEUE_END = 4
class OutputType(Enum):
    CC_FINGERPRINT = 0
    PER_FLOW_QUEUE = 1
    BUSY_PERIOD = 2
    
def fix_seed(seed):
    np.random.seed(seed)

target_node_id=21
queue_threshold=0
busy_period_threshold=0

def parse_log_entry(line):
    parts = line.split()
    
    node = int(parts[1].split(':')[1])
    pkt_type = parts[10]
    data_pkt = pkt_type=='U' or pkt_type=='T'
    event_type = parts[4]
    queue_event=int(parts[16])
    
    if not data_pkt or node != target_node_id or event_type not in ['Enqu', 'Dequ'] or queue_event not in [1,2]:
        return None
    else:
        timestamp = int(parts[0])
        
        queue_info = parts[2].split(':')
        port = int(queue_info[0])
        queue = int(queue_info[1])
        queue_len= int(parts[3])
        payload_size = int(parts[14].split('(')[1].split(')')[0])
        flow_id = int(parts[15])
        n_active_flows=int(parts[17])
        return {
            'timestamp': timestamp,
            'node': node,
            'port': port,
            'queue': queue,
            'payload_size': payload_size,
            'event_type': event_type,
            'data_pkt': data_pkt,
            'queue_len': queue_len,
            'flow_id': flow_id,
            'queue_event': queue_event,
            'n_active_flows': n_active_flows,
        }

def calculate_throughput_and_delay(log_file):
    start_time=None
    end_time=None
    enqu_timestamps = deque()
    total_payload = 0
    queuing_delay_list = []
    with open(log_file, 'r') as file:
        for line in file:
            entry = parse_log_entry(line)
            if entry:
                assert entry['node'] == target_node_id and entry['port'] == target_node_id and entry['queue'] in [1,3]
                if start_time is None:
                    start_time = entry['timestamp']
                end_time = entry['timestamp']
                if entry['event_type'] == 'Enqu':
                    enqu_timestamps.append(entry['timestamp'])
                elif entry['event_type'] == 'Dequ':
                    total_payload += entry['payload_size']
                    if enqu_timestamps:
                        queuing_delay_list.append(entry['timestamp'] - enqu_timestamps.popleft())

    total_time = end_time - start_time
    throughput = total_payload * 8 / total_time
    average_queuing_delay = np.mean(queuing_delay_list)  if len(queuing_delay_list) > 0 else 0
    return throughput, average_queuing_delay,queuing_delay_list

def calculate_queue_lengths(log_file):
    queue_lengths = []
    with open(log_file, 'r') as file:
        for line in file:
            entry = parse_log_entry(line)
            if entry:
                assert entry['node'] == target_node_id and entry['port'] == target_node_id and entry['queue'] in [1, 3]
                if entry['event_type'] == 'Enqu':
                    queue_lengths.append((entry['flow_id'],entry['timestamp'], entry['queue_len'], entry['queue_event'],entry['n_active_flows']))

    return np.array(queue_lengths)

def calculate_busy_period(log_file):
    flow_id_per_period=[]
    flow_id_per_period_cur=None
    n_flow_event=0
    qlen_prev = 0
    with open(log_file, 'r') as file:
        for line in file:
            entry = parse_log_entry(line)
            if entry:
                assert entry['node'] == target_node_id and entry['port'] == target_node_id and entry['queue'] in [1, 3]
                if entry['event_type'] == 'Enqu':
                    queue_event = entry["queue_event"]
                    flow_id = entry["flow_id"]
                    queue_len=entry["queue_len"]
                    n_active_flows=entry["n_active_flows"]
                   
                    if queue_event == int(QueueEvent.ARRIVAL_FIRST_PKT.value) or queue_event == int(QueueEvent.ARRIVAL_LAST_PKT.value):
                        n_flow_event+=1
                        if queue_len>queue_threshold:
                            if qlen_prev<=queue_threshold:
                                # start a new busy period
                                if flow_id_per_period_cur is None:
                                    flow_id_per_period_cur=set()
                        else:
                            if qlen_prev>queue_threshold:
                                # terminate a new busy period
                                if n_active_flows==0 and flow_id_per_period_cur is not None and len(flow_id_per_period_cur)>busy_period_threshold:
                                    assert queue_event == int(QueueEvent.ARRIVAL_LAST_PKT.value)
                                    flow_id_per_period.append(flow_id_per_period_cur)
                                    flow_id_per_period_cur=None
                        qlen_prev=queue_len
                        if flow_id_per_period_cur is not None:
                            flow_id_per_period_cur.add(flow_id)
                    else:
                        assert "Invalid queue_event"
    n_flows_per_period=[len(flow_id_per_period[i]) for i in range(len(flow_id_per_period))]
    flow_id_per_period_unique= [item for sublist in flow_id_per_period for item in sublist]
    assert len(flow_id_per_period_unique)==len(set(flow_id_per_period_unique))
    if len(flow_id_per_period)>0:
        print(f"n_flow_event: {n_flow_event}, {len(n_flows_per_period)} busy periods, n_flows_per_period: {np.min(n_flows_per_period)}, {np.max(n_flows_per_period)}, {len(flow_id_per_period_unique)} unique flows")
    else:
        print(f"n_flow_event: {n_flow_event}, no busy period")
    return flow_id_per_period

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-p",
        dest="prefix",
        action="store",
        default="topo4-4_traffic",
        help="Specify the prefix of the fct file. Usually like fct_<topology>_<trace>",
    )
    parser.add_argument("-s", dest="step", action="store", default="5")
    parser.add_argument(
        "--shard", dest="shard", type=int, default=0, help="random seed"
    )
    parser.add_argument("--shard_cc", dest = "shard_cc",type=int, default=0, help="random seed")
    parser.add_argument(
        "-t",
        dest="type",
        action="store",
        type=int,
        default=0,
        help="0: normal, 1: incast, 2: all",
    )
    parser.add_argument('--enable_debug', dest='enable_debug', action = 'store', type=int, default=0, help="enable debug for parameter sample space")
    parser.add_argument(
        "--output_dir",
        dest="output_dir",
        action="store",
        default="data/input",
        help="the name of the flow file",
    )
    parser.add_argument(
        "--scenario_dir",
        dest="scenario_dir",
        action="store",
        default="AliStorage2019_exp_util0.5_lr10Gbps_nflows10000_nhosts4",
        help="the name of the flow file",
    )
    args = parser.parse_args()
    enable_debug=args.enable_debug
    output_type=OutputType.BUSY_PERIOD
    
    fix_seed(args.shard)
    type = args.type

    time_limit = int(30000 * 1e9)
    shard_cc=args.shard_cc
    config_specs = "_s%d"%(shard_cc)
    output_dir = "%s/%s" % (args.output_dir, args.scenario_dir)
    file = "%s/fct_%s%s.txt" % (output_dir, args.prefix, config_specs)
    if not os.path.exists(file):
        exit(0)
    # print file
    if type == 0:
        cmd = (
            "cat %s" % (file)
            + " | awk '{if ($5==100 && $7+$8<"
            + "%d" % time_limit
            + ") {slow=$8/$9;print slow<1?$9:$8, $9, $6, $7, $2, $3, $1}}' | sort -n -k 4"
        )
        # print cmd
        output = subprocess.check_output(cmd, shell=True)
    # elif type == 1:
    #     cmd = (
    #         "cat %s" % (file)
    #         + " | awk '{if ($4==200 && $6+$7<"
    #         + "%d" % time_limit
    #         + ") {slow=$7/$8;print slow<1?1:slow, $5}}'"
    #     )
    #     # print cmd
    #     output = subprocess.check_output(cmd, shell=True)
    # else:
    #     cmd = (
    #         "cat %s" % (file)
    #         + " | awk '{$6+$7<"
    #         + "%d" % time_limit
    #         + ") {slow=$7/$8;print slow<1?1:slow, $5}}'"
    #     )
    #     # print cmd
    #     output = subprocess.check_output(cmd, shell=True)

    # up to here, `output` should be a string of multiple lines, each line is: fct, size
    
    output=output.decode()
    a = output[:-1].split("\n")
    n = len(a)
    res_np = np.array([x.split() for x in a])
    print(res_np.shape)
    # for i in range(n):
    # 	print "%s %s %s %s %s %s"%(res_np[i,0], res_np[i,1], res_np[i,2], res_np[i,3], res_np[i,4], res_np[i,5])
    fcts = res_np[:, 0].astype("int64")
    i_fcts = res_np[:, 1].astype("int64")
    fid=res_np[:, 6].astype("int64")
    np.save(
        "%s/fct_%s%s.npy" % (output_dir, args.prefix, config_specs), fcts
    )  # Byte
    np.save(
        "%s/fct_i_%s%s.npy" % (output_dir, args.prefix, config_specs),
        i_fcts,
    )  # ns
    np.save("%s/fid_%s%s.npy" % (output_dir, args.prefix, config_specs), fid)
    
    tr_path="%s/mix_%s%s.tr" % (output_dir, args.prefix,  config_specs)
    # Read and parse the log file
    log_path = tr_path.replace('.tr', '.log')

    if not os.path.exists(log_path):
        os.system(f"{cur_dir}/trace_reader {tr_path} > {log_path}")
    
    if output_type==OutputType.PER_FLOW_QUEUE:
        queue_lengths = calculate_queue_lengths(log_path)

        with open("%s/qfeat_%s%s.txt" % (output_dir, args.prefix,  config_specs), "w") as file:
            for flowid, timestamp, queue_len, queue_event, n_active_flows in queue_lengths:
                file.write(f"{flowid} {timestamp} {queue_len} {queue_event} {n_active_flows}\n")
        print(queue_lengths.shape)
        np.save("%s/qfeat_%s%s.npy" % (output_dir, args.prefix, config_specs), queue_lengths)
    elif output_type==OutputType.BUSY_PERIOD:
        flow_id_per_period=calculate_busy_period(log_path)
        np.save("%s/period_%s%s.npy" % (output_dir, args.prefix, config_specs), flow_id_per_period)
        # with open("%s/period_%s%s.txt" % (output_dir, args.prefix, config_specs), "w") as file:
        #     for period in flow_id_per_period:
        #         file.write(" ".join(map(str, period)) + "\n")
#            
    os.system(
        "rm %s"
        % tr_path)
    
    os.system("rm %s" % (file))
    os.system(
        "rm %s"
        % ("%s/mix_%s%s.log" % (output_dir, args.prefix,  config_specs))
    )
    os.system("rm %s/flows.txt" % (output_dir))
    
    # os.system(
    #     "rm %s"
    #     % ("%s/pfc_%s%s.txt" % (output_dir, args.prefix,  config_specs))
    # )

    # os.system(
    #     "rm %s"
    #     % ("%s/qlen_%s%s.txt" % (output_dir, args.prefix, config_specs))
    # )
    
    # os.system(
    #     "rm %s"
    #     % ("%s/pdrop_%s%s.txt" % (output_dir, args.prefix, config_specs))
    # )

