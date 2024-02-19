import subprocess
import argparse
import numpy as np
import os


def fix_seed(seed):
    np.random.seed(seed)


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
    # parser.add_argument(
    #     "--fwin", dest="fwin", type=int, default=30, help="fwin"
    # )
    # parser.add_argument('--cc_param_factor', dest='cc_param_factor', type=float, default=1.0, help="cc_param_factor")
    # parser.add_argument('--bfsz_factor', dest='bfsz_factor', action = 'store', type=float, default=1.0, help="buffer size factor")
    parser.add_argument(
        "-t",
        dest="type",
        action="store",
        type=int,
        default=0,
        help="0: normal, 1: incast, 2: all",
    )
    parser.add_argument('--enable_debug', dest='enable_debug', action = 'store', type=int, default=0, help="enable debug for parameter sample space")
    # parser.add_argument('-T', dest='time_limit', action='store', type=int, default=20000000000, help="only consider flows that finish before T")
    # parser.add_argument("--cc", dest="cc", action="store", default="dctcp", help="")
    parser.add_argument(
        "-b",
        dest="bw",
        action="store",
        type=int,
        default=25,
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
    enable_debug=args.enable_debug
    
    fix_seed(args.shard)
    type = args.type
    # time_limit = args.time_limit

    # Please list all the cc (together with parameters) that you want to compare.
    # For example, here we list two CC: 1. HPCC-PINT with utgt=95,AI=50Mbps,pint_log_base=1.05,pint_prob=1; 2. HPCC with utgt=95,ai=50Mbps.
    # For the exact naming, please check ../simulation/mix/fct_*.txt output by the simulation.
    # CCs = [
    # 	'hpccPint95ai50log1.05p1.000',
    # 	'hp95ai50',
    # ]
    # CCs = [
    # 	args.cc,
    # ]
    # time_limit = int(float(args.file.split("_")[-1])*1e9)
    time_limit = int(30000 * 1e9)
    # bfsz_factor = float(args.bfsz_factor)
    # cc_param_factor=float(args.cc_param_factor)
    shard_cc=args.shard_cc
    # step = int(args.step)
    # res = [[i/100.] for i in range(0, 100, step)]
    # fwin = args.fwin
    config_specs = "_s%d"%(shard_cc)
    output_dir = "%s/%s" % (args.output_dir, args.scenario_dir)
    # for cc in CCs:
    # file = "%s_%s.txt"%(args.prefix, cc)
    file = "%s/fct_%s%s.txt" % (output_dir, args.prefix, config_specs)
    # print file
    if type == 0:
        # cmd = "cat %s"%(file)+" | awk '{if ($4==100 && $6+$7<"+"%d"%time_limit+") {slow=$7/$8;print slow<1?1:slow, $5}}'"
        cmd = (
            "cat %s" % (file)
            + " | awk '{if ($5==100 && $7+$8<"
            + "%d" % time_limit
            + ") {slow=$8/$9;print slow<1?$9:$8, $9, $6, $7, $2, $3}}' | sort -n -k 4"
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
    # a = output.split('\n')[:-2]
    a = output.split("\n")[:-1]
    n = len(a)
    res_np = np.array(map(lambda x: x.split(), a))

    print(res_np.shape)
    # for i in range(n):
    # 	print "%s %s %s %s %s %s"%(res_np[i,0], res_np[i,1], res_np[i,2], res_np[i,3], res_np[i,4], res_np[i,5])
    fcts = res_np[:, 0].astype("int64")
    i_fcts = res_np[:, 1].astype("int64")
    flow_sizes = res_np[:, 2].astype("int64")
    flow_arrival_times = res_np[:, 3].astype("int64")
    np.save(
        "%s/fct_%s%s.npy" % (output_dir, args.prefix, config_specs), fcts
    )  # Byte
    np.save(
        "%s/fct_i_%s%s.npy" % (output_dir, args.prefix, config_specs),
        i_fcts,
    )  # ns
    
    np.save("%s/fsize_%s%s.npy" % (output_dir, args.prefix, config_specs), flow_sizes)  # Byte
    np.save("%s/fat_%s%s.npy" % (output_dir, args.prefix, config_specs), flow_arrival_times)  # ns
    src_arr = np.array(map(lambda x: x[-3].split(), res_np[:, 4])).astype("int32")
    dst_arr = np.array(map(lambda x: x[-3].split(), res_np[:, 5])).astype("int32")
    res_arr = np.concatenate((src_arr, dst_arr), axis=1)
    np.save("%s/fsd_%s%s.npy" % (output_dir, args.prefix, config_specs), res_arr)  # Byte

    # ofile = open("%s/trafficfile" % (output_dir), "w")
    # for i in range(n):
    #     ofile.write("%d %d\n" % (src_arr[i], dst_arr[i]))
    # ofile.write("-1 -1")
    # ofile.close()

    # os.system("rm %s/flows.txt" % (output_dir))
    if not enable_debug:
        os.system("rm %s" % (file))
        os.system(
            "rm %s"
            % ("%s/mix_%s%s.tr" % (output_dir, args.prefix,  config_specs))
        )
        os.system(
            "rm %s"
            % ("%s/pfc_%s%s.txt" % (output_dir, args.prefix,  config_specs))
        )
    
        os.system(
            "rm %s"
            % ("%s/qlen_%s%s.txt" % (output_dir, args.prefix, config_specs))
        )

    # ofile = open("%s/trafficfile_flow" % (output_dir), "w")
    # for i in range(n):
    #     ofile.write(
    #         "%d %d %d %d\n" % (fcts[i], i_fcts[i], flow_sizes[i], flow_arrival_times[i])
    #     )
    # ofile.write("-1 -1")
    # ofile.close()
