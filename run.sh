cargo run --release

python run.py --root /data1/lichenni/projects/flow_simulation/parsimon-eval/expts/fig_8/data/25/ns3 --cc dctcp --trace flows --bw 10 --topo topology --fwin 18000 --base_rtt 14400

python2 run.py --root mix --cc dctcp --trace flow_parsimon --bw 10 --topo fat_parsimon

/data1/lichenni/software/anaconda3/envs/py27/bin/python /data1/lichenni/projects/flow_simulation/parsimon/backends/High-Precision-Congestion-Control/simulation/run_by_n.py --cc hp --trace flows --bw 10 --fwin 18000 --base_rtt 14400 --topo topo-pl-7 --root /data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps --hpai 50

CC='gcc-5' CXX='g++-5' ./waf configure --build-profile=optimized

CC='gcc-5' CXX='g++-5' ./waf configure --build-profile=debug --out=build/debug

export NS_LOG=PacketPathExample=info

./waf --run 'scratch/third mix_7/config_topo-pl-7_flows_dctcp_k30.txt'
./waf -d debug -out=debug.txt --run 'scratch/test'
./waf --run 'scratch/third /data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps/config_topo-pl-7_flows_hp_k18000.txt'

./waf --run 'scratch/third /data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps/config_topo-pl-7_flows_hp_k18000.txt' --command-template="gdb"

/data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps/config_topo-pl-7_flows_hp_k18000.txt

https://github.com/kwzhao/High-Precision-Congestion-Control/compare/9f4be2a9ead8a90e8bf732c66bd758c00e58e5be...13958423c9b7e666b8b51bdb889816ec3f52d79a

https://github.com/kwzhao/High-Precision-Congestion-Control/compare/13958423c9b7e666b8b51bdb889816ec3f52d79a...a69f1a6d8157fb70190db6dd74ee8cdeb90425b5



I think you can capture the packet trace, and then calculate the throughput yourself. That's what I did :)

To capture packet trace, you can check https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/simulation/run.py#L76
With this option set, the simulation also output a trace file to: https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/simulation/run.py#L13

Then you can use https://github.com/alibaba-edu/High-Precision-Congestion-Control/blob/master/analysis/trace_reader.cpp to read the trace file.

Please do the `make trace_reader` under analysis/