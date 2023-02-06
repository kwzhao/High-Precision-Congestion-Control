/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* Copyright (c) 2006 Georgia Tech Research Corporation, INRIA
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/
#include <iostream>
#include <stdio.h>
#include "ns3/log.h"
#include "ns3/enum.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/simulator.h"
#include "drop-tail-queue.h"
#include "broadcom-egress-queue.h"

NS_LOG_COMPONENT_DEFINE("BEgressQueue");

namespace ns3 {

	NS_OBJECT_ENSURE_REGISTERED(BEgressQueue);

	TypeId BEgressQueue::GetTypeId(void)
	{
		static TypeId tid = TypeId("ns3::BEgressQueue")
			.SetParent<Queue>()
			.AddConstructor<BEgressQueue>()
			.AddAttribute("MaxBytes",
				"The maximum number of bytes accepted by this BEgressQueue.",
				DoubleValue(1000.0 * 1024 * 1024),
				MakeDoubleAccessor(&BEgressQueue::m_maxBytes),
				MakeDoubleChecker<double>())
			.AddTraceSource ("BeqEnqueue", "Enqueue a packet in the BEgressQueue. Multiple queue",
					MakeTraceSourceAccessor (&BEgressQueue::m_traceBeqEnqueue))
			.AddTraceSource ("BeqDequeue", "Dequeue a packet in the BEgressQueue. Multiple queue",
					MakeTraceSourceAccessor (&BEgressQueue::m_traceBeqDequeue))
			;

		return tid;
	}

	BEgressQueue::BEgressQueue() :
		Queue()
	{
		NS_LOG_FUNCTION_NOARGS();
		m_bytesInQueueTotal = 0;
		m_rrlast = 0;
		for (uint32_t i = 0; i < fCnt; i++)
		{
			m_bytesInQueue[i] = 0;
			m_queues.push_back(CreateObject<DropTailQueue>());
		}
		for (uint32_t i = 0; i < qCnt; i++)
		{
			m_deficit[i] = 0;
			m_quantum[i] = 512;
		}
	}

	BEgressQueue::~BEgressQueue()
	{
		NS_LOG_FUNCTION_NOARGS();
	}

	void
		BEgressQueue::SetWeights(const uint32_t weights[], const uint32_t n)
	{
		uint32_t lim = std::min(qCnt, n);
		for (uint32_t i = 0; i < lim; i++)
		{
			m_quantum[i] = weights[i];
		}
	}

	bool
		BEgressQueue::DoEnqueue(Ptr<Packet> p, uint32_t qIndex)
	{
		NS_LOG_FUNCTION(this << p);

		if (m_bytesInQueueTotal + p->GetSize() < m_maxBytes)  //infinite queue
		{
			m_queues[qIndex]->Enqueue(p);
			m_bytesInQueueTotal += p->GetSize();
			m_bytesInQueue[qIndex] += p->GetSize();
		}
		else
		{
			return false;
		}
		return true;
	}

	Ptr<Packet>
		BEgressQueue::DoDequeueRR(bool paused[]) // this is for switch only
	{
		NS_LOG_FUNCTION(this);

		if (m_bytesInQueueTotal == 0)
		{
			NS_LOG_LOGIC("Queue empty");
			return 0;
		}

		uint32_t qIndex; // final index from which to dequeue

		if (m_queues[0]->GetNPackets() > 0)
		{
			// Priority packets in queue 0 will be sent before all others
			qIndex = 0;
		}
		else
		{
			// No priority packets, so we do deficit round-robin among the
			// rest. We know there is at least one nonempty queue.
			bool can_terminate = false;
			// Searching for a queue to pop from will only terminate if there
			// is at least one nonempty queue that is unpaused.
			for (int i = 0; i < qCnt; i++)
			{
				if (paused[i])
				{
					// XXX: not positive this is the behavior we want
					m_deficit[i] = 0;
				}
				if (m_queues[i]->GetNPackets() > 0 && !paused[i])
				{
					can_terminate = true;
				}
			}
			if (!can_terminate)
			{
				NS_LOG_LOGIC("All nonempty queues are paused");
				return 0;
			}

			// Now at this point we know this loop will terminate because the
			// nonempty unpaused queue will eventually accumulate enough
			// deficit to send.
			uint32_t i = m_rrlast % qCnt;
			while (m_rrlast == (uint32_t)(-1)						// sentinel index
				   || m_queues[i]->GetNPackets() == 0				// empty queue
				   || paused[i]										// queue is paused
				   || m_queues[i]->Peek()->GetSize() > m_deficit[i] // not enough deficit
			)
			{
				m_rrlast++;
				NS_ASSERT(m_rrlast != (uint32_t)(-1)); // about to hit sentinel and wrap around
				i = m_rrlast % qCnt;
				if (m_queues[i]->GetNPackets() > 0 && !paused[i])
				{
					// We only bump deficits for queues that are active
					m_deficit[i] += m_quantum[i];
				}
			}

			// `i` now points to a valid dequeue target
			qIndex = i;
		}

		Ptr<Packet> p = m_queues[qIndex]->Dequeue();
		m_traceBeqDequeue(p, qIndex);
		m_bytesInQueueTotal -= p->GetSize();
		m_bytesInQueue[qIndex] -= p->GetSize();
		m_qlast = qIndex;

		// Update deficit
		if (m_queues[qIndex]->GetNPackets() > 0)
		{
			m_deficit[qIndex] -= p->GetSize();
		}
		else
		{
			m_deficit[qIndex] = 0;
		}

		NS_LOG_LOGIC("Popped " << p);
		NS_LOG_LOGIC("Number bytes " << m_bytesInQueueTotal);
		return p;
	}

	bool
		BEgressQueue::Enqueue(Ptr<Packet> p, uint32_t qIndex)
	{
		NS_LOG_FUNCTION(this << p);
		//
		// If DoEnqueue fails, Queue::Drop is called by the subclass
		//
		bool retval = DoEnqueue(p, qIndex);
		if (retval)
		{
			NS_LOG_LOGIC("m_traceEnqueue (p)");
			m_traceEnqueue(p);
			m_traceBeqEnqueue(p, qIndex);

			uint32_t size = p->GetSize();
			m_nBytes += size;
			m_nTotalReceivedBytes += size;

			m_nPackets++;
			m_nTotalReceivedPackets++;
		}
		return retval;
	}

	Ptr<Packet>
		BEgressQueue::DequeueRR(bool paused[])
	{
		NS_LOG_FUNCTION(this);
		Ptr<Packet> packet = DoDequeueRR(paused);
		if (packet != 0)
		{
			NS_ASSERT(m_nBytes >= packet->GetSize());
			NS_ASSERT(m_nPackets > 0);
			m_nBytes -= packet->GetSize();
			m_nPackets--;
			NS_LOG_LOGIC("m_traceDequeue (packet)");
			m_traceDequeue(packet);
		}
		return packet;
	}

	bool
		BEgressQueue::DoEnqueue(Ptr<Packet> p)	//for compatiability
	{
		std::cout << "Warning: Call Broadcom queues without priority\n";
		uint32_t qIndex = 0;
		NS_LOG_FUNCTION(this << p);
		if (m_bytesInQueueTotal + p->GetSize() < m_maxBytes)
		{
			m_queues[qIndex]->Enqueue(p);
			m_bytesInQueueTotal += p->GetSize();
			m_bytesInQueue[qIndex] += p->GetSize();
		}
		else
		{
			return false;

		}
		return true;
	}


	Ptr<Packet>
		BEgressQueue::DoDequeue(void)
	{
		NS_ASSERT_MSG(false, "BEgressQueue::DoDequeue not implemented");
		return 0;
	}


	Ptr<const Packet>
		BEgressQueue::DoPeek(void) const	//DoPeek doesn't work for multiple queues!!
	{
		std::cout << "Warning: Call Broadcom queues without priority\n";
		NS_LOG_FUNCTION(this);
		if (m_bytesInQueueTotal == 0)
		{
			NS_LOG_LOGIC("Queue empty");
			return 0;
		}
		NS_LOG_LOGIC("Number bytes " << m_bytesInQueue);
		return m_queues[0]->Peek();
	}

	uint32_t
		BEgressQueue::GetNBytes(uint32_t qIndex) const
	{
		return m_bytesInQueue[qIndex];
	}


	uint32_t
		BEgressQueue::GetNBytesTotal() const
	{
		return m_bytesInQueueTotal;
	}

	uint32_t
		BEgressQueue::GetLastQueue()
	{
		return m_qlast;
	}

}
