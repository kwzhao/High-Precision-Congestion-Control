#ifndef UTILS_HPP
#define UTILS_HPP

#include "trace-format.h"

typedef uint64_t FlowInt;

// Map to store the transmitted size for each active flow
std::map<uint32_t, uint32_t> activeFlows;

static uint32_t GetDevInt(uint16_t node, uint8_t intf){
	return ((uint32_t)node << 8) | intf;
}
struct Device{
	uint16_t node;
	uint8_t intf;

	Device(uint16_t _node, uint8_t _intf): node(_node), intf(_intf) {}
	uint32_t GetDevInt(){
		return ::GetDevInt(node, intf);
	}
};

static inline bool IsFlow(ns3::TraceFormat &tr){
	return tr.l3Prot == 0x6 || tr.l3Prot == 0x11 || tr.l3Prot == 0xFC || tr.l3Prot == 0xFD || tr.l3Prot == 0x0;
}

static inline FlowInt GetFlowInt(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport){
	FlowInt res;
	uint64_t src = (sip >> 8) & 0xffff, dst = (dip >> 8) & 0xffff;
	res = ((src << 16) | dst);
	res = (((res << 16) | sport) << 16) | dport;
	return res;
}
static inline FlowInt GetFlowInt(ns3::TraceFormat &tr){
	switch (tr.l3Prot){
		case 0x6:
		case 0x11:
			return GetFlowInt(tr.sip, tr.dip, tr.data.sport, tr.data.dport);
		case 0xFC: // ACK
		case 0xFD: // NACK
			return GetFlowInt(tr.sip, tr.dip, tr.ack.sport, tr.ack.dport);
		case 0x0: // QpAv
			return GetFlowInt(tr.sip, tr.dip, tr.qp.sport, tr.qp.dport);
		default:
			return GetFlowInt(tr.sip, tr.dip, 0, 0);
	}
}
static inline FlowInt GetReverseFlowInt(ns3::TraceFormat &tr){
	switch (tr.l3Prot){
		case 0x6:
		case 0x11:
			return GetFlowInt(tr.dip, tr.sip, tr.data.dport, tr.data.sport);
		case 0xFC: // ACK
		case 0xFD: // NACK
			return GetFlowInt(tr.dip, tr.sip, tr.ack.dport, tr.ack.sport);
		case 0x0: // QpAv
			return GetFlowInt(tr.dip, tr.sip, tr.qp.dport, tr.qp.sport);
		default:
			return GetFlowInt(tr.dip, tr.sip, 0, 0);
	}
}

// Return the forward direction FlowInt for data, and reverse FlowInt for ACK
static inline FlowInt GetStandardFlowInt(ns3::TraceFormat &tr){
	if (tr.l3Prot == 0xFC || tr.l3Prot == 0xFD)
		return GetReverseFlowInt(tr);
	else
		return GetFlowInt(tr);
}

static inline char l3ProtToChar(uint8_t p){
	switch (p){
		case 0x6:
			return 'T';
		case 0x11:
			return 'U';
		case 0xFC: // ACK
			return 'A';
		case 0xFD: // NACK
			return 'N';
		case 0xFE: // PFC
			return 'P';
		case 0xFF:
			return 'C';
		default:
			return 'X';
	}
}

static inline void InitFlowTransmittedSize(uint32_t flowId) {
    
	activeFlows[flowId] = 0; // First packet for this flow
}
// Update the transmitted size for each flow
static inline void UpdateFlowTransmittedSize(uint32_t flowId, uint32_t packetSize) {
	activeFlows[flowId] += packetSize;
}
static inline void RemoveFlowTransmittedSize(uint32_t flowId) {
	activeFlows.erase(flowId);
}

static inline void PrintActiveFlows() {
	if (activeFlows.empty()) {
		printf("0\n");
	}
	else {
		// printf("%u,", activeFlows.size());
		for (const auto& flow : activeFlows) {
			printf("%u:%u,", flow.first, flow.second);
			// printf("%u,", flow.second);
		}
		printf("\n");
	}
}

static inline void print_trace(ns3::TraceFormat &tr){
	if (tr.queueEvent==0){
		UpdateFlowTransmittedSize(tr.flowId, tr.data.payload);
		return;
	}
	else if (tr.queueEvent==2){
		UpdateFlowTransmittedSize(tr.flowId, tr.data.payload);
		PrintActiveFlows();
		RemoveFlowTransmittedSize(tr.flowId);
	}
	else{
		PrintActiveFlows();
	}
	if (tr.queueEvent==1){
		InitFlowTransmittedSize(tr.flowId);
	}
	// if (tr.flowId<38477){
	// 	return;
	// }
	return;
	switch (tr.l3Prot){
		case 0x6:
		case 0x11:
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %hu %hu %c %u %lu %u %hu(%hu) %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, tr.data.sport, tr.data.dport, l3ProtToChar(tr.l3Prot), tr.data.seq, tr.data.ts, tr.data.pg, tr.size, tr.data.payload, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		case 0xFC: // ACK
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %u %u %c 0x%02X %u %u %lu %hu %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, tr.ack.sport, tr.ack.dport, l3ProtToChar(tr.l3Prot), tr.ack.flags, tr.ack.pg, tr.ack.seq, tr.ack.ts, tr.size, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		case 0xFD: // NACK
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %u %u %c 0x%02X %u %u %lu %hu %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, tr.ack.sport, tr.ack.dport, l3ProtToChar(tr.l3Prot), tr.ack.flags, tr.ack.pg, tr.ack.seq, tr.ack.ts, tr.size, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		case 0xFE: // PFC
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %c %u %u %u %hu %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, l3ProtToChar(tr.l3Prot), tr.pfc.time, tr.pfc.qlen, tr.pfc.qIndex, tr.size, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		case 0xFF: // CNP
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %c %u %u %u %u %u %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, l3ProtToChar(tr.l3Prot), tr.cnp.fid, tr.cnp.qIndex, tr.cnp.ecnBits, tr.cnp.seq, tr.size, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		case 0x0: // QpAv
			printf("%lu n:%u %u:%u %s %08x %08x %u %u %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, EventToStr((ns3::PEvent)tr.event), tr.sip, tr.dip, tr.qp.sport, tr.qp.dport, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
		default:
			printf("%lu n:%u %u:%u %u %s ecn:%x %08x %08x %x %u %u %x %u", tr.time, tr.node, tr.intf, tr.qidx, tr.qlen, EventToStr((ns3::PEvent)tr.event), tr.ecn, tr.sip, tr.dip, tr.l3Prot, tr.size, tr.flowId, tr.queueEvent, tr.nActiveFlows);
			break;
	}
	printf("\n");
}

#endif /* UTILS_HPP */
