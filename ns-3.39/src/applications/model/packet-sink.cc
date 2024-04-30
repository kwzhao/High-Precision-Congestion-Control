/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright 2007 University of Washington
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
 *
 * Author:  Tom Henderson (tomhend@u.washington.edu)
 */
#include "ns3/address.h"
#include "ns3/address-utils.h"
#include "ns3/log.h"
#include "ns3/inet-socket-address.h"
#include "ns3/inet6-socket-address.h"
#include "ns3/node.h"
#include "ns3/socket.h"
#include "ns3/udp-socket.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/packet.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/udp-socket-factory.h"
#include "packet-sink.h"
#include "ns3/boolean.h"
#include "ns3/ipv4-packet-info-tag.h"
#include "ns3/ipv6-packet-info-tag.h"
#include "ns3/flow-id-tag.h"
/* Modification */
#include "ns3/uinteger.h"
/* Modification */

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("PacketSink");

NS_OBJECT_ENSURE_REGISTERED (PacketSink);

TypeId 
PacketSink::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::PacketSink")
    .SetParent<Application> ()
    .SetGroupName("Applications")
    .AddConstructor<PacketSink> ()
    .AddAttribute ("Local",
                   "The Address on which to Bind the rx socket.",
                   AddressValue (),
                   MakeAddressAccessor (&PacketSink::m_local),
                   MakeAddressChecker ())
    .AddAttribute ("LocalTag",
                   "The Address on which to Bind the rx socket.",
                   AddressValue (),
                   MakeAddressAccessor (&PacketSink::m_local_tag),
                   MakeAddressChecker ())
    .AddAttribute ("Protocol",
                   "The type id of the protocol to use for the rx socket.",
                   TypeIdValue (UdpSocketFactory::GetTypeId ()),
                   MakeTypeIdAccessor (&PacketSink::m_tid),
                   MakeTypeIdChecker ())
    .AddAttribute ("EnableSeqTsSizeHeader",
                   "Enable optional header tracing of SeqTsSizeHeader",
                   BooleanValue (false),
                   MakeBooleanAccessor (&PacketSink::m_enableSeqTsSizeHeader),
                   MakeBooleanChecker ())
    /* Modification */
    .AddAttribute ("TotalQueryBytes","Query Bytes after which application closes",UintegerValue (0),
          MakeUintegerAccessor (&PacketSink::TotalQueryBytes),
          MakeUintegerChecker<uint64_t> ())

    .AddAttribute ("recvAt", "recvAtTime", TimeValue (Seconds (0.0)),
          MakeTimeAccessor (&PacketSink::m_recvAt),
          MakeTimeChecker ())

    .AddAttribute  ("priority","priority of all sockets created by this sink", UintegerValue(0),
            MakeUintegerAccessor(&PacketSink::priority), MakeUintegerChecker<uint32_t>())

    .AddAttribute ("priorityCustom","priority of sent packets",UintegerValue (1),
                  MakeUintegerAccessor (&PacketSink::m_priorCustom),
                  MakeUintegerChecker<uint8_t> ())

    .AddAttribute  ("flowId","flowId mainly intended for ack packets. This will be passed to tcp socket base", UintegerValue(2),
                        MakeUintegerAccessor(&PacketSink::flowId), MakeUintegerChecker<uint32_t>())
    .AddAttribute  ("senderPriority","senderPriority. This is just to get FCT with corresponding priority in the stats", UintegerValue(2),
                        MakeUintegerAccessor(&PacketSink::sender_priority), MakeUintegerChecker<uint32_t>())
    /* Modification */
    .AddTraceSource ("Rx",
                     "A packet has been received",
                     MakeTraceSourceAccessor (&PacketSink::m_rxTrace),
                     "ns3::Packet::AddressTracedCallback")
    .AddTraceSource ("RxWithAddresses", "A packet has been received",
                     MakeTraceSourceAccessor (&PacketSink::m_rxTraceWithAddresses),
                     "ns3::Packet::TwoAddressTracedCallback")
    .AddTraceSource ("RxWithSeqTsSize",
                     "A packet with SeqTsSize header has been received",
                     MakeTraceSourceAccessor (&PacketSink::m_rxTraceWithSeqTsSize),
                     "ns3::PacketSink::SeqTsSizeCallback")
    .AddTraceSource ("FlowFinish", "end of flow ",
                     MakeTraceSourceAccessor (&PacketSink::m_flowFinishTrace),
                     "ns3::Packet::TracedCallback")
  ;
  return tid;
}

PacketSink::PacketSink ()
{
  NS_LOG_FUNCTION (this);
  m_socket = 0;
  m_totalRx = 0;
}

PacketSink::~PacketSink()
{
  NS_LOG_FUNCTION (this);
}

uint64_t PacketSink::GetTotalRx () const
{
  NS_LOG_FUNCTION (this);
  return m_totalRx;
}

Ptr<Socket>
PacketSink::GetListeningSocket (void) const
{
  NS_LOG_FUNCTION (this);
  return m_socket;
}

std::list<Ptr<Socket> >
PacketSink::GetAcceptedSockets (void) const
{
  NS_LOG_FUNCTION (this);
  return m_socketList;
}

void PacketSink::DoDispose (void)
{
  NS_LOG_FUNCTION (this);
  m_socket = 0;
  m_socketList.clear ();

  // chain up
  Application::DoDispose ();
}


// Application Methods
void PacketSink::StartApplication ()    // Called at time specified by Start
{
  NS_LOG_FUNCTION (this);
  // Create the socket if not already
  if (!m_socket)
    {
      m_socket = Socket::CreateSocket (GetNode (), m_tid);
      /* Modification */
      m_socket->SetPriority(priority);
      m_socket->SetAttribute("flowId",UintegerValue(flowId));
      m_socket->SetAttribute("mypriority",UintegerValue(m_priorCustom));
      /* Modification */
      if (m_socket->Bind (m_local) == -1)
        {
          NS_FATAL_ERROR ("Failed to bind socket");
        }
      /* Modification */
      m_socket->SetPriority(priority);
      m_socket->SetAttribute("flowId",UintegerValue(flowId));
      m_socket->SetAttribute("mypriority",UintegerValue(m_priorCustom));
      /* Modification */
      m_socket->Listen ();
      m_socket->ShutdownSend ();
      if (addressUtils::IsMulticast (m_local))
        {
          Ptr<UdpSocket> udpSocket = DynamicCast<UdpSocket> (m_socket);
          if (udpSocket)
            {
              // equivalent to setsockopt (MCAST_JOIN_GROUP)
              udpSocket->MulticastJoinGroup (0, m_local);
            }
          else
            {
              NS_FATAL_ERROR ("Error: joining multicast on a non-UDP socket");
            }
        }
    }

  if (InetSocketAddress::IsMatchingType (m_local))
    {
      m_localPort = InetSocketAddress::ConvertFrom (m_local).GetPort ();
    }
  else if (Inet6SocketAddress::IsMatchingType (m_local))
    {
      m_localPort = Inet6SocketAddress::ConvertFrom (m_local).GetPort ();
    }
  else
    {
      m_localPort = 0;
    }

  /* Modification */
      m_socket->SetPriority(priority);
      m_socket->SetAttribute("flowId",UintegerValue(flowId));
      m_socket->SetAttribute("mypriority",UintegerValue(m_priorCustom));
  /* Modification */
  m_socket->SetRecvCallback (MakeCallback (&PacketSink::HandleRead, this));
  m_socket->SetRecvPktInfo (true);
  m_socket->SetAcceptCallback (
    MakeNullCallback<bool, Ptr<Socket>, const Address &> (),
    MakeCallback (&PacketSink::HandleAccept, this));
  m_socket->SetCloseCallbacks (
    MakeCallback (&PacketSink::HandlePeerClose, this),
    MakeCallback (&PacketSink::HandlePeerError, this));
}

void PacketSink::StopApplication ()     // Called at time specified by Stop
{
  NS_LOG_FUNCTION (this);
  while(!m_socketList.empty ()) //these are accepted sockets, close them
    {
      Ptr<Socket> acceptedSocket = m_socketList.front ();
      m_socketList.pop_front ();
      acceptedSocket->Close ();
    }
  if (m_socket) 
    {
      m_socket->Close ();
      m_socket->SetRecvCallback (MakeNullCallback<void, Ptr<Socket> > ());
    }
}

void PacketSink::HandleRead (Ptr<Socket> socket)
{
  NS_LOG_FUNCTION (this << socket);
  Ptr<Packet> packet;
  Address from;
  Address localAddress;
  while ((packet = socket->RecvFrom (from)))
    {
      if (packet->GetSize () == 0)
        { //EOF
          break;
        }
      // FlowIdTag tag;
      // uint32_t flowIdTmp = flowId;
      // if (packet->PeekPacketTag (tag))
      // {
      //     printf("FlowIdTag found\n");
      //     // Extract the flow ID from the packet
      //     flowIdTmp = tag.GetFlowId();
      // }
      m_totalRx += packet->GetSize ();
      if (InetSocketAddress::IsMatchingType (from))
        {
          NS_LOG_INFO ("At time " << Simulator::Now ().As (Time::S)
                       << " packet sink received "
                       <<  packet->GetSize () << " bytes from "
                       << InetSocketAddress::ConvertFrom(from).GetIpv4 ()
                       << " port " << InetSocketAddress::ConvertFrom (from).GetPort ()
                       << " total Rx " << m_totalRx << " bytes");
        }
      else if (Inet6SocketAddress::IsMatchingType (from))
        {
          NS_LOG_INFO ("At time " << Simulator::Now ().As (Time::S)
                       << " packet sink received "
                       <<  packet->GetSize () << " bytes from "
                       << Inet6SocketAddress::ConvertFrom(from).GetIpv6 ()
                       << " port " << Inet6SocketAddress::ConvertFrom (from).GetPort ()
                       << " total Rx " << m_totalRx << " bytes");
        }

      if (!m_rxTrace.IsEmpty () || !m_rxTraceWithAddresses.IsEmpty () ||
          (!m_rxTraceWithSeqTsSize.IsEmpty () && m_enableSeqTsSizeHeader))
        {
          Ipv4PacketInfoTag interfaceInfo;
          Ipv6PacketInfoTag interface6Info;
          if (packet->RemovePacketTag (interfaceInfo))
            {
              localAddress = InetSocketAddress (interfaceInfo.GetAddress (), m_localPort);
            }
          else if (packet->RemovePacketTag (interface6Info))
            {
              localAddress = Inet6SocketAddress (interface6Info.GetAddress (), m_localPort);
            }
          else
            {
              socket->GetSockName (localAddress);
            }
          m_rxTrace (packet, from);
          m_rxTraceWithAddresses (packet, from, localAddress);

          if (!m_rxTraceWithSeqTsSize.IsEmpty () && m_enableSeqTsSizeHeader)
            {
              PacketReceived (packet, from, localAddress);
            }
        }
      /* Modification */
      if(TotalQueryBytes){
        if(m_totalRx >= TotalQueryBytes){
          double totalSize = m_totalRx ;//+ ((m_totalRx-1)/(1400.0)+1)*(64); // TODO: Add header sizes more precisely.
          if (m_recvAt.GetSeconds()!=0){
            m_flowFinishTrace(totalSize, m_recvAt.GetNanoSeconds(),true,sender_priority,flowId,InetSocketAddress::ConvertFrom(from),InetSocketAddress::ConvertFrom(m_local_tag));
          }
          else{
            m_flowFinishTrace(totalSize, m_startTime.GetNanoSeconds(),false,sender_priority,flowId,InetSocketAddress::ConvertFrom(from),InetSocketAddress::ConvertFrom(m_local_tag));
            // std::cout << "Flow finished. FCT = " << Simulator::Now().GetSeconds()-m_startTime.GetSeconds() << " seconds" << std::endl;
          }
          StopApplication();
        }
      }
      /* Modification */
    }
}

void
PacketSink::PacketReceived (const Ptr<Packet> &p, const Address &from,
                            const Address &localAddress)
{
  SeqTsSizeHeader header;
  Ptr<Packet> buffer;

  auto itBuffer = m_buffer.find (from);
  if (itBuffer == m_buffer.end ())
    {
      itBuffer = m_buffer.insert (std::make_pair (from, Create<Packet> (0))).first;
    }

  buffer = itBuffer->second;
  buffer->AddAtEnd (p);
  buffer->PeekHeader (header);

  NS_ABORT_IF (header.GetSize () == 0);

  while (buffer->GetSize () >= header.GetSize ())
    {
      NS_LOG_DEBUG ("Removing packet of size " << header.GetSize () << " from buffer of size " << buffer->GetSize ());
      Ptr<Packet> complete = buffer->CreateFragment (0, static_cast<uint32_t> (header.GetSize ()));
      buffer->RemoveAtStart (static_cast<uint32_t> (header.GetSize ()));

      complete->RemoveHeader (header);

      m_rxTraceWithSeqTsSize (complete, from, localAddress, header);

      if (buffer->GetSize () > header.GetSerializedSize ())
        {
          buffer->PeekHeader (header);
        }
      else
        {
          break;
        }
    }
}

void PacketSink::HandlePeerClose (Ptr<Socket> socket)
{
  NS_LOG_FUNCTION (this << socket);
}
 
void PacketSink::HandlePeerError (Ptr<Socket> socket)
{
  NS_LOG_FUNCTION (this << socket);
}

void PacketSink::HandleAccept (Ptr<Socket> s, const Address& from)
{
  NS_LOG_FUNCTION (this << s << from);
  /* Modification */
    s->SetPriority(priority);
    s->SetAttribute("flowId",UintegerValue(flowId));
    s->SetAttribute("mypriority",UintegerValue(m_priorCustom));
  /* Modification */
  s->SetRecvCallback (MakeCallback (&PacketSink::HandleRead, this));
  m_socketList.push_back (s);
}

} // Namespace ns3