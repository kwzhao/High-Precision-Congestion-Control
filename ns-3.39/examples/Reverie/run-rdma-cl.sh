source config.sh
DIR=$(pwd)
DUMP_DIR=$DIR/dump_sigcomm
RESULTS_DIR=$DIR/results_sigcomm

if [ ! -d "$DUMP_DIR" ];then
	mkdir $DUMP_DIR
fi
if [ ! -d "$RESULTS_DIR" ];then
	mkdir $RESULTS_DIR
fi

cd $NS3

LOSSLESS=0
LOSSY=1

DT=101
FAB=102
ABM=110
REVERIE=111

DCQCNCC=1
INTCC=3
TIMELYCC=7
PINTCC=10
CUBIC=2
DCTCP=4


NUM=0

# BUFFER_ALGS=($DT $FAB $ABM "reverie")
BUFFER_ALGS=($REVERIE)

BURST_SIZES=(500000)

LOADS=(0.4)

egresslossyFrac=0.8

gamma=0.999

START_TIME=1
END_TIME=1.02
FLOW_LAUNCH_END_TIME=1.01
BUFFER_PER_PORT_PER_GBPS=5.12 # in KiloBytes per port per Gbps
BUFFERSIZE=$(python3 -c "print(20*25*1000*$BUFFER_PER_PORT_PER_GBPS)") # in Bytes
ALPHAFILE=$DIR/alphas

EXP=$1

RDMAREQRATE=0
TCPREQRATE=2

############################################################################
###### Pure RDMA low load, across bursts with default DCQCN
rdmaload=0
tcpload=0.8
tcpburst=0
RDMACC=$DCQCNCC
TCPCC=$CUBIC
for rdmaburst in ${BURST_SIZES[@]};do
	if [[ $rdmaburst == 2000000 ]];then
		continue;
	fi
	for alg in ${BUFFER_ALGS[@]};do
		if [[ $alg != $REVERIE ]];then
			BUFFERMODEL="sonic"
		else
			BUFFERMODEL="reverie"
		fi
		while [[ $(ps aux | grep reverie-evaluation-sigcomm2023-optimized | wc -l) -gt $N_CORES ]];do
			sleep 30;
			echo "waiting for cores, $N_CORES running..."
		done
		FCTFILE=$DUMP_DIR/evaluation-$alg-$RDMACC-$TCPCC-$rdmaload-$tcpload-$rdmaburst-$tcpburst-$egresslossyFrac-$gamma.fct
		TORFILE=$DUMP_DIR/evaluation-$alg-$RDMACC-$TCPCC-$rdmaload-$tcpload-$rdmaburst-$tcpburst-$egresslossyFrac-$gamma.tor
		DUMPFILE=$DUMP_DIR/evaluation-$alg-$RDMACC-$TCPCC-$rdmaload-$tcpload-$rdmaburst-$tcpburst-$egresslossyFrac-$gamma.out
		PFCFILE=$DUMP_DIR/evaluation-$alg-$RDMACC-$TCPCC-$rdmaload-$tcpload-$rdmaburst-$tcpburst-$egresslossyFrac-$gamma.pfc
		echo $FCTFILE
		if [[ $EXP == 1 ]];then
			echo '(time ./waf --run "reverie-evaluation-sigcomm2023 --bufferalgIngress=$alg --bufferalgEgress=$alg --rdmacc=$RDMACC --rdmaload=$rdmaload --rdmarequestSize=$rdmaburst --rdmaqueryRequestRate=2 --tcpload=$tcpload --tcpcc=$TCPCC --enableEcn=true --tcpqueryRequestRate=1 --tcprequestSize=$tcpburst --egressLossyShare=$egresslossyFrac --bufferModel=$BUFFERMODEL --gamma=$gamma --START_TIME=$START_TIME --END_TIME=$END_TIME --FLOW_LAUNCH_END_TIME=$FLOW_LAUNCH_END_TIME --buffersize=$BUFFERSIZE --fctOutFile=$FCTFILE --torOutFile=$TORFILE --alphasFile=$ALPHAFILE --pfcOutFile=$PFCFILE" > $DUMPFILE 2> $DUMPFILE)'
			(time ./waf --run "reverie-evaluation-sigcomm2023 --bufferalgIngress=$alg --bufferalgEgress=$alg --rdmacc=$RDMACC --rdmaload=$rdmaload --rdmarequestSize=$rdmaburst --rdmaqueryRequestRate=$RDMAREQRATE --tcpload=$tcpload --tcpcc=$TCPCC --enableEcn=true --tcpqueryRequestRate=$TCPREQRATE --tcprequestSize=$tcpburst --egressLossyShare=$egresslossyFrac --bufferModel=$BUFFERMODEL --gamma=$gamma --START_TIME=$START_TIME --END_TIME=$END_TIME --FLOW_LAUNCH_END_TIME=$FLOW_LAUNCH_END_TIME --buffersize=$BUFFERSIZE --fctOutFile=$FCTFILE --torOutFile=$TORFILE --alphasFile=$ALPHAFILE --pfcOutFile=$PFCFILE" > $DUMPFILE 2> $DUMPFILE)&
			sleep 5
		fi
		NUM=$(( $NUM+1  ))
	done
done

echo "Total $NUM experiments"