#!/bin/bash
python2 /data1/zabreyko/polyphony-project/eval/crates/simulators/High-Precision-Congestion-Control/simulation/prepare_run.py --name $1 --root ${13} --cc dctcp --topo $3 --trace $2 --wint 1000000 <<EOF
3
$4
$5
$6
$7
$8
$9
${10}
${11}
${12}
EOF
