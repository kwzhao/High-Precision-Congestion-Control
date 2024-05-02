cargo run --release

python run.py --root /data1/lichenni/projects/flow_simulation/parsimon-eval/expts/fig_8/data/25/ns3 --cc dctcp --trace flows --bw 10 --topo topology --fwin 18000 --base_rtt 14400

python2 run.py --root mix --cc dctcp --trace flow_parsimon --bw 10 --topo fat_parsimon

/data1/lichenni/software/anaconda3/envs/py27/bin/python /data1/lichenni/projects/flow_simulation/parsimon/backends/High-Precision-Congestion-Control/simulation/run_m3.py --cc hp --trace flows --bw 10 --fwin 18000 --base_rtt 14400 --topo topo-pl-7 --root /data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps --hpai 50

CC='gcc-5' CXX='g++-5' ./waf configure --build-profile=optimized

CC='gcc-5' CXX='g++-5' ./waf configure --build-profile=debug --out=build/debug

export NS_LOG=PacketPathExample=info

./waf --run 'scratch/third mix_7/config_topo-pl-7_flows_dctcp_k30.txt'
./waf -d debug -out=debug.txt --run 'scratch/test'
./waf --run 'scratch/third /data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps/config_topo-pl-7_flows_hp_k18000.txt'

./waf --run 'scratch/third /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt' --command-template="gdb"

/data2/lichenni/path_tc/shard0_nflows20_nhosts7_lr10Gbps/config_topo-pl-7_flows_hp_k18000.txt

https://github.com/kwzhao/High-Precision-Congestion-Control/compare/9f4be2a9ead8a90e8bf732c66bd758c00e58e5be...13958423c9b7e666b8b51bdb889816ec3f52d79a

https://github.com/kwzhao/High-Precision-Congestion-Control/compare/13958423c9b7e666b8b51bdb889816ec3f52d79a...a69f1a6d8157fb70190db6dd74ee8cdeb90425b5

# parse the result, which can be used to calcualte the flow rate, queue length, etc.
./trace_reader /data2/lichenni/path_tc_test/shard0_nflows2000_nhosts3_lr10Gbps/mix_topo-pl-3_s0.tr > /data2/lichenni/path_tc_test/shard0_nflows2000_nhosts3_lr10Gbps/tr_s0.log

# parse qlen.txt
3 3 859528 2021 2259 4300 2682 1888 27959 39265 11275 2668 2599 2753 2742 15486 16367 6119 90
3 3: The first two numbers indicate the switch ID and the port ID, respectively. In this case, both the switch ID and the port ID are 3, which means this entry is for port 3 on switch 3.

859528: This number represents the total queue length in bytes at the moment of logging for port 3 on switch 3. This is the sum of the queue lengths across all priority queues within the port.

2021 2259 4300 2682 1888 27959 39265 11275 2668 2599 2753 2742 15486 16367 6119 90: The series of numbers following the total queue length are the counts of occurrences where the queue length fell within certain ranges, as managed by the QlenDistribution class. Each number corresponds to a specific "bucket" or range of queue lengths, measured in kilobytes (KB), indicating how often the queue length was observed to be within that range during the monitoring period.

The first number (2021) could represent the count of times the queue length was within the range of 0-1 KB,
The second number (2259) could represent the count of times the queue length was within the range of 1-2 KB,
And so on, with each subsequent number representing the count of times the queue length fell within progressively higher KB ranges.


CXXFLAGS=-w ./ns3 configure --build-profile=optimized

gdb --args ./waf --run 'scratch/third /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt'

gdb --args build/scratch/ns3.39-third-debug /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt

debug

./ns3 run 'scratch/third /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt' --gdb

run


./ns3 run 'scratch/third /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt' > test.log 2> test.log

NS_LOG="Ipv4EndPointDemux" ./ns3 run 'scratch/third /data2/lichenni/path_tc_cc/shard1_nflows1_nhosts3/config_topo-pl-3-1-1000_flows_s0.txt' > test.log 2> test.log

python run_cc.py --trace flows --base_rtt 14400 --topo topo-pl-3 --root /data2/lichenni/path_cc_test/shard0_nflows1000_nhosts3 --shard_cc 0 --shard_total 0 --enable_tr 1 --enable_debug 0 --bw 1 --pd 1000

python ../analysis/fct_to_file_cc.py --shard 0 -p topo-pl-3-1-1000 --output_dir /data2/lichenni/path_cc_test --scenario_dir shard0_nflows1000_nhosts3 --shard_cc 0 --enable_debug 0

