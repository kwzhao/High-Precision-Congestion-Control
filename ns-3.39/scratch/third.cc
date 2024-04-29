/*
 * reverie-evaluation-sigcomm2023.cc
 *
 *  Created on: Feb 02, 2023
 *      Author: vamsi
 */

#include <iostream>
#include <fstream>
#include <unordered_map>
#include <time.h>
#include "ns3/core-module.h"
#include "ns3/qbb-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/global-route-manager.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/packet.h"
#include "ns3/error-model.h"
#include <ns3/rdma.h>
#include <ns3/rdma-client.h>
#include <ns3/rdma-client-helper.h>
#include <ns3/rdma-driver.h>
#include <ns3/switch-node.h>
#include <ns3/sim-setting.h>

#include <cmath>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <ctime>
#include <set>
#include <string>
#include <unordered_map>
#include <stdlib.h>
#include <unistd.h>
#include <vector>

using namespace ns3;
using namespace std;

#define LOSSLESS 0
#define LOSSY 1
#define DUMMY 2

# define DT 101
# define FAB 102
# define CS 103
# define IB 104
# define ABM 110
# define REVERIE 111

# define DCQCNCC 1
# define INTCC 3
# define TIMELYCC 7
# define PINTCC 10

// Define constants for TCP Congestion Controls
#define TCP_BBR 15
#define TCP_BIC 16
#define TCP_CUBIC 17
#define TCP_DCTCP 18
#define TCP_HIGH_SPEED 19
#define TCP_HTCP 20
#define TCP_HYBLA 21
#define TCP_ILLINOIS 22
#define TCP_LED_BAT 23
#define TCP_LP 24
#define TCP_SCALABLE 25
#define TCP_VEGAS 26
#define TCP_VENO 27
#define TCP_WESTWOOD 28
#define TCP_YEAH 29
#define TCP_NEW_RENO 30

#define PORT_NUMBER_START 4444
NS_LOG_COMPONENT_DEFINE("GENERIC_SIMULATION");

uint32_t cc_mode = 1;
bool enable_qcn = true,enable_pfc = true;
bool gen_tcp_traffic = true;
uint32_t packet_payload_size = 1000, l2_chunk_size = 0, l2_ack_interval = 0;
uint32_t ack_size = 59;
double pause_time = 5, simulator_stop_time = 3.01;
std::string data_rate, link_delay, topology_file, flow_file, trace_file, trace_output_file;
std::string fct_output_file = "fct.txt";
std::string pfc_output_file = "pfc.txt";

double alpha_resume_interval = 55, rp_timer, ewma_gain = 1 / 16;
double rate_decrease_interval = 4;
uint32_t fast_recovery_times = 5;
std::string rate_ai, rate_hai, min_rate = "100Mb/s";
std::string dctcp_rate_ai = "1000Mb/s";

bool clamp_target_rate = false, l2_back_to_zero = false;
double error_rate_per_link = 0.0;
uint32_t has_win = 1;
uint32_t global_t = 1;
uint32_t mi_thresh = 5;
bool var_win = false, fast_react = true;
bool multi_rate = true;
bool sample_feedback = false;
double pint_log_base = 1.05;
double pint_prob = 1.0;
double u_target = 0.95;
uint32_t int_multi = 1;
bool rate_bound = true;

uint32_t ack_high_prio = 0;
uint64_t link_down_time = 0;
uint32_t link_down_A = 0, link_down_B = 0;

uint32_t enable_trace = 1;

uint32_t buffer_size = 16;

uint32_t timely_t_high = 500000; //ns
uint32_t timely_t_low = 50000; //ns
double timely_beta = 0.8; //ns

uint32_t qlen_dump_interval = 100000000, qlen_mon_interval = 100;
uint64_t qlen_mon_start = 2000000000, qlen_mon_end = 2100000000;
string qlen_mon_file;

unordered_map<uint64_t, uint32_t> rate2kmax, rate2kmin;
unordered_map<uint64_t, double> rate2pmax;

double alpha_values[8] = {1, 1, 1, 1, 1, 1, 1, 1};
uint32_t PORT_START[512] = {4444};

/************************************************
 * Runtime varibles
 ***********************************************/
std::ifstream topof, flowf, tracef;

NodeContainer n;

uint64_t nic_rate;

uint64_t maxRtt, maxBdp;
uint64_t fwin;
uint64_t baseRtt;

struct Interface{
    uint32_t idx;
    bool up;
    uint64_t delay;
    uint64_t bw;

    Interface() : idx(0), up(false){}
};
map<Ptr<Node>, map<Ptr<Node>, Interface> > nbr2if;
// Mapping destination to next hop for each node: <node, <dest, <nexthop0, ...> > >
map<Ptr<Node>, map<Ptr<Node>, vector<Ptr<Node> > > > nextHop;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairDelay;
map<uint32_t, map<uint32_t, uint64_t> > pairBw;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairBdp;
map<uint32_t, map<uint32_t, uint64_t> > pairRtt;
map<uint32_t, map<uint32_t, vector<uint64_t>>> pairBws;
uint32_t log_time_interval = 10000; //ms

std::vector<Ipv4Address> serverAddress;

// maintain port number for each host pair
std::unordered_map<uint32_t, unordered_map<uint32_t, uint16_t> > portNumder;

struct FlowInput{
    uint32_t flowId, src, dst, pg, maxPacketCount, port, dport;
    double start_time;
    uint32_t idx;
};
FlowInput flow_input = {0};
uint32_t flow_num;

Ipv4Address node_id_to_ip(uint32_t id){
    return Ipv4Address(0x0b000001 + ((id / 256) * 0x00010000) + ((id % 256) * 0x00000100));
}

uint32_t ip_to_node_id(Ipv4Address ip){
    return (ip.Get() >> 8) & 0xffff;
}

void ReadFlowInput(){
    if (flow_input.idx < flow_num){
        flowf >> flow_input.flowId >> flow_input.src >> flow_input.dst >> flow_input.pg >> flow_input.dport >> flow_input.maxPacketCount >> flow_input.start_time;
        NS_ASSERT(n.Get(flow_input.src)->GetNodeType() == 0 && n.Get(flow_input.dst)->GetNodeType() == 0);
    }
}

void TraceMsgFinish (FILE* fout, double size_double, double start_double, bool incast, uint32_t prior, uint32_t flowId, InetSocketAddress sip_socket, InetSocketAddress dip_socket)
{
    // printf("flow %u finished\n", flowId);
    uint64_t start = static_cast<uint32_t>(start_double);
    uint64_t size = static_cast<uint32_t>(size_double);
    Ipv4Address sip = sip_socket.GetIpv4();
    Ipv4Address dip = dip_socket.GetIpv4();
    // std::cout << "Ipv4Address sip " << sip << ":" <<  sip_socket.GetPort() << ", dip " << dip << ":" <<  dip_socket.GetPort() << std::endl;
    uint32_t sid = ip_to_node_id(sip), did = ip_to_node_id(dip);
	uint64_t base_rtt = pairRtt[sid][did], b = pairBw[sid][did];
	uint64_t header = CustomHeader::GetStaticWholeHeaderSize() - IntHeader::GetStaticSize();
	uint64_t header_delay = header * 8000000000lu / b;
	uint64_t head = std::min((uint64_t) packet_payload_size, size);
	uint64_t rest = size - head;
	uint32_t rest_nr_packets = (size-1) / packet_payload_size;
	uint64_t tx_delay = 0;
	for (auto bw: pairBws[sid][did]) {
		tx_delay += ((head + header) * 8000000000lu / bw);
	}
	uint64_t rest_delay = rest * 8000000000lu / b + (rest_nr_packets * header_delay);
	uint64_t standalone_fct = (base_rtt / 2) + tx_delay + rest_delay;
	
	// flowId, sip, dip, sport, dport, size (B), start_time, fct (ns), standalone_fct (ns)
	fprintf(fout, "%u %08x %08x %u %u %lu %lu %lu %lu\n", flowId, sip.Get(), dip.Get(), sip_socket.GetPort() , dip_socket.GetPort(), size, start, Simulator::Now().GetNanoSeconds() - start, standalone_fct);
	fflush(fout);
}

void ScheduleFlowInputsTcp(FILE* fout){
    uint32_t prior = 1; // hardcoded for tcp
    while (flow_input.idx < flow_num){
        // printf("flow %u sent\n", flow_input.flowId);
        // uint16_t port = portNumder[flow_input.src][flow_input.dst]++; // get a new port number
        uint16_t port = PORT_START[flow_input.dst]++; // get a new port number
        if (port >= UINT16_MAX - 1) {
            port = PORT_NUMBER_START;
            PORT_START[flow_input.dst] = PORT_NUMBER_START;
        }

        Ptr<Node> rxNode = n.Get (flow_input.dst);
        Ptr<Ipv4> ipv4 = rxNode->GetObject<Ipv4> ();
        Ipv4InterfaceAddress rxInterface = ipv4->GetAddress (1, 0);
        Ipv4Address rxAddress = rxInterface.GetLocal ();
        // Ipv4Address rxAddress = serverAddress[flow_input.dst];
        // InetSocketAddress ad (rxAddress, flow_input.dport);
        InetSocketAddress ad (rxAddress, port);
        Address sinkAddress(ad);

        Ipv4Address txAddress = serverAddress[flow_input.src];
        InetSocketAddress adTx (txAddress, port);
        Address sinkAddressTx(adTx);

        // std::cout << "Ipv4Address sip " << txAddress << ":" << port << ", dip " << rxAddress << ":" << flow_input.dport << std::endl;

        Ptr<BulkSendApplication> bulksend = CreateObject<BulkSendApplication>();
        bulksend->SetAttribute("Protocol", TypeIdValue(TcpSocketFactory::GetTypeId()));
        bulksend->SetAttribute ("SendSize", UintegerValue (flow_input.maxPacketCount));
        bulksend->SetAttribute ("MaxBytes", UintegerValue(flow_input.maxPacketCount));
        bulksend->SetAttribute("FlowId", UintegerValue(flow_input.flowId));
        bulksend->SetAttribute("priorityCustom", UintegerValue(prior));
        bulksend->SetAttribute("Remote", AddressValue(sinkAddress));
        // bulksend->SetAttribute("Local", AddressValue(sinkAddressTx));
        bulksend->SetAttribute("InitialCwnd", UintegerValue (maxBdp/packet_payload_size + 1));
        bulksend->SetAttribute("priority", UintegerValue(prior));
        bulksend->SetStartTime (Seconds(flow_input.start_time));
        bulksend->SetStopTime (Seconds (simulator_stop_time));
        n.Get (flow_input.src)->AddApplication(bulksend);

        PacketSinkHelper sink ("ns3::TcpSocketFactory", InetSocketAddress (Ipv4Address::GetAny (), port));
        ApplicationContainer sinkApp = sink.Install (n.Get(flow_input.dst));
        sinkApp.Get(0)->SetAttribute("TotalQueryBytes", UintegerValue(flow_input.maxPacketCount));
        sinkApp.Get(0)->SetAttribute("LocalTag", AddressValue(sinkAddress));
        sinkApp.Get(0)->SetAttribute("priority", UintegerValue(0)); // ack packets are prioritized
        sinkApp.Get(0)->SetAttribute("priorityCustom", UintegerValue(0)); // ack packets are prioritized
        sinkApp.Get(0)->SetAttribute("flowId", UintegerValue(flow_input.flowId));
        sinkApp.Get(0)->SetAttribute("senderPriority", UintegerValue(prior));
        sinkApp.Start (Seconds(flow_input.start_time));
        sinkApp.Stop (Seconds (simulator_stop_time));
        sinkApp.Get(0)->TraceConnectWithoutContext("FlowFinish", MakeBoundCallback(&TraceMsgFinish, fout));

        // get the next flow input
        flow_input.idx++;
        ReadFlowInput();
    }
}

void ScheduleFlowInputs(){
    while (flow_input.idx < flow_num && Seconds(flow_input.start_time) == Simulator::Now()){
        uint32_t port = portNumder[flow_input.src][flow_input.dst]++; // get a new port number
        RdmaClientHelper clientHelper(flow_input.flowId, flow_input.pg, serverAddress[flow_input.src], serverAddress[flow_input.dst], port, flow_input.dport, flow_input.maxPacketCount, has_win?fwin:0, baseRtt);
        ApplicationContainer appCon = clientHelper.Install(n.Get(flow_input.src));
        appCon.Start(Seconds(0)); // setting the correct time here conflicts with Sim time since there is already a schedule event that triggered this function at desired time.
        // get the next flow input
        flow_input.idx++;
        ReadFlowInput();
    }

    // schedule the next time to run this function
    if (flow_input.idx < flow_num){
        Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
    }else { // no more flows, close the file
        flowf.close();
    }
}

void qp_finish(FILE* fout, Ptr<RdmaQueuePair> q){
    // remove rxQp from the receiver
    uint32_t sid = ip_to_node_id(q->sip), did = ip_to_node_id(q->dip);
    Ptr<Node> dstNode = n.Get(did);
    Ptr<RdmaDriver> rdma = dstNode->GetObject<RdmaDriver> ();
    rdma->m_rdma->DeleteRxQp(q->sip.Get(), q->m_pg, q->sport);
}

void qp_delivered(FILE* fout, Ptr<RdmaRxQueuePair> rxq){
	uint32_t sid = ip_to_node_id(Ipv4Address(rxq->dip));
	uint32_t did = ip_to_node_id(Ipv4Address(rxq->sip));
	Ptr<Node> srcNode = n.Get(sid);
	Ptr<RdmaDriver> rdma = srcNode->GetObject<RdmaDriver> ();
	Ptr<RdmaQueuePair> q = rdma->m_rdma->GetQp(rxq->sip, rxq->dport, rxq->pg);

	uint64_t base_rtt = pairRtt[sid][did], b = pairBw[sid][did];
	uint64_t header = CustomHeader::GetStaticWholeHeaderSize() - IntHeader::GetStaticSize();
	uint64_t header_delay = header * 8000000000lu / b;
	uint64_t head = std::min((uint64_t) packet_payload_size, q->m_size);
	uint64_t rest = q->m_size - head;
	uint32_t rest_nr_packets = (q->m_size-1) / packet_payload_size;
	uint64_t tx_delay = 0;
	for (auto bw: pairBws[sid][did]) {
		tx_delay += ((head + header) * 8000000000lu / bw);
	}
	uint64_t rest_delay = rest * 8000000000lu / b + (rest_nr_packets * header_delay);
	uint64_t standalone_fct = (base_rtt / 2) + tx_delay + rest_delay;
	
	// flowId, sip, dip, sport, dport, size (B), start_time, fct (ns), standalone_fct (ns)
	fprintf(fout, "%u %08x %08x %u %u %lu %lu %lu %lu\n", q->m_flowId, q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->m_size, q->startTime.GetTimeStep(), (Simulator::Now() - q->startTime).GetTimeStep(), standalone_fct);
	fflush(fout);
}

void get_pfc(FILE* fout, Ptr<QbbNetDevice> dev, uint32_t type){
    fprintf(fout, "%lu %u %u %u %u\n", Simulator::Now().GetTimeStep(), dev->GetNode()->GetId(), dev->GetNode()->GetNodeType(), dev->GetIfIndex(), type);
}

struct QlenDistribution{
	vector<uint32_t> cnt; // cnt[i] is the number of times that the queue len is i KB

	void add(uint32_t qlen){
		uint32_t kb = qlen / 1000;
		if (cnt.size() < kb+1)
			cnt.resize(kb+1);
		cnt[kb]++;
	}
};
map<uint32_t, map<uint32_t, QlenDistribution> > queue_result;
void monitor_buffer(FILE* qlen_output, NodeContainer *n){
	for (uint32_t i = 0; i < n->GetN(); i++){
		if (n->Get(i)->GetNodeType() == 1){ // is switch
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n->Get(i));
			if (queue_result.find(i) == queue_result.end())
				queue_result[i];
			for (uint32_t j = 1; j < sw->GetNDevices(); j++){
				uint32_t size = 0;
				for (uint32_t k = 0; k < SwitchMmu::qCnt; k++)
					size += sw->m_mmu->egress_bytes[j][k];
				queue_result[i][j].add(size);
			}
		}
	}
	if (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0){
		fprintf(qlen_output, "time: %lu\n", Simulator::Now().GetTimeStep());
		for (auto &it0 : queue_result)
			for (auto &it1 : it0.second){
				fprintf(qlen_output, "%u %u", it0.first, it1.first);
				auto &dist = it1.second.cnt;
				for (uint32_t i = 0; i < dist.size(); i++)
					fprintf(qlen_output, " %u", dist[i]);
				fprintf(qlen_output, "\n");
			}
		fflush(qlen_output);
	}
	if (Simulator::Now().GetTimeStep() < qlen_mon_end)
		Simulator::Schedule(NanoSeconds(qlen_mon_interval), &monitor_buffer, qlen_output, n);
}

void CalculateRoute(Ptr<Node> host){
    // queue for the BFS.
    vector<Ptr<Node> > q;
    // Distance from the host to each node.
    map<Ptr<Node>, int> dis;
    map<Ptr<Node>, uint64_t> delay;
    map<Ptr<Node>, vector<uint64_t>> bws;
    map<Ptr<Node>, uint64_t> bw;
    // init BFS.
    q.push_back(host);
    dis[host] = 0;
    delay[host] = 0;
    bw[host] = 0xfffffffffffffffflu;
    // BFS.
    for (int i = 0; i < (int)q.size(); i++){
        Ptr<Node> now = q[i];
        int d = dis[now];
        for (auto it = nbr2if[now].begin(); it != nbr2if[now].end(); it++){
            // skip down link
            if (!it->second.up)
                continue;
            Ptr<Node> next = it->first;
            // If 'next' have not been visited.
            if (dis.find(next) == dis.end()){
                dis[next] = d + 1;
                delay[next] = delay[now] + it->second.delay;
                bws[next] = bws[now];
				bws[next].push_back(it->second.bw);
                bw[next] = std::min(bw[now], it->second.bw);
                // we only enqueue switch, because we do not want packets to go through host as middle point
                if (next->GetNodeType() == 1)
                    q.push_back(next);
            }
            // if 'now' is on the shortest path from 'next' to 'host'.
            if (d + 1 == dis[next]){
                nextHop[next][host].push_back(now);
            }
        }
    }
    for (auto it : delay)
        pairDelay[it.first][host] = it.second;
    for (auto it : bw)
        pairBw[it.first->GetId()][host->GetId()] = it.second;
    for (auto it: bws)
		pairBws[it.first->GetId()][host->GetId()] = it.second;
}

void CalculateRoutes(NodeContainer &n){
    for (int i = 0; i < (int)n.GetN(); i++){
        Ptr<Node> node = n.Get(i);
        if (node->GetNodeType() == 0)
            CalculateRoute(node);
    }
}

void SetRoutingEntries(){
    // For each node.
    for (auto i = nextHop.begin(); i != nextHop.end(); i++){
        Ptr<Node> node = i->first;
        auto &table = i->second;
        for (auto j = table.begin(); j != table.end(); j++){
            // The destination node.
            Ptr<Node> dst = j->first;
            // The IP address of the dst.
            Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
            // The next hops towards the dst.
            vector<Ptr<Node> > nexts = j->second;
            for (int k = 0; k < (int)nexts.size(); k++){
                Ptr<Node> next = nexts[k];
                uint32_t interface = nbr2if[node][next].idx;
                if (node->GetNodeType() == 1)
                    DynamicCast<SwitchNode>(node)->AddTableEntry(dstAddr, interface);
                else{
                    node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(dstAddr, interface);
                }
            }
        }
    }
}

// take down the link between a and b, and redo the routing
void TakeDownLink(NodeContainer n, Ptr<Node> a, Ptr<Node> b){
	if (!nbr2if[a][b].up)
		return;
	// take down link between a and b
	nbr2if[a][b].up = nbr2if[b][a].up = false;
	nextHop.clear();
	CalculateRoutes(n);
	// clear routing tables
	for (uint32_t i = 0; i < n.GetN(); i++){
		if (n.Get(i)->GetNodeType() == 1)
			DynamicCast<SwitchNode>(n.Get(i))->ClearTable();
		else
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->ClearTable();
	}
	DynamicCast<QbbNetDevice>(a->GetDevice(nbr2if[a][b].idx))->TakeDown();
	DynamicCast<QbbNetDevice>(b->GetDevice(nbr2if[b][a].idx))->TakeDown();
	// reset routing table
	SetRoutingEntries();

	// redistribute qp on each host
	for (uint32_t i = 0; i < n.GetN(); i++){
		if (n.Get(i)->GetNodeType() == 0)
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->RedistributeQp();
	}
}

uint64_t get_nic_rate(NodeContainer &n){
    for (uint32_t i = 0; i < n.GetN(); i++)
        if (n.Get(i)->GetNodeType() == 0)
            return DynamicCast<QbbNetDevice>(n.Get(i)->GetDevice(1))->GetDataRate().GetBitRate();
}

void PrintProgress(Time interval)
{
	std::cout << "t = " << Simulator::Now().GetMilliSeconds() << " ms" << '\n';
	Simulator::Schedule(interval, &PrintProgress, interval);
}

int main(int argc, char *argv[])
{
    bool powertcp = false;
    bool thetapowertcp = false;

    uint32_t bufferalgIngress = DT;
    uint32_t bufferalgEgress = DT;
    double egressLossyShare = 0.8;
    std::string bufferModel = "sonic";
    double gamma = 0.99;

    std::string alphasFile = "/data1/lichenni/projects/ref_sys/High-Precision-Congestion-Control/ns-3.39/examples/Reverie/alphas"; // On lakewood

    std::string line;
    std::fstream aFile;
    aFile.open(alphasFile);
    uint32_t p = 0;
    while ( getline( aFile, line ) && p < 8 ) { // hard coded to read only 8 alpha values.
        std::istringstream iss( line );
        double a;
        iss >> a;
        alpha_values[p] = a;
        // std::cout << "alpha-" << p << " " << alpha_values[p] << std::endl;
        p++;
    }
    aFile.close();

	clock_t begint, endt;
	begint = clock();
	if (argc > 1)
	{
		//Read the configuration file
		std::ifstream conf;
		conf.open(argv[1]);
		while (!conf.eof())
		{
			std::string key;
			conf >> key;

			if (key.compare("ENABLE_QCN") == 0)
			{
				uint32_t v;
				conf >> v;
				enable_qcn = v;
				if (enable_qcn)
					std::cout << "ENABLE_QCN\t\t\t" << "Yes" << "\n";
				else
					std::cout << "ENABLE_QCN\t\t\t" << "No" << "\n";
			}
            else if (key.compare("ENABLE_PFC") == 0)
			{
				uint32_t v;
				conf >> v;
				enable_pfc = v;
				if (enable_pfc)
					std::cout << "ENABLE_PFC\t\t\t" << "Yes" << "\n";
				else
					std::cout << "ENABLE_PFC\t\t\t" << "No" << "\n";
			}
			else if (key.compare("CLAMP_TARGET_RATE") == 0)
			{
				uint32_t v;
				conf >> v;
				clamp_target_rate = v;
				if (clamp_target_rate)
						std::cout << "CLAMP_TARGET_RATE\t\t" << "Yes" << "\n";
					else
						std::cout << "CLAMP_TARGET_RATE\t\t" << "No" << "\n";
			}
			else if (key.compare("PAUSE_TIME") == 0)
			{
				double v;
				conf >> v;
				pause_time = v;
				std::cout << "PAUSE_TIME\t\t\t" << pause_time << "\n";
			}
				else if (key.compare("DATA_RATE") == 0)
				{
					std::string v;
					conf >> v;
					data_rate = v;
					std::cout << "DATA_RATE\t\t\t" << data_rate << "\n";
				}
				else if (key.compare("LINK_DELAY") == 0)
				{
					std::string v;
					conf >> v;
					link_delay = v;
					std::cout << "LINK_DELAY\t\t\t" << link_delay << "\n";
			}
			else if (key.compare("PACKET_PAYLOAD_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				packet_payload_size = v;
				std::cout << "PACKET_PAYLOAD_SIZE\t\t" << packet_payload_size << "\n";
			}
			else if (key.compare("L2_CHUNK_SIZE") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_chunk_size = v;
				std::cout << "L2_CHUNK_SIZE\t\t\t" << l2_chunk_size << "\n";
			}
			else if (key.compare("L2_ACK_INTERVAL") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_ack_interval = v;
				std::cout << "L2_ACK_INTERVAL\t\t\t" << l2_ack_interval << "\n";
			}
			else if (key.compare("L2_BACK_TO_ZERO") == 0)
			{
				uint32_t v;
				conf >> v;
				l2_back_to_zero = v;
				if (l2_back_to_zero)
						std::cout << "L2_BACK_TO_ZERO\t\t\t" << "Yes" << "\n";
					else
						std::cout << "L2_BACK_TO_ZERO\t\t\t" << "No" << "\n";
			}
			else if (key.compare("TOPOLOGY_FILE") == 0)
			{
				std::string v;
				conf >> v;
				topology_file = v;
				std::cout << "TOPOLOGY_FILE\t\t\t" << topology_file << "\n";
			}
			else if (key.compare("FLOW_FILE") == 0)
			{
				std::string v;
				conf >> v;
				flow_file = v;
				std::cout << "FLOW_FILE\t\t\t" << flow_file << "\n";
			}
			else if (key.compare("TRACE_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_file = v;
				std::cout << "TRACE_FILE\t\t\t" << trace_file << "\n";
			}
			else if (key.compare("TRACE_OUTPUT_FILE") == 0)
			{
				std::string v;
				conf >> v;
				trace_output_file = v;
				if (argc > 2)
				{
					trace_output_file = trace_output_file + std::string(argv[2]);
				}
				std::cout << "TRACE_OUTPUT_FILE\t\t" << trace_output_file << "\n";
			}
			else if (key.compare("SIMULATOR_STOP_TIME") == 0)
			{
				double v;
				conf >> v;
				simulator_stop_time = v;
				std::cout << "SIMULATOR_STOP_TIME\t\t" << simulator_stop_time << "\n";
			}
			else if (key.compare("ALPHA_RESUME_INTERVAL") == 0)
			{
				double v;
				conf >> v;
				alpha_resume_interval = v;
				std::cout << "ALPHA_RESUME_INTERVAL\t\t" << alpha_resume_interval << "\n";
			}
			else if (key.compare("RP_TIMER") == 0)
			{
				double v;
				conf >> v;
				rp_timer = v;
				std::cout << "RP_TIMER\t\t\t" << rp_timer << "\n";
			}
			else if (key.compare("EWMA_GAIN") == 0)
			{
				double v;
				conf >> v;
				ewma_gain = v;
				std::cout << "EWMA_GAIN\t\t\t" << ewma_gain << "\n";
			}
			else if (key.compare("FAST_RECOVERY_TIMES") == 0)
			{
				uint32_t v;
				conf >> v;
				fast_recovery_times = v;
				std::cout << "FAST_RECOVERY_TIMES\t\t" << fast_recovery_times << "\n";
			}
			else if (key.compare("RATE_AI") == 0)
			{
				std::string v;
				conf >> v;
				rate_ai = v;
				std::cout << "RATE_AI\t\t\t\t" << rate_ai << "\n";
			}
			else if (key.compare("RATE_HAI") == 0)
			{
				std::string v;
				conf >> v;
				rate_hai = v;
				std::cout << "RATE_HAI\t\t\t" << rate_hai << "\n";
			}
			else if (key.compare("ERROR_RATE_PER_LINK") == 0)
			{
				double v;
				conf >> v;
				error_rate_per_link = v;
				std::cout << "ERROR_RATE_PER_LINK\t\t" << error_rate_per_link << "\n";
			}
			else if (key.compare("CC_MODE") == 0){
					conf >> cc_mode;
					std::cout << "CC_MODE\t\t" << cc_mode << '\n';
			}else if (key.compare("RATE_DECREASE_INTERVAL") == 0){
				double v;
				conf >> v;
				rate_decrease_interval = v;
				std::cout << "RATE_DECREASE_INTERVAL\t\t" << rate_decrease_interval << "\n";
			}else if (key.compare("MIN_RATE") == 0){
				conf >> min_rate;
				std::cout << "MIN_RATE\t\t" << min_rate << "\n";
            }else if (key.compare("FCT_OUTPUT_FILE") == 0){
                conf >> fct_output_file;
                std::cout << "FCT_OUTPUT_FILE\t\t" << fct_output_file << '\n';
            }else if (key.compare("HAS_WIN") == 0){
                conf >> has_win;
                std::cout << "HAS_WIN\t\t" << has_win << "\n";
			}else if (key.compare("GLOBAL_T") == 0){
				conf >> global_t;
				std::cout << "GLOBAL_T\t\t" << global_t << '\n';
			}else if (key.compare("MI_THRESH") == 0){
				conf >> mi_thresh;
				std::cout << "MI_THRESH\t\t" << mi_thresh << '\n';
			}else if (key.compare("VAR_WIN") == 0){
				uint32_t v;
				conf >> v;
				var_win = v;
				std::cout << "VAR_WIN\t\t" << v << '\n';
			}else if (key.compare("FAST_REACT") == 0){
				uint32_t v;
				conf >> v;
				fast_react = v;
				std::cout << "FAST_REACT\t\t" << v << '\n';
			}else if (key.compare("U_TARGET") == 0){
				conf >> u_target;
				std::cout << "U_TARGET\t\t" << u_target << '\n';
			}else if (key.compare("INT_MULTI") == 0){
				conf >> int_multi;
				std::cout << "INT_MULTI\t\t\t\t" << int_multi << '\n';
			}else if (key.compare("RATE_BOUND") == 0){
				uint32_t v;
				conf >> v;
				rate_bound = v;
				std::cout << "RATE_BOUND\t\t" << rate_bound << '\n';
			}else if (key.compare("ACK_HIGH_PRIO") == 0){
				conf >> ack_high_prio;
				std::cout << "ACK_HIGH_PRIO\t\t" << ack_high_prio << '\n';
			}else if (key.compare("DCTCP_RATE_AI") == 0){
				conf >> dctcp_rate_ai;
				std::cout << "DCTCP_RATE_AI\t\t\t\t" << dctcp_rate_ai << "\n";
			}else if (key.compare("TIMELY_T_HIGH") == 0){
				conf >> timely_t_high;
				std::cout << "TIMELY_T_HIGH\t\t\t\t" << timely_t_high << "\n";
			}else if (key.compare("TIMELY_T_LOW") == 0){
				conf >> timely_t_low;
				std::cout << "TIMELY_T_LOW\t\t\t\t" << timely_t_low << "\n";
			}else if (key.compare("TIMELY_BETA") == 0){
				conf >> timely_beta;
				std::cout << "TIMELY_BETA\t\t\t\t" << timely_beta << "\n";
			}else if (key.compare("PFC_OUTPUT_FILE") == 0){
				conf >> pfc_output_file;
				std::cout << "PFC_OUTPUT_FILE\t\t\t\t" << pfc_output_file << '\n';
			}else if (key.compare("LINK_DOWN") == 0){
				conf >> link_down_time >> link_down_A >> link_down_B;
				std::cout << "LINK_DOWN\t\t\t\t" << link_down_time << ' '<< link_down_A << ' ' << link_down_B << '\n';
			}else if (key.compare("ENABLE_TRACE") == 0){
				conf >> enable_trace;
				std::cout << "ENABLE_TRACE\t\t\t\t" << enable_trace << '\n';
			}else if (key.compare("KMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmax[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("KMIN_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "KMIN_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					uint32_t k;
					conf >> rate >> k;
					rate2kmin[rate] = k;
					std::cout << ' ' << rate << ' ' << k;
				}
				std::cout<<'\n';
			}else if (key.compare("PMAX_MAP") == 0){
				int n_k ;
				conf >> n_k;
				std::cout << "PMAX_MAP\t\t\t\t";
				for (int i = 0; i < n_k; i++){
					uint64_t rate;
					double p;
					conf >> rate >> p;
					rate2pmax[rate] = p;
					std::cout << ' ' << rate << ' ' << p;
				}
				std::cout<<'\n';
			}else if (key.compare("BUFFER_SIZE") == 0){
				conf >> buffer_size;
				std::cout << "BUFFER_SIZE\t\t\t\t" << buffer_size << '\n';
			}else if (key.compare("QLEN_MON_FILE") == 0){
				conf >> qlen_mon_file;
				std::cout << "QLEN_MON_FILE\t\t\t\t" << qlen_mon_file << '\n';
			}else if (key.compare("QLEN_MON_START") == 0){
				conf >> qlen_mon_start;
				std::cout << "QLEN_MON_START\t\t\t\t" << qlen_mon_start << '\n';
			}else if (key.compare("QLEN_MON_END") == 0){
				conf >> qlen_mon_end;
				std::cout << "QLEN_MON_END\t\t\t\t" << qlen_mon_end << '\n';
			}else if (key.compare("MULTI_RATE") == 0){
				int v;
				conf >> v;
				multi_rate = v;
				std::cout << "MULTI_RATE\t\t\t\t" << multi_rate << '\n';
			}else if (key.compare("SAMPLE_FEEDBACK") == 0){
				int v;
				conf >> v;
				sample_feedback = v;
				std::cout << "SAMPLE_FEEDBACK\t\t\t\t" << sample_feedback << '\n';
			}else if(key.compare("PINT_LOG_BASE") == 0){
				conf >> pint_log_base;
				std::cout << "PINT_LOG_BASE\t\t\t\t" << pint_log_base << '\n';
			}else if (key.compare("PINT_PROB") == 0){
				conf >> pint_prob;
				std::cout << "PINT_PROB\t\t\t\t" << pint_prob << '\n';
			}else if (key.compare("FIXED_WIN") == 0){
				conf >> fwin;
				std::cout << "FIXED_WIN\t\t\t\t" << fwin << '\n';
			}else if (key.compare("BASE_RTT") == 0){
				conf >> baseRtt;
				std::cout << "BASE_RTT\t\t\t\t" << baseRtt << '\n';
			}
			fflush(stdout);
		}
		conf.close();
	}
	else
	{
		std::cout << "Error: require a config file\n";
		fflush(stdout);
		return 1;
	}

    buffer_size=buffer_size*1024;

    printf("fwin: %lu, bfsz: %d, enable_pfc: %d, cc_mode: %d, rate2kmin: %u, rate2kmax: %u, timely_t_low: %d, timely_t_high: %d,rate2kmin: %u, rate2kmax: %u, u_target: %f, ai: %s, enable_qcn: %d\n",
       fwin, buffer_size, enable_pfc, cc_mode,
       rate2kmin[10000000000], rate2kmax[10000000000],
       timely_t_low, timely_t_high, rate2kmin[10000000000], rate2kmax[10000000000], u_target, rate_ai.c_str(),enable_qcn);
    Config::SetDefault("ns3::QbbNetDevice::PauseTime", UintegerValue(pause_time));
    Config::SetDefault("ns3::QbbNetDevice::QbbEnabled", BooleanValue(enable_pfc));
    Config::SetDefault("ns3::QbbNetDevice::QcnEnabled", BooleanValue(enable_qcn));

    // set int_multi
    IntHop::multi = int_multi;
    // IntHeader::mode
    if (cc_mode == TIMELYCC) // timely, use ts
        IntHeader::mode = IntHeader::TS;
    else if (cc_mode == INTCC) // hpcc, powertcp, use int
        IntHeader::mode = IntHeader::NORMAL;
    else if (cc_mode == PINTCC) // hpcc-pint
        IntHeader::mode = IntHeader::PINT;
    else // others, no extra header
        IntHeader::mode = IntHeader::NONE;
    
    if (cc_mode < TCP_BBR)
        gen_tcp_traffic = false;

    // Set Pint
    if (cc_mode == PINTCC) {
        Pint::set_log_base(pint_log_base);
        IntHeader::pint_bytes = Pint::get_n_bytes();
        printf("PINT bits: %d bytes: %d\n", Pint::get_n_bits(), Pint::get_n_bytes());
    }

    topof.open(topology_file.c_str());
    flowf.open(flow_file.c_str());
    tracef.open(trace_file.c_str());
    uint32_t node_num, switch_num, link_num, trace_num;
    topof >> node_num >> switch_num >> link_num;
    flowf >> flow_num;
    tracef >> trace_num;


    //n.Create(node_num);
    std::vector<uint32_t> node_type(node_num, 0);
    for (uint32_t i = 0; i < switch_num; i++)
    {
        uint32_t sid;
        topof >> sid;
        node_type[sid] = 1;
    }
    for (uint32_t i = 0; i < node_num; i++){
        if (node_type[i] == 0)
            n.Add(CreateObject<Node>());
        else{
            Ptr<SwitchNode> sw = CreateObject<SwitchNode>();
            n.Add(sw);
            sw->SetAttribute("EcnEnabled", BooleanValue(enable_qcn));
        }
    }


    NS_LOG_INFO("Create nodes.");

    Config::SetDefault ("ns3::Ipv4GlobalRouting::FlowEcmpRouting", BooleanValue(true));
    InternetStackHelper internet;
    Ipv4GlobalRoutingHelper globalRoutingHelper;
    internet.SetRoutingHelper (globalRoutingHelper);
    internet.Install(n);

    //
    // Assign IP to each server
    //
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() == 0){ // is server
            serverAddress.resize(i + 1);
            serverAddress[i] = node_id_to_ip(i);
        }
    }

    NS_LOG_INFO("Create channels.");

    //
    // Explicitly create the channels required by the topology.
    //

    Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
    Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
    rem->SetRandomVariable(uv);
    uv->SetStream(50);
    rem->SetAttribute("ErrorRate", DoubleValue(error_rate_per_link));
    rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));

	FILE *pfc_file = fopen(pfc_output_file.c_str(), "w");

    QbbHelper qbb;
    Ipv4AddressHelper ipv4;
    for (uint32_t i = 0; i < link_num; i++)
    {
        uint32_t src, dst;
        std::string data_rate, link_delay;
        double error_rate;
        topof >> src >> dst >> data_rate >> link_delay >> error_rate;

        Ptr<Node> snode = n.Get(src), dnode = n.Get(dst);

        qbb.SetDeviceAttribute("DataRate", StringValue(data_rate));
        qbb.SetChannelAttribute("Delay", StringValue(link_delay));

        if (error_rate > 0)
        {
            Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
            Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
            rem->SetRandomVariable(uv);
            uv->SetStream(50);
            rem->SetAttribute("ErrorRate", DoubleValue(error_rate));
            rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
            qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
        }
        else
        {
            qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
        }

        fflush(stdout);

        // Assigne server IP
        // Note: this should be before the automatic assignment below (ipv4.Assign(d)),
        // because we want our IP to be the primary IP (first in the IP address list),
        // so that the global routing is based on our IP
        NetDeviceContainer d = qbb.Install(snode, dnode);
        if (snode->GetNodeType() == 0){
            Ptr<Ipv4> ipv4 = snode->GetObject<Ipv4>();
            ipv4->AddInterface(d.Get(0));
            ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[src], Ipv4Mask(0xff000000)));
        }
        if (dnode->GetNodeType() == 0){
            Ptr<Ipv4> ipv4 = dnode->GetObject<Ipv4>();
            ipv4->AddInterface(d.Get(1));
            ipv4->AddAddress(1, Ipv4InterfaceAddress(serverAddress[dst], Ipv4Mask(0xff000000)));
        }

        // used to create a graph of the topology
        nbr2if[snode][dnode].idx = DynamicCast<QbbNetDevice>(d.Get(0))->GetIfIndex();
        nbr2if[snode][dnode].up = true;
        nbr2if[snode][dnode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(0))->GetChannel())->GetDelay().GetTimeStep();
        nbr2if[snode][dnode].bw = DynamicCast<QbbNetDevice>(d.Get(0))->GetDataRate().GetBitRate();
        nbr2if[dnode][snode].idx = DynamicCast<QbbNetDevice>(d.Get(1))->GetIfIndex();
        nbr2if[dnode][snode].up = true;
        nbr2if[dnode][snode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(1))->GetChannel())->GetDelay().GetTimeStep();
        nbr2if[dnode][snode].bw = DynamicCast<QbbNetDevice>(d.Get(1))->GetDataRate().GetBitRate();

        // This is just to set up the connectivity between nodes. The IP addresses are useless
        char ipstring[16];
		sprintf(ipstring, "10.%d.%d.0", i / 254 + 1, i % 254 + 1);
		ipv4.SetBase(ipstring, "255.255.255.0");
        ipv4.Assign(d);

        // setup PFC trace
        DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(0))));
        DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback (&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(1))));
    }

    nic_rate = get_nic_rate(n);
    
    // config switch
    // The switch mmu runs Dynamic Thresholds (DT) by default.
    uint64_t totalHeadroom;
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() == 1){ // is switch
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
            totalHeadroom = 0;
            sw->m_mmu->SetIngressLossyAlg(bufferalgIngress);
            sw->m_mmu->SetIngressLosslessAlg(bufferalgIngress);
            sw->m_mmu->SetEgressLossyAlg(bufferalgEgress);
            sw->m_mmu->SetEgressLosslessAlg(bufferalgEgress);
            sw->m_mmu->SetABMalphaHigh(1024);
            sw->m_mmu->SetABMdequeueUpdateNS(maxRtt);
            sw->m_mmu->SetPortCount(sw->GetNDevices() - 1); // set the actual port count here so that we don't always iterate over the default 256 ports.
            sw->m_mmu->SetBufferModel(bufferModel);
            sw->m_mmu->SetGamma(gamma);
            // std::cout << "ports " << sw->GetNDevices() << " node " << i << std::endl;
            for (uint32_t j = 1; j < sw->GetNDevices(); j++){
                Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(j));
                uint64_t rate = dev->GetDataRate().GetBitRate();
                // set port bandwidth in the mmu, used by ABM.
                sw->m_mmu->bandwidth[j] = rate;
                for (uint32_t qu = 0; qu < 8; qu++) {
                    if (qu == 3 || qu == 0) { // lossless
                        sw->m_mmu->SetAlphaIngress(alpha_values[qu], j, qu);
                        sw->m_mmu->SetAlphaEgress(10000, j, qu);
                        // set pfc
                        double delay = DynamicCast<QbbChannel>(dev->GetChannel())->GetDelay().GetSeconds();
                        uint32_t headroom = (packet_payload_size + 48) * 2 + 3860 + (2 * rate * delay / 8);
                        // std::cout << headroom << std::endl;
                        sw->m_mmu->SetHeadroom(headroom, j, qu);
                        totalHeadroom += headroom;
                    }
                    else { // lossy
                        sw->m_mmu->SetAlphaIngress(10000, j, qu);
                        sw->m_mmu->SetAlphaEgress(alpha_values[qu], j, qu);
                    }

                    // set ecn
                    NS_ASSERT_MSG(rate2kmin.find(rate) != rate2kmin.end(), "must set kmin for each link speed");
                    NS_ASSERT_MSG(rate2kmax.find(rate) != rate2kmax.end(), "must set kmax for each link speed");
                    NS_ASSERT_MSG(rate2pmax.find(rate) != rate2pmax.end(), "must set pmax for each link speed");
                    sw->m_mmu->ConfigEcn(j, rate2kmin[rate], rate2kmax[rate], rate2pmax[rate]);
                }

            }
            sw->m_mmu->SetBufferPool(buffer_size);
            sw->m_mmu->SetIngressPool(buffer_size - totalHeadroom);
            sw->m_mmu->SetSharedPool(buffer_size  - totalHeadroom);
            sw->m_mmu->SetEgressLosslessPool(buffer_size);
            sw->m_mmu->SetEgressLossyPool((buffer_size - totalHeadroom) * egressLossyShare);
            sw->m_mmu->node_id = sw->GetId();
        }
        if (n.Get(i)->GetNodeType())
            std::cout << "total headroom: " << totalHeadroom << " ingressPool " << buffer_size - totalHeadroom << " egressLosslessPool " 
                      << buffer_size << " egressLossyPool " << (uint64_t)((buffer_size - totalHeadroom) * egressLossyShare) 
                      << " sharedPool " << buffer_size - totalHeadroom <<  std::endl;
    }

    #if ENABLE_QP
    FILE *fct_output = fopen(fct_output_file.c_str(), "w");
    //
    // install RDMA driver
    //
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() == 0){ // is server
            // create RdmaHw
            Ptr<RdmaHw> rdmaHw = CreateObject<RdmaHw>();
            rdmaHw->SetAttribute("ClampTargetRate", BooleanValue(clamp_target_rate));
            rdmaHw->SetAttribute("AlphaResumInterval", DoubleValue(alpha_resume_interval));
            rdmaHw->SetAttribute("RPTimer", DoubleValue(rp_timer));
            rdmaHw->SetAttribute("FastRecoveryTimes", UintegerValue(fast_recovery_times));
            rdmaHw->SetAttribute("EwmaGain", DoubleValue(ewma_gain));
            rdmaHw->SetAttribute("RateAI", DataRateValue(DataRate(rate_ai)));
            rdmaHw->SetAttribute("RateHAI", DataRateValue(DataRate(rate_hai)));
            rdmaHw->SetAttribute("L2BackToZero", BooleanValue(l2_back_to_zero));
            rdmaHw->SetAttribute("L2ChunkSize", UintegerValue(l2_chunk_size));
            rdmaHw->SetAttribute("L2AckInterval", UintegerValue(l2_ack_interval));
            rdmaHw->SetAttribute("CcMode", UintegerValue(cc_mode));
            rdmaHw->SetAttribute("RateDecreaseInterval", DoubleValue(rate_decrease_interval));
            rdmaHw->SetAttribute("MinRate", DataRateValue(DataRate(min_rate)));
            rdmaHw->SetAttribute("Mtu", UintegerValue(packet_payload_size));
            rdmaHw->SetAttribute("MiThresh", UintegerValue(mi_thresh));
            rdmaHw->SetAttribute("VarWin", BooleanValue(var_win));
            rdmaHw->SetAttribute("FastReact", BooleanValue(fast_react));
            rdmaHw->SetAttribute("MultiRate", BooleanValue(multi_rate));
            rdmaHw->SetAttribute("SampleFeedback", BooleanValue(sample_feedback));
            rdmaHw->SetAttribute("TargetUtil", DoubleValue(u_target));
            rdmaHw->SetAttribute("RateBound", BooleanValue(rate_bound));
            rdmaHw->SetAttribute("DctcpRateAI", DataRateValue(DataRate(dctcp_rate_ai)));
            rdmaHw->SetAttribute("TimelyTHigh", UintegerValue(timely_t_high));
			rdmaHw->SetAttribute("TimelyTLow", UintegerValue(timely_t_low));
			rdmaHw->SetAttribute("TimelyBeta", DoubleValue(timely_beta));
            rdmaHw->SetAttribute("PowerTCPEnabled", BooleanValue(powertcp));
            rdmaHw->SetAttribute("PowerTCPdelay", BooleanValue(thetapowertcp));
            rdmaHw->SetPintSmplThresh(pint_prob);
            // create and install RdmaDriver
            Ptr<RdmaDriver> rdma = CreateObject<RdmaDriver>();
            Ptr<Node> node = n.Get(i);
            rdma->SetNode(node);
            rdma->SetRdmaHw(rdmaHw);

            node->AggregateObject (rdma);
            rdma->Init();
            rdma->TraceConnectWithoutContext("QpComplete", MakeBoundCallback (qp_finish, fct_output));
            rdma->TraceConnectWithoutContext("QpDelivered", MakeBoundCallback (qp_delivered, fct_output));
        }
    }
    #endif

    // set ACK priority on hosts
    if (ack_high_prio) {
		RdmaEgressQueue::ack_q_idx = 0;
		for (uint32_t i = 0; i < node_num; i++)
		{
			if (n.Get(i)->GetNodeType() == 1)
			{ // switch
				Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
				sw->SetAttribute("AckHighPrio", UintegerValue(1));
			}
		}
	} else {
		RdmaEgressQueue::ack_q_idx = 3;
	}

    // setup routing
    CalculateRoutes(n);
    SetRoutingEntries();

    //
    // get BDP and delay
    //
    maxRtt = maxBdp = 0;
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() != 0)
            continue;
        for (uint32_t j = 0; j < node_num; j++){
            if (n.Get(j)->GetNodeType() != 0)
                continue;
            if (i == j)
                continue;
            uint64_t delay = pairDelay[n.Get(i)][n.Get(j)];
            uint64_t rtt = delay * 2;
            uint64_t bw = pairBw[i][j];
            uint64_t bdp = rtt * bw / 1000000000/8;
            pairBdp[n.Get(i)][n.Get(j)] = bdp;
            pairRtt[i][j] = rtt;
            if (bdp > maxBdp)
                maxBdp = bdp;
            if (rtt > maxRtt)
                maxRtt = rtt;
        }
    }
    printf("maxRtt=%lu maxBdp=%lu\n", maxRtt, maxBdp);

    //
    // setup switch CC
    //
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() == 1){ // switch
            Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
            sw->SetAttribute("CcMode", UintegerValue(cc_mode));
            sw->SetAttribute("MaxRtt", UintegerValue(baseRtt));
            sw->SetAttribute("PowerEnabled", BooleanValue(powertcp));
        }
    }

    //
	// add trace
	//

	NodeContainer trace_nodes;
	for (uint32_t i = 0; i < trace_num; i++)
	{
		uint32_t nid;
		tracef >> nid;
		if (nid >= n.GetN()){
			continue;
		}
		trace_nodes = NodeContainer(trace_nodes, n.Get(nid));
	}

	FILE *trace_output = fopen(trace_output_file.c_str(), "w");
	if (enable_trace)
		qbb.EnableTracing(trace_output, trace_nodes);

	// dump link speed to trace file
	{
		SimSetting sim_setting;
		for (auto i: nbr2if){
			for (auto j : i.second){
				uint16_t node = i.first->GetId();
				uint8_t intf = j.second.idx;
				uint64_t bps = DynamicCast<QbbNetDevice>(i.first->GetDevice(j.second.idx))->GetDataRate().GetBitRate();
				sim_setting.port_speed[node][intf] = bps;
			}
		}
		sim_setting.win = fwin;
		sim_setting.Serialize(trace_output);
	}

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    Time interPacketInterval = Seconds(0.0000005 / 2);

    // maintain port number for each host
    for (uint32_t i = 0; i < node_num; i++){
        if (n.Get(i)->GetNodeType() == 0)
            PORT_START[i] = 4444;
            for (uint32_t j = 0; j < node_num; j++){
                if (n.Get(j)->GetNodeType() == 0)
                    portNumder[i][j] = PORT_NUMBER_START; // each host pair use port number from 10000
            }
    }

    /* Applications Background*/
    if (gen_tcp_traffic){
        /*General TCP Socket settings. Mostly used by various congestion control algorithms in common*/
        Config::SetDefault ("ns3::TcpSocket::ConnTimeout", TimeValue (MilliSeconds (10))); // syn retry interval
        Config::SetDefault ("ns3::TcpSocketBase::MinRto", TimeValue (MicroSeconds (1000)) );  //(MilliSeconds (5))
        Config::SetDefault ("ns3::TcpSocketBase::RTTBytes", UintegerValue ( packet_payload_size*100 )); //packet_payload_size*1000 // This many number of first bytes will be prioritized by ABM. It is not necessarily RTTBytes
        Config::SetDefault ("ns3::TcpSocketBase::ClockGranularity", TimeValue (NanoSeconds (10))); //(MicroSeconds (100))
        Config::SetDefault ("ns3::RttEstimator::InitialEstimation", TimeValue (MicroSeconds (10))); //TimeValue (MicroSeconds (80))
        Config::SetDefault ("ns3::TcpSocket::SndBufSize", UintegerValue (1073725440)); //1073725440
        Config::SetDefault ("ns3::TcpSocket::RcvBufSize", UintegerValue (1073725440));
        Config::SetDefault ("ns3::TcpSocket::ConnCount", UintegerValue (6));  // Syn retry count
        Config::SetDefault ("ns3::TcpSocketBase::Timestamp", BooleanValue (true));
        Config::SetDefault ("ns3::TcpSocket::SegmentSize", UintegerValue (packet_payload_size));
        Config::SetDefault ("ns3::TcpSocket::DelAckCount", UintegerValue (0));
        Config::SetDefault ("ns3::TcpSocket::PersistTimeout", TimeValue (Seconds (20)));

        switch (cc_mode) {
            case TCP_BBR:
                printf("CC: BBR\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpBbr::GetTypeId()));
                break;
            case TCP_CUBIC:
                printf("CC: CUBIC\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpCubic::GetTypeId()));
                break;
            case TCP_DCTCP:
                printf("CC: DCTCP\n");
                if (!enable_qcn) {
                    std::cout << "Set enableEcn option in order to use DCTCP" << std::endl;
                    exit(1);
                }
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpDctcp::GetTypeId()));
                Config::SetDefault("ns3::TcpSocketBase::UseEcn", StringValue("On"));
                break;
            case TCP_HIGH_SPEED:
                printf("CC: HighSpeed\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpHighSpeed::GetTypeId()));
                break;
            case TCP_HTCP:
                printf("CC: HTCP\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpHtcp::GetTypeId()));
                break;
            case TCP_HYBLA:
                printf("CC: Hybla\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpHybla::GetTypeId()));
                break;
            case TCP_ILLINOIS:
                printf("CC: Illinois\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpIllinois::GetTypeId()));
                break;
            case TCP_LED_BAT:
                printf("CC: LEDBAT\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpLedbat::GetTypeId()));
                break;
            case TCP_LP:
                printf("CC: LP\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpLp::GetTypeId()));
                break;
            case TCP_SCALABLE:
                printf("CC: Scalable\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpScalable::GetTypeId()));
                break;
            case TCP_VEGAS:
                printf("CC: Vegas\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpVegas::GetTypeId()));
                break;
            case TCP_VENO:
                printf("CC: Veno\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpVeno::GetTypeId()));
                break;
            case TCP_WESTWOOD:
                printf("CC: Westwood+\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpWestwoodPlus::GetTypeId()));
                break;
            case TCP_YEAH:
                printf("CC: YeAH\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpYeah::GetTypeId()));
                break;
            case TCP_NEW_RENO:
                printf("CC: Default TCP NewReno\n");
                Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(ns3::TcpNewReno::GetTypeId()));
                break;
        }

    }
    flow_input.idx = 0;
    if (flow_num > 0){
        ReadFlowInput();
        if (gen_tcp_traffic){
            Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ns3::MakeBoundCallback(&ScheduleFlowInputsTcp, fct_output));
        }
        else
            Simulator::Schedule(Seconds(flow_input.start_time)-Simulator::Now(), ScheduleFlowInputs);
    }
    
    topof.close();
	tracef.close();

	// schedule link down
	if (link_down_time > 0){
		Simulator::Schedule(Seconds(2) + MicroSeconds(link_down_time), &TakeDownLink, n, n.Get(link_down_A), n.Get(link_down_B));
	}

	// schedule buffer monitor
	FILE* qlen_output = fopen(qlen_mon_file.c_str(), "w");
	Simulator::Schedule(NanoSeconds(qlen_mon_start), &monitor_buffer, qlen_output, &n);

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();
	//
	// Now, do the actual simulation.
	//
    std::cout << "Running Simulation.\n";
    fflush(stdout);
    NS_LOG_INFO("Run Simulation.");
    Simulator::Schedule(MilliSeconds(log_time_interval), &PrintProgress, MilliSeconds(log_time_interval));
    Simulator::Stop(Seconds(simulator_stop_time));
    Simulator::Run();
    Simulator::Destroy();
    NS_LOG_INFO("Done.");
    fclose(trace_output);

	endt = clock();
	std::cout << (double)(endt - begint) / CLOCKS_PER_SEC << "\n";

}