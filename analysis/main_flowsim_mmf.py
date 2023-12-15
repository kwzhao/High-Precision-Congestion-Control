# weighted_genpar_flowsim.py
import numpy as np
from ctypes import *

from time import time
import argparse
import os

MTU = 1000
HEADER_SIZE = 48
DELAY_PROPAGATION_BASE = 1000
BYTE_TO_BIT = 8
UNIT_G = 1000000000


class FCTStruct(Structure):
    _fields_ = [
        ("estimated_fcts", POINTER(c_double)),
        ("t_flows", POINTER(c_double)),
        ("num_flows", POINTER(c_uint)),
        ("num_flows_enq", POINTER(c_uint)),
    ]


def make_array(ctype, arr):
    return (ctype * len(arr))(*arr)


C_LIB_PATH = "/data1/lichenni/projects/flow_simulation/fast-mmf-fattree/get_fct_mmf.so"

C_LIB = CDLL(C_LIB_PATH)
C_LIB.get_fct_mmf = C_LIB.get_fct_mmf
C_LIB.get_fct_mmf.argtypes = [
    c_uint,
    POINTER(c_double),
    POINTER(c_double),
    POINTER(c_int),
    POINTER(c_int),
    c_int,
    POINTER(c_int),
    c_int,
    c_int,
    c_int,
    c_int,
]
C_LIB.get_fct_mmf.restype = FCTStruct

C_LIB.free_fctstruct = C_LIB.free_fctstruct
C_LIB.free_fctstruct.argtypes = [FCTStruct]
C_LIB.free_fctstruct.restype = None


def fix_seed(seed):
    np.random.seed(seed)


parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-p",
    dest="prefix",
    action="store",
    default="topo4-4_traffic",
    help="Specify the prefix of the fct file. Usually like fct_<topology>_<trace>",
)
parser.add_argument("-s", dest="step", action="store", default="5")
parser.add_argument("--shard", dest="shard", type=int, default=0, help="random seed")
parser.add_argument(
    "-t",
    dest="type",
    action="store",
    type=int,
    default=0,
    help="0: normal, 1: incast, 2: all",
)
# parser.add_argument('-T', dest='time_limit', action='store', type=int, default=20000000000, help="only consider flows that finish before T")
parser.add_argument("--cc", dest="cc", action="store", default="dctcp", help="")
parser.add_argument(
    "--nhost", dest="nhost", type=int, default=6, help="number of hosts"
)
parser.add_argument(
    "-b",
    dest="bw",
    action="store",
    type=int,
    default=10,
    help="bandwidth of edge link (Gbps)",
)
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

fix_seed(args.shard)

dir_input = "%s/%s" % (args.output_dir, args.scenario_dir)

nhost = int(args.nhost)
bw = int(args.bw)
output_dir = dir_input
# output_dir = "/data1/lichenni/projects/flow_simulation/High-Precision-Congestion-Control/gc"
# os.makedirs(output_dir, exist_ok=True)

if not os.path.exists("%s/fcts_flowsim.npy" % output_dir) and os.path.exists(
    "%s/flow_sizes.npy" % output_dir
):
    sizes = np.load("%s/flow_sizes.npy" % (dir_input))
    fats = np.load("%s/flow_arrival_times.npy" % (dir_input))
    flow_src_dst = np.load("%s/flow_src_dst.npy" % (dir_input))

    n_flows = len(sizes)

    start = time()
    fats_pt = make_array(c_double, fats)
    sizes_pt = make_array(c_double, sizes)
    # n_links_passed = abs(flow_src_dst[:, 0] - flow_src_dst[:, 1]) + 2
    # pkt_head = np.clip(sizes, a_min=0, a_max=MTU)
    # pkt_rest = sizes - pkt_head
    # size_byte = (
    #     (pkt_head + HEADER_SIZE) * n_links_passed
    #     + (pkt_rest + np.ceil(pkt_rest / MTU) * HEADER_SIZE)
    # ).astype("int64")
    # sizes_pt = make_array(c_double, size_byte)
    src_pt = make_array(c_int, flow_src_dst[:, 0])
    dst_pt = make_array(c_int, flow_src_dst[:, 1])
    # topo_pt=make_array(c_int, np.array([2,2,1,2,1,1]))
    topo_pt = make_array(c_int, np.array([1, 4]))
    res = C_LIB.get_fct_mmf(
        n_flows, fats_pt, sizes_pt, src_pt, dst_pt, nhost, topo_pt, 2, 8, 2, bw
    )

    estimated_fcts = np.fromiter(res.estimated_fcts, dtype=np.float64, count=n_flows)

    # t_flows = np.fromiter(res.t_flows, dtype=np.float64, count=2 * n_flows)
    # num_flows = np.fromiter(res.num_flows, dtype=np.uint, count=2 * n_flows).astype(
    # np.int64
    # )
    # num_flows_enq = np.fromiter(res.num_flows_enq, dtype=np.uint, count=n_flows).astype(
    #     np.int64
    # )
    end = time()
    print("c_sim:%f" % (end - start))
    print("estimated_fcts:%f" % (np.mean(estimated_fcts)))
    # print(f"t_flows-{len(t_flows)}: {np.mean(t_flows)}")
    # print(f"num_flows-{len(num_flows)}: {np.mean(num_flows)}")
    # print(f"num_flows_enq-{len(num_flows_enq)}: {np.mean(num_flows_enq)}")

    np.save("%s/fcts_flowsim.npy" % output_dir, estimated_fcts)
    # os.system("rm %s/flows.txt" % (output_dir))
    # np.save(f"{output_dir}/t_flows_flowsim.npy", np.array(t_flows))
    # np.save(f"{output_dir}/num_flows_flowsim.npy", np.array(num_flows))
    # np.save(f"{output_dir}/num_flows_enq_flowsim.npy", num_flows_enq)
    C_LIB.free_fctstruct(res)
