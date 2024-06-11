import subprocess
import argparse
import numpy as np
import os
import numpy as np
from os.path import abspath, dirname

cur_dir=dirname(abspath(__file__))
os.chdir(cur_dir)

def fix_seed(seed):
    np.random.seed(seed)
from collections import deque

payload_size_in_byte=1000.0

def parse_log_entry(line):
    parts = line.split()
    
    node = int(parts[1].split(':')[1])
    
    pkt_type = parts[10]
    data_pkt = pkt_type=='U' or pkt_type=='T'
    payload_size = int(parts[-2].split('(')[1].split(')')[0])
    event_type = parts[4]
    seq = int(parts[11])
    
    if not data_pkt or node != 3 or event_type not in ['Enqu', 'Dequ'] or seq != 0:
        return None
    else:
        timestamp = int(parts[0])
        
        queue_info = parts[2].split(':')
        port = int(queue_info[0])
        queue = int(queue_info[1])
        queue_len= float(parts[3])
        flow_id = int(parts[-1])
        return {
            'timestamp': timestamp,
            'node': node,
            'port': port,
            'queue': queue,
            'payload_size': payload_size,
            'event_type': event_type,
            'data_pkt': data_pkt,
            'queue_len': queue_len/payload_size_in_byte,
            'flow_id': flow_id,
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
                assert entry['node'] == 3 and entry['port'] == 3 and entry['queue'] in [1,3]
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
                assert entry['node'] == 3 and entry['port'] == 3 and entry['queue'] in [1, 3]
                if entry['event_type'] == 'Enqu':
                    queue_lengths.append((entry['flow_id'],entry['timestamp'], entry['queue_len']))

    return queue_lengths
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
            + " | awk '{if ($7+$8<"
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
    
    cc_feat=[]
    tr_path="%s/mix_%s%s.tr" % (output_dir, args.prefix,  config_specs)
    # Read and parse the log file
    log_path = tr_path.replace('.tr', '.log')

    if not os.path.exists(log_path):
        os.system(f"{cur_dir}/trace_reader {tr_path} > {log_path}")
    queue_lengths = calculate_queue_lengths(log_path)

    with open("%s/qfeat_%s%s.txt" % (output_dir, args.prefix,  config_specs), "w") as file:
        for flowid, timestamp, queue_len in queue_lengths:
            file.write(f"{flowid} {timestamp} {queue_len}\n")
                
    os.system(
        "rm %s"
        % tr_path)
    
    # os.system("rm %s" % (file))
    # os.system(
    #     "rm %s"
    #     % ("%s/mix_%s%s.log" % (output_dir, args.prefix,  config_specs))
    # )
    
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

