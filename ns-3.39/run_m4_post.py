import subprocess
import argparse
import numpy as np
import os
import numpy as np
from os.path import abspath, dirname
from enum import Enum
from collections import deque, defaultdict
import traceback

cur_dir = dirname(abspath(__file__))
os.chdir(cur_dir)


def fix_seed(seed):
    np.random.seed(seed)


def calculate_busy_period_path(
    fat,
    fct,
    fid,
    fsd,
    fsize,
    nhosts,
    flow_size_threshold,
    remainsize_list,
):
    if flow_size_threshold == 100000000:
        flow_size_threshold = np.inf
    flows = {}
    for i in range(len(fid)):
        links = set()
        links.add((fsd[i][0], nhosts + fsd[i][0]))
        for link_idx in range(fsd[i][0], fsd[i][1]):
            links.add((nhosts + link_idx, nhosts + link_idx + 1))
        links.add((nhosts + fsd[i][1], fsd[i][1]))
        flows[fid[i]] = {
            "start_time": fat[i],
            "end_time": fat[i] + fct[i],
            "links": links,
            "size": fsize[i],
        }

    active_graphs = (
        {}
    )  # Dictionary to hold multiple bipartite graphs with graph_id as key
    busy_periods = []  # List to store busy periods
    busy_periods_len = []
    busy_periods_duration = []
    remainsizes = []
    remainsizes_num = []
    busy_periods_unique = set()
    events = []

    # flow_to_end_time = {}
    for flow_id, flow in flows.items():
        events.append(
            (flow["start_time"], "start", flow_id, flow["links"], flow["size"])
        )
        events.append((flow["end_time"], "end", flow_id, flow["links"], flow["size"]))
        # flow_to_end_time[flow_id] = flow["end_time"]

    events.sort()

    link_to_graph = {}  # Map to quickly find which graph a link belongs to
    graph_id_new = 0  # Unique identifier for each graph
    large_flow_to_info = {}
    flow_to_size = {}
    for event_idx, (time, event, flow_id, links, size) in enumerate(events):
        cur_time = time
        # if flow_id % 1000 == 0:
        #     print(f'Processing flow {flow_id}')

        if event == "start":
            flow_to_size[flow_id] = size
            if size > flow_size_threshold:
                large_flow_to_info[flow_id] = (time, links)
                # involved_graph_ids = set()
                # for link in links:
                #     if link in link_to_graph:
                #         involved_graph_ids.add(link_to_graph[link])
                # if involved_graph_ids:
                #     for gid in involved_graph_ids:
                #         graph = active_graphs[gid]
                #         graph["all_links"].add(link)
                #         graph["all_flows"].add(flow_id)
            else:
                new_active_links = defaultdict(set)
                new_all_links = set()
                new_flows = set()
                new_all_flows = set()
                new_event_idxs = set()

                involved_graph_ids = set()
                for link in links:
                    if link in link_to_graph:
                        involved_graph_ids.add(link_to_graph[link])

                if involved_graph_ids:
                    for gid in involved_graph_ids:
                        graph = active_graphs[gid]
                        new_active_links.update(graph["active_links"])
                        new_all_links.update(graph["all_links"])
                        new_flows.update(graph["active_flows"])
                        new_all_flows.update(graph["all_flows"])
                        new_event_idxs.update(graph["event_idxs"])
                        if cur_time > graph["start_time"]:
                            cur_time = graph["start_time"]

                        for link in graph["active_links"]:
                            link_to_graph[link] = graph_id_new
                        del active_graphs[gid]

                for link in links:
                    new_active_links[link].add(flow_id)
                    new_all_links.add(link)
                    link_to_graph[link] = graph_id_new
                new_flows.add(flow_id)
                new_all_flows.add(flow_id)
                new_event_idxs.add(event_idx)
                for large_flow_id in large_flow_to_info:
                    _, links_tmp = large_flow_to_info[large_flow_id]
                    if large_flow_id not in new_all_flows and not links_tmp.isdisjoint(
                        new_all_links
                    ):
                        new_all_flows.add(large_flow_id)
                active_graphs[graph_id_new] = {
                    "active_links": new_active_links,
                    "all_links": new_all_links,
                    "active_flows": new_flows,
                    "all_flows": new_all_flows,
                    "start_time": cur_time,
                    "event_idxs": new_event_idxs,
                }
                graph_id_new += 1

        elif event == "end":
            graph = None
            flow_to_size.pop(flow_id)
            if flow_id in large_flow_to_info:
                large_flow_to_info.pop(flow_id)
                # involved_graph_ids = set()
                # for link in links:
                #     if link in link_to_graph:
                #         involved_graph_ids.add(link_to_graph[link])
                # if involved_graph_ids:
                #     for gid in involved_graph_ids:
                #         graph = active_graphs[gid]
                #         graph["all_links"].add(link)
                #         graph["all_flows"].add(flow_id)
            else:
                for link in links:
                    if link in link_to_graph:
                        graph_id = link_to_graph[link]
                        graph = active_graphs[graph_id]
                        break

                if graph:
                    for link in links:
                        if flow_id in graph["active_links"][link]:
                            graph["active_links"][link].remove(flow_id)
                            if not graph["active_links"][link]:
                                del graph["active_links"][link]
                                del link_to_graph[link]
                        else:
                            assert (
                                False
                            ), f"Flow {flow_id} not found in link {link} of graph {graph_id}"
                    if flow_id in graph["active_flows"]:
                        graph["active_flows"].remove(flow_id)
                    else:
                        assert (
                            False
                        ), f"Flow {flow_id} not found in active flows of graph {graph_id}"
                    graph["event_idxs"].add(event_idx)

                    n_small_flows = len(
                        [
                            flow_id
                            for flow_id in graph["active_flows"]
                            if flow_to_size[flow_id] <= flow_size_threshold
                        ]
                    )
                    # n_large_flows = len(graph["active_flows"]) - n_small_flows
                    if n_small_flows == 0:  # If no active small flows left in the graph
                        assert (
                            len(graph["active_flows"])
                            == len(graph["active_links"])
                            == 0
                        ), f"n_active_flows: {len(graph['active_flows'])}, n_active_links: {len(graph['active_links'])}"
                        # end_time = cur_time
                        # for flow_id in graph["active_flows"]:
                        #     if flow_to_end_time[flow_id] > end_time:
                        #         end_time = flow_to_end_time[flow_id]
                        # busy_periods.append((graph['start_time'], end_time, list(graph['all_links']), list(graph['all_flows'])))
                        # if len(graph["all_flows"]) > 0:
                        fid_target = sorted(graph["all_flows"])
                        busy_periods.append(tuple(fid_target))
                        busy_periods_len.append(len(fid_target))
                        busy_periods_duration.append([graph["start_time"], cur_time])
                        busy_periods_unique.update(fid_target)

                        busy_period_event_idxs = sorted(graph["event_idxs"])
                        remainsize = []
                        for i in busy_period_event_idxs:
                            tmp = remainsize_list[i]
                            if isinstance(tmp, dict):
                                tmp_list = []
                                for j in fid_target:
                                    if j in tmp:
                                        tmp_list.append(tmp[j])
                                if len(tmp_list) > 0:
                                    remainsize.append(tmp_list)
                                else:
                                    remainsize.append([0])
                            else:
                                remainsize.append(tmp)
                        assert (
                            len(remainsize) == len(fid_target) * 2
                        ), f"{len(remainsize)} != {len(fid_target) * 2}"

                        remainsizes_num.append(np.max([len(x) for x in remainsize]))
                        remainsizes.append(tuple(remainsize))

                        del active_graphs[graph_id]
                        # for link in graph["active_links"]:
                        #     del link_to_graph[link]

                        # if n_large_flows > 0:
                        #     new_active_links = defaultdict(set)
                        #     new_all_links = set()
                        #     new_flows = set()
                        #     new_all_flows = set()
                        #     start_time = cur_time
                        #     for flow_id in graph["active_flows"]:
                        #         new_flows.add(flow_id)
                        #         new_all_flows.add(flow_id)
                        #         for link in large_flow_to_info[flow_id][1]:
                        #             new_active_links[link].add(flow_id)
                        #             new_all_links.add(link)
                        #             link_to_graph[link] = graph_id_new
                        #         # if large_flow_to_info[flow_id][0] < start_time:
                        #         #     start_time = large_flow_to_info[flow_id][0]
                        #     active_graphs[graph_id_new] = {
                        #         "active_links": new_active_links,
                        #         "all_links": new_all_links,
                        #         "active_flows": new_flows,
                        #         "all_flows": new_all_flows,
                        #         "start_time": start_time,
                        #     }
                        #     graph_id_new += 1
                else:
                    assert False, f"Flow {flow_id} has no active graph"

    print(
        f"n_flow_event: {len(events)}, {len(busy_periods)} busy periods, flow_size_threshold: {flow_size_threshold}, n_flows_unique: {len(busy_periods_unique)} , n_flows_per_period_est: {np.min(busy_periods_len)}, {np.mean(busy_periods_len)}, {np.max(busy_periods_len)}"
    )

    return busy_periods, busy_periods_duration, remainsizes, remainsizes_num


def calculate_busy_period_link(
    fat,
    fct,
    fid,
    fsize_total,
    flow_size_threshold,
    remainsize_list,
):
    if flow_size_threshold == 100000000:
        flow_size_threshold = np.inf
    events = []
    flow_to_fsize = {}
    for i in range(len(fat)):
        events.append((fat[i], "arrival", fid[i]))
        events.append((fat[i] + fct[i], "departure", fid[i]))
        flow_to_fsize[fid[i]] = fsize_total[i]
    events.sort(key=lambda x: x[0])

    n_inflight_flows = 0
    current_busy_period_start_time = None
    current_busy_period_start_event = None
    busy_periods_time = []

    active_flows = set()
    enable_new_period = True
    event_idx = 0
    for event in events:
        time, event_type, flow_id = event
        if event_type == "arrival":
            n_inflight_flows += 1
            if flow_to_fsize[flow_id] < flow_size_threshold:
                active_flows.add(flow_id)
            if enable_new_period:
                current_busy_period_start_time = time
                current_busy_period_start_event = event_idx
                enable_new_period = False
        elif event_type == "departure":
            n_inflight_flows -= 1
            if flow_to_fsize[flow_id] < flow_size_threshold:
                active_flows.remove(flow_id)
            if not enable_new_period and len(active_flows) == 0:
                busy_periods_time.append(
                    (
                        current_busy_period_start_time,
                        time,
                        current_busy_period_start_event,
                        event_idx,
                    )
                )
                enable_new_period = True
        event_idx += 1
    busy_periods = []
    busy_periods_len = []
    busy_periods_duration = []
    remainsizes = []
    remainsizes_num = []
    busy_periods_unique = set()
    for busy_period_time in busy_periods_time:
        (
            busy_period_start,
            busy_period_end,
            busy_period_start_event_idx,
            busy_period_end_event_idx,
        ) = busy_period_time
        fid_target_idx = ~np.logical_or(
            fat + fct <= busy_period_start,
            fat >= busy_period_end,
        )
        fid_target = fid[fid_target_idx]
        if np.sum(fid_target) > 0:
            # busy_periods.append([np.min(fid_target), np.max(fid_target)])
            # busy_periods_len.append(len(fid_target))
            busy_periods.append(tuple(fid_target))
            busy_periods_len.append(len(fid_target))
            busy_periods_duration.append([busy_period_start, busy_period_end])
            busy_periods_unique.update(fid_target)
            remainsize = []
            for i in range(busy_period_start_event_idx, busy_period_end_event_idx + 1):
                tmp = remainsize_list[i]
                if isinstance(tmp, dict):
                    tmp_list = []
                    for j in fid_target:
                        if j in tmp:
                            tmp_list.append(tmp[j])
                    remainsize.append(tmp_list)
                else:
                    remainsize.append(tmp)
            # remainsize = [
            #     remainsize_list[i]
            #     for i in range(
            #         busy_period_start_event_idx, busy_period_end_event_idx + 1
            #     )
            # ]
            # if len(remainsizes) == 1490:
            #     fats = fat[fid_target_idx]
            #     fcts = fct[fid_target_idx]
            #     fats = fats - fats[0]
            #     fcts_stamp = fats + fcts

            #     # Concatenate the arrays
            #     merged = np.concatenate((fats, fcts_stamp))
            #     sorted_indices = np.argsort(merged)
            #     idx_completion_events = np.where(sorted_indices >= len(fats))[0]
            #     idx_completion_ranks = np.argsort(fcts_stamp)

            #     print(
            #         f"remainsize: {len(remainsize)}, {len(fid_target)}, {len(busy_periods_time)}, {fid_target[0]}, {busy_period_start_event_idx}"
            #     )
            assert (
                len(remainsize) == len(fid_target) * 2
            ), f"{len(remainsize)} != {len(fid_target) * 2}"

            remainsizes_num.append(np.max([len(x) for x in remainsize]))
            remainsizes.append(tuple(remainsize))

    # unique_lengths, counts = np.unique(busy_periods_len, return_counts=True)

    # if not enable_empirical:
    #     busy_periods_filter=[]
    #     busy_periods_len_filter=[]
    #     for length, count in zip(unique_lengths, counts):
    #         period_indices = np.where(busy_periods_len == length)[0]
    #         if count > 500:
    #             period_indices=np.random.choice(period_indices,500,replace=False)
    #         busy_periods_filter.extend([busy_periods[i] for i in period_indices])
    #         busy_periods_len_filter.extend([busy_periods_len[i] for i in period_indices])
    #     busy_periods=busy_periods_filter
    #     busy_periods_len=busy_periods_len_filter
    print(
        f"n_flow_event: {len(events)}, {len(busy_periods)} busy periods, flow_size_threshold: {flow_size_threshold}, n_flows_unique: {len(busy_periods_unique)} , n_flows_per_period_est: {np.min(busy_periods_len)}, {np.mean(busy_periods_len)}, {np.max(busy_periods_len)}"
    )
    return busy_periods, busy_periods_duration, remainsizes, remainsizes_num


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
    parser.add_argument(
        "--shard_cc", dest="shard_cc", type=int, default=0, help="random seed"
    )
    parser.add_argument(
        "-t",
        dest="type",
        action="store",
        type=int,
        default=0,
        help="0: normal, 1: incast, 2: all",
    )
    parser.add_argument(
        "--enable_tr",
        dest="enable_tr",
        action="store",
        type=int,
        default=0,
        help="enable tracing",
    )
    parser.add_argument(
        "--output_dir",
        dest="output_dir",
        action="store",
        default="data/input",
        help="the name of the flow file",
    )
    parser.add_argument(
        "--max_inflight_flows",
        dest="max_inflight_flows",
        type=int,
        default=0,
        help="max inflgiht flows for close-loop traffic",
    )
    parser.add_argument(
        "--cc",
        dest="cc",
        action="store",
        default="hp",
        help="hp/dcqcn/timely/dctcp/hpccPint",
    )
    args = parser.parse_args()
    enable_tr = args.enable_tr
    flow_size_threshold_list = [100000000]

    fix_seed(args.shard)
    nhosts = 32
    time_limit = int(30000 * 1e9)
    shard_cc = args.shard_cc
    # max_inflight_flows = args.max_inflight_flows
    # config_specs = "_s%d_i%d" % (shard_cc, max_inflight_flows)
    config_specs = "_%s" % (args.cc)
    output_dir = args.output_dir
    file = "%s/fct_%s%s.txt" % (output_dir, args.prefix, config_specs)
    print(file)
    if not os.path.exists(file):
        exit(0)
    # flowId, sip, dip, sport, dport, size (B), start_time, fct (ns), standalone_fct (ns)
    cmd = (
        "cat %s" % (file)
        + " | awk '{if ($5==100 && $7+$8<"
        + "%d" % time_limit
        + ") {slow=$8/$9;print slow<1?$9:$8, $9, $6, $7, $2, $3, $1}}' | sort -n -k 4,4 -k 7,7"
    )
    # print cmd
    output = subprocess.check_output(cmd, shell=True)

    try:
        output = output.decode()
        a = output[:-1].split("\n")
        n = len(a)
        res_np = np.array([x.split() for x in a])
        print(res_np.shape)
        # for i in range(n):
        # 	print "%s %s %s %s %s %s"%(res_np[i,0], res_np[i,1], res_np[i,2], res_np[i,3], res_np[i,4], res_np[i,5])
        fcts = res_np[:, 0].astype("int64")
        i_fcts = res_np[:, 1].astype("int64")
        fsize = res_np[:, 2].astype("int64")
        fat = res_np[:, 3].astype("int64")
        fid = res_np[:, 6].astype("int64")
        if nhosts == 21:
            util = np.sum(fsize) / (np.max(fat + fcts) - np.min(fat)) * 8 / 10
            print(f"util: {util}")
            n_inflight_flows_mean = np.sum(fcts - 2000) / (
                np.max(fat + fcts) - np.min(fat)
            )
            print(f"n_inflight_flows_mean: {n_inflight_flows_mean}")
        np.save(
            "%s/fct_%s%s.npy" % (output_dir, args.prefix, config_specs), fcts
        )  # Byte
        np.save(
            "%s/fct_i_%s%s.npy" % (output_dir, args.prefix, config_specs),
            i_fcts,
        )  # ns
        np.save("%s/fid_%s%s.npy" % (output_dir, args.prefix, config_specs), fid)
        np.save("%s/fat_%s%s.npy" % (output_dir, args.prefix, config_specs), fat)
        exit(0)
        # src_arr = np.array(lambda x: x[-3].split(), res_np[:, 4]).astype("int32")
        # dst_arr = np.array(lambda x: x[-3].split(), res_np[:, 5]).astype("int32")
        # fsd = np.concatenate((src_arr, dst_arr), axis=1)
        # print(f"fsd: {fsd.shape}")
        # np.save("%s/fsd_%s%s.npy" % (output_dir, args.prefix, config_specs), fsd)
        # with open("%s/fsd_%s%s.txt"% (output_dir, args.prefix, config_specs), "w") as file:
        #     for i in range(fsd.shape[0]):
        #         file.write(" ".join(map(str, fsd[i])) + "\n")

        tr_path = "%s/mix_%s%s.tr" % (output_dir, args.prefix, config_specs)
        # if enable_tr:
        #     # Read and parse the log file
        #     log_path = tr_path.replace(".tr", ".log")

        #     if not os.path.exists(log_path):
        #         os.system(f"{cur_dir}/trace_reader {tr_path} > {log_path}")

        #     if output_type == OutputType.PER_FLOW_QUEUE:
        #         queue_lengths = calculate_queue_lengths(log_path)

        #         with open(
        #             "%s/qfeat_%s%s.txt" % (output_dir, args.prefix, config_specs), "w"
        #         ) as file:
        #             for (
        #                 flowid,
        #                 timestamp,
        #                 queue_len,
        #                 queue_event,
        #                 n_active_flows,
        #             ) in queue_lengths:
        #                 file.write(
        #                     f"{flowid} {timestamp} {queue_len} {queue_event} {n_active_flows}\n"
        #                 )
        #         print(queue_lengths.shape)
        #         np.save(
        #             "%s/qfeat_%s%s.npy" % (output_dir, args.prefix, config_specs),
        #             queue_lengths,
        #         )
        #     elif output_type == OutputType.BUSY_PERIOD:
        #         flow_id_per_period_est = calculate_busy_period(log_path)
        #         np.save(
        #             "%s/period_%s%s.npy" % (output_dir, args.prefix, config_specs),
        #             flow_id_per_period_est,
        #         )
        # with open("%s/period_%s%s.txt" % (output_dir, args.prefix, config_specs), "w") as file:
        #     for period in flow_id_per_period_est:
        #         file.write(" ".join(map(str, period)) + "\n")

        # os.system(
        #     "rm %s" % ("%s/mix_%s%s.log" % (output_dir, args.prefix, config_specs))
        # )

        # Read and parse the log file
        log_path = tr_path.replace(".tr", ".log")

        if not os.path.exists(log_path):
            os.system(f"{cur_dir}/trace_reader {tr_path} > {log_path}")
        if os.path.exists(log_path):
            remainsize_list = []
            with open(log_path, "r") as file:
                # Read the file line by line
                for line in file:
                    # Strip leading/trailing whitespace characters (like newline)
                    line = line.strip().rstrip(",").split(",")
                    # Print each line
                    if len(line[0]) > 1:
                        line_dict = {}
                        for i in range(len(line)):
                            tmp = line[i].split(":")
                            line_dict[int(tmp[0])] = int(tmp[1])
                        remainsize_list.append(line_dict)
                    else:
                        remainsize_list.append([0])

        for flow_size_threshold in flow_size_threshold_list:
            if nhosts == 21:
                (
                    busy_periods,
                    busy_periods_time,
                    busy_periods_remainsize,
                    remainsizes_num,
                ) = calculate_busy_period_link(
                    fat,
                    fcts,
                    fid,
                    fsize,
                    flow_size_threshold,
                    remainsize_list,
                )
            else:
                fsd = np.load("%s/fsd.npy" % (output_dir))
                fsd = fsd[fid]
                print(f"fsd: {fsd.shape}")
                (
                    busy_periods,
                    busy_periods_time,
                    busy_periods_remainsize,
                    remainsizes_num,
                ) = calculate_busy_period_path(
                    fat,
                    fcts,
                    fid,
                    fsd,
                    fsize,
                    nhosts,
                    flow_size_threshold,
                    remainsize_list,
                )
            busy_periods = np.array(busy_periods, dtype=object)
            np.save(
                "%s/period_%s%s_t%d.npy"
                % (output_dir, args.prefix, config_specs, flow_size_threshold),
                busy_periods,
            )
            np.save(
                "%s/period_time_%s%s_t%d.npy"
                % (output_dir, args.prefix, config_specs, flow_size_threshold),
                np.array(busy_periods_time),
            )
            busy_periods_remainsize = np.array(busy_periods_remainsize, dtype=object)
            np.save(
                "%s/period_remainsize_%s%s_t%d.npy"
                % (output_dir, args.prefix, config_specs, flow_size_threshold),
                np.array(busy_periods_remainsize),
            )
            np.save(
                "%s/period_remainsize_num_%s%s_t%d.npy"
                % (output_dir, args.prefix, config_specs, flow_size_threshold),
                np.array(remainsizes_num),
            )
            # with open("%s/period_%s%s.txt" % (output_dir, args.prefix, config_specs), "w") as file:
            #     for period in flow_id_per_period_est:
            #         file.write(" ".join(map(str, period)) + "\n")
        if os.path.exists(tr_path):
            os.system("rm %s" % tr_path)
        if os.path.exists(log_path):
            os.system("rm %s" % log_path)

        # os.system("rm %s" % (file))

        # if os.path.exists("%s/flows.txt"% (output_dir)):
        #     os.system("rm %s/flows.txt" % (output_dir))

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
    except Exception as e:
        print(output_dir, args.prefix, config_specs, e)
        traceback.print_exc()
        pass
