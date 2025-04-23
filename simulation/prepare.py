import json
from dataclasses import dataclass
import subprocess
import sys

@dataclass
class Flow(object):
    index: int
    pg: int
    src: int
    dst: int
    size: int
    start: int

def parse_file(file):
    with open(file, 'r') as f:
        data = json.load(f)

    classes = [10, 18, 26]
    weights = []
    cwnds = []
    dctcp_ks = []
    for cl in classes:
        weights.append(int(data["weights"][str(cl)] * 1024))
        cwnds.append(int(data["init_cwnds"][str(cl)]) * 1000)
        dctcp_ks.append(data["dctcp_ks"][str(cl)])

    max_dest = -1

    prefix = "/data1/zabreyko/polyphony-project/eval/crates/simulators/High-Precision-Congestion-Control/simulation"

    occurences = dict()
    occurences[10] = 0
    occurences[18] = 0
    occurences[26] = 0

    sizes = dict()
    sizes[10] = 0
    sizes[18] = 0
    sizes[26] = 0

    flows = list()
    for flow_obj in data["flows"]:
        index = flow_obj["id"]
        pg = flow_obj["qindex"]
        src = flow_obj["src"]
        dst = flow_obj["dst"]
        start = flow_obj["start"]
        size = flow_obj["size"]
        flow = Flow(index=index, pg=pg, src=src, dst=dst, size=size, start=start)
        flows.append(flow)
        max_dest = max(max_dest, dst)

        occurences[pg] += 1
        sizes[pg] += size

    print(occurences)
    print(sizes)

    file = file[file.rfind("/") + 1:file.rfind(".")]
    out_file = "{}/inputs/{}/{}".format(prefix, max_dest, file)
    with open(out_file, 'w') as f:
        content = "{}\n".format(len(flows))
        for flow in flows:
            #content += "{} {} {} {} {} {}\n".format(flow.index, classes.index(flow.pg) + 1, flow.src, flow.dst, flow.size, flow.start)
            content += "{} {} {} {} {} {} {}\n".format(flow.index, flow.src, flow.dst, classes.index(flow.pg) + 1, flow.index + 10, flow.size, flow.start / 1e9)
        f.write(content)

    if max_dest == 2:
        topo_file = "mix_m3/topo-pl-3.txt"
    elif max_dest == 4:
        topo_file = "mix_m3/topo-pl-5.txt"
    elif max_dest == 6:
        topo_file = "mix_m3/topo-pl-7.txt"
    else:
        a = 1 / 0

    name = "{}_{}".format(file, max_dest)
    arguments = ["{}/run.sh".format(prefix), name, out_file, "{}/{}".format(prefix, topo_file), weights[0], weights[1], weights[2], cwnds[0], cwnds[1], cwnds[2], dctcp_ks[0], dctcp_ks[1], dctcp_ks[2], prefix]
    for i in range(len(arguments)):
        arguments[i] = str(arguments[i])
    subprocess.run(arguments)



parse_file(sys.argv[1])
