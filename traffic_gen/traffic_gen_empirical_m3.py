import sys
import random
import math
import heapq
from argparse import ArgumentParser
import numpy as np
import os
from consts import (
    BYTE_TO_BIT,
    UNIT_G,
    ia_distribution,
    ias_sigma_range,
    load_range,
    load_bottleneck_range,
)
from custom_rand import CustomRand

dir_path_cur = os.path.dirname(os.path.realpath(__file__)) + "/"

size_distribution_list = ["cachefollower-all", "hadoop-all", "webserver-all"]
min_size_in_byte = 50


def fix_seed(seed):
    np.random.seed(seed)
    random.seed(seed)


class Flow:
    def __init__(self, src, dst, size, t):
        self.src, self.dst, self.size, self.t = src, dst, size, t

    def __str__(self):
        return "%d %d 3 100 %d %.9f" % (self.src, self.dst, self.size, self.t)


def translate_bandwidth(b):
    if b == None:
        return None
    if type(b) != str:
        return None
    if b[-1] == "G":
        return float(b[:-1]) * 1e9
    if b[-1] == "M":
        return float(b[:-1]) * 1e6
    if b[-1] == "K":
        return float(b[:-1]) * 1e3
    return float(b)


def poisson(lam):
    return -math.log(1 - random.random()) * lam


def PosNormal(mean, sigma):
    x = np.random.normal(mean, sigma, 1)
    return x if x >= 0 else PosNormal(mean, sigma)


if __name__ == "__main__":
    payload_size = 1000
    parser = ArgumentParser()
    parser.add_argument(
        "--shard", dest="shard", type=int, default=0, help="random seed"
    )
    parser.add_argument(
        "--switchtohost",
        dest="switch_to_host",
        type=int,
        default=4,
        help="the ratio of switch-to-switch link to host-to-switch link",
    )
    parser.add_argument(
        "-f",
        "--nflows",
        dest="nflows",
        help="the total number of flows, by default 10000",
        default="10000",
    )
    parser.add_argument("-n", "--nhost", dest="nhost", help="number of hosts")
    parser.add_argument(
        "-b",
        "--bandwidth",
        dest="bandwidth",
        help="the bandwidth of host link (G/M/K), by default 10G",
        default="10G",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="the output file",
        default="../simulation/mix/",
    )
    parser.add_argument(
        "--constfsize",
        dest="constfsize",
        type=int,
        default=0,
        help="the flow size for constant size distribution in bytes",
    )
    options = parser.parse_args()

    fix_seed(options.shard)

    base_t = 1 * UNIT_G

    if not options.nhost:
        print("please use -n to enter number of hosts")
        sys.exit(0)
    n_flows = int(options.nflows)
    nhost = int(options.nhost)
    switch_to_host = int(options.switch_to_host)
    bandwidth_base = translate_bandwidth(options.bandwidth)
    if bandwidth_base == None:
        print("bandwidth format incorrect")
        sys.exit(0)
    bandwidth_list_scale = []
    if nhost == 21:
        bandwidth_list_scale = [1] * (nhost)
    else:
        for link_id in range(nhost - 1):
            if link_id == 0 or link_id == nhost - 2:
                bandwidth_list_scale.append(1)
            else:
                bandwidth_list_scale.append(switch_to_host)

    output_dir = options.output
    if not os.path.exists("%s/flows.txt" % (output_dir)):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # generate flows
        bandwidth_list = []
        host_pair_list_ori = []
        host_pair_to_link_dict = {}
        if nhost == 21:
            for link_id in range(nhost):
                bandwidth_list.append(bandwidth_list_scale[link_id] * bandwidth_base)
            for i in range(nhost - 1):
                src_dst_pair = (i, nhost - 1)
                host_pair_list_ori.append(src_dst_pair)
                host_pair_to_link_dict[src_dst_pair] = []
                host_pair_to_link_dict[src_dst_pair].append(i)
                host_pair_to_link_dict[src_dst_pair].append(nhost - 1)
        else:
            for link_id in range(nhost - 1):
                bandwidth_list.append(bandwidth_list_scale[link_id] * bandwidth_base)
            for i in range(nhost - 1):
                for j in range(i + 1, nhost):
                    src_dst_pair = (i, j)
                    # if (j-i)!=nhost-1:
                    host_pair_list_ori.append(src_dst_pair)
                    host_pair_to_link_dict[src_dst_pair] = []
                    for link_id in range(i, j):
                        host_pair_to_link_dict[src_dst_pair].append(link_id)
        # host_pair_list=[(0,nhost-1)]
        host_pair_list = []
        if nhost == 2:
            ntc = 1
        elif nhost == 21:
            ntc = 20
            host_pair_idx_list = [(i, nhost - 1) for i in range(0, nhost - 1)]
            host_pair_list += host_pair_idx_list
        else:
            ntc = random.randint(2, nhost * (nhost - 1) // 2)
            host_pair_idx_list = np.random.choice(
                len(host_pair_list_ori), size=ntc, replace=False
            )
            host_pair_list += [host_pair_list_ori[i] for i in host_pair_idx_list]

        assert len(host_pair_list) == ntc
        print("lr: ", bandwidth_list, "ntc: ", ntc, "host_pair_list: ", host_pair_list)

        host_list = []
        for i in range(ntc):
            host_list.append((base_t, i))
        heapq.heapify(host_list)

        n_flows_tmp = n_flows * ntc + 1
        # n_flows_tmp=np.random.randint(10, n_flows + 1)*ntc+1

        customRand_dict = {}
        for cdf_file_name in size_distribution_list:
            fileName = dir_path_cur + cdf_file_name + ".txt"
            file = open(fileName, "r")
            lines = file.readlines()
            cdf = []
            for line in lines:
                x, y = map(float, line.strip().split(" "))
                cdf.append([x, y])
            customRand = CustomRand()
            if not customRand.setCdf(cdf):
                print("Error: Not valid cdf")
                sys.exit(0)
            customRand_dict[cdf_file_name] = customRand

        size_dist_candidate = np.random.choice(
            size_distribution_list, size=1, replace=True
        )[0]
        ias_sigma_candidate = (
            np.random.rand() * (ias_sigma_range[1] - ias_sigma_range[0])
            + ias_sigma_range[0]
        )

        load_candidate = (
            np.random.rand() * (load_range[1] - load_range[0]) + load_range[0]
        )
        load_bottleneck_target = (
            np.random.rand() * (load_bottleneck_range[1] - load_bottleneck_range[0])
            + load_bottleneck_range[0]
        )

        load_per_link = {}
        if nhost == 21:
            for i in range(nhost):
                load_per_link[i] = 0
        else:
            for i in range(nhost - 1):
                load_per_link[i] = 0
        for i in range(ntc):
            load_tmp = load_candidate
            src_dst_pair = host_pair_list[i]

            for link_id in host_pair_to_link_dict[src_dst_pair]:
                load_per_link[link_id] += load_tmp / bandwidth_list_scale[link_id]
        tmp = list(load_per_link.values())
        load_bottleneck_cur = np.max(tmp)
        load_bottleneck_link_id = tmp.index(load_bottleneck_cur)
        load_candidate = load_candidate * load_bottleneck_target / load_bottleneck_cur

        customRand_tmp = customRand_dict[size_dist_candidate]

        f_sizes_in_byte = np.array(
            [customRand_tmp.rand() for _ in range(n_flows_tmp)]
        ).astype("int64")

        avg_in_byte = np.mean(f_sizes_in_byte)

        if ia_distribution == "lognorm":
            avg_inter_arrival_in_s = (
                1
                / (
                    bandwidth_list[load_bottleneck_link_id]
                    * load_candidate
                    / 8.0
                    / avg_in_byte
                )
                / ntc
            )
            arr_sigma = ias_sigma_candidate
            mu = np.log(avg_inter_arrival_in_s) - (arr_sigma**2) / 2
            f_arr_in_ns = (
                np.random.lognormal(mean=mu, sigma=arr_sigma, size=(n_flows_tmp - 1,))
                * UNIT_G
            ).astype("int64")
        elif ia_distribution == "exp":
            avg_inter_arrival_in_s = (
                1
                / (
                    bandwidth_list[load_bottleneck_link_id]
                    * load_candidate
                    / 8.0
                    / avg_in_byte
                )
                / ntc
            )
            f_arr_in_ns = (
                np.random.exponential(
                    scale=avg_inter_arrival_in_s, size=(n_flows_tmp - 1,)
                )
                * UNIT_G
            ).astype("int64")

        flow_src_dst_save = []
        f_arr_in_ns_save = []
        f_sizes_in_byte_save = []
        data = ""
        flow_id_total = 0
        t = base_t
        host_pair_list_idx = np.arange(len(host_pair_list))
        p_candidate_list = [ntc, 10, 20, 50, 100]
        p_candidate = np.random.choice(p_candidate_list, size=1, replace=False)[0]
        p_list = np.random.rand(ntc) * p_candidate / ntc
        p_list[0] = 1.0

        p_list = np.array(p_list) / np.sum(p_list)
        n_flows_foreground = 0
        while flow_id_total < n_flows_tmp - 1:
            # host_pair_idx=np.random.choice(host_pair_list_idx,p=p_list)
            host_pair_idx = np.random.choice(host_pair_list_idx)
            if host_pair_idx == 0:
                n_flows_foreground += 1
            src, dst = host_pair_list[host_pair_idx]
            size = f_sizes_in_byte[flow_id_total]
            if size < min_size_in_byte:
                size = min_size_in_byte
            if size % payload_size == 0:
                size -= 1
            data += "%d %d %d 3 100 %d %.9f\n" % (
                flow_id_total,
                src,
                dst,
                size,
                t * 1e-9,
            )

            flow_src_dst_save.append([src, dst])
            f_arr_in_ns_save.append(t)
            f_sizes_in_byte_save.append(size)

            inter_t = f_arr_in_ns[flow_id_total]
            t += inter_t
            flow_id_total += 1
        n_flows_total = flow_id_total
        t += 20 * UNIT_G
        data += "%f" % ((t) / 1e9)
        data = "{}{}".format("%d\n" % n_flows_total, data)
        ofile = open("%s/flows.txt" % (output_dir), "w")
        ofile.write(data)
        ofile.close()

        n_flows_done = min(n_flows_total, n_flows_tmp - 1)
        end_time = float(np.sum(f_arr_in_ns[:n_flows_done])) / UNIT_G
        utilization = (
            np.sum(f_sizes_in_byte[:n_flows_done])
            * BYTE_TO_BIT
            / end_time
            / bandwidth_list[load_bottleneck_link_id]
        )
        print("utilization: ", np.round(utilization, 3), np.round(load_candidate, 3))
        print("load_candidate:", load_bottleneck_target, load_candidate)
        print(
            "stats:",
            n_flows_total,
            p_list[0],
            n_flows_foreground,
            size_dist_candidate,
            ias_sigma_candidate,
            end_time,
        )
        stats = {
            "n_flows": n_flows_total,
            "ratio": p_list[0],
            "n_flows_foreground": n_flows_foreground,
            "load_bottleneck_target": load_bottleneck_target,
            "host_pair_list": host_pair_list,
            "load_candidate": load_candidate,
            "size_dist_candidate": size_dist_candidate,
            "ias_sigma_candidate": ias_sigma_candidate,
        }
        np.save("%s/stats.npy" % (output_dir), stats)  # Byte

        flow_src_dst = np.array(flow_src_dst_save).astype("int32")
        f_arr_in_ns = np.array(f_arr_in_ns_save).astype("int64")
        f_sizes_in_byte = np.array(f_sizes_in_byte_save).astype("int64")
        np.save("%s/fsize.npy" % (output_dir), f_sizes_in_byte)  # Byte
        np.save("%s/fat.npy" % (output_dir), f_arr_in_ns)  # ns
        np.save("%s/fsd.npy" % (output_dir), flow_src_dst)