# Copyright 201-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# ------------------------------------------------------------------------------
# CONTROLLER PACKET-IN/OUT TESTS
#
# To run all tests:
#     make packetio
# ------------------------------------------------------------------------------

from ptf.testutils import group

from lib.base_test import *

# ------------------------------------------------------------------------------
# P4 CONSTANTS
#
# Modify to match the content of your P4 program or P4Info file.
# ------------------------------------------------------------------------------

CPU_CLONE_SESSION_ID = 99


@group("packetio")
class PacketOutTest(P4RuntimeTest):
    """Tests controller packet-out capability by sending PacketOut messages and
    expecting a corresponding packet on the output port set in the PacketOut
    metadata.
    """

    def runTest(self):
        for pkt_type in ["tcp", "udp", "icmp", "arp", "tcpv6", "udpv6", "icmpv6"]:
            print_inline("%s ... " % pkt_type)
            pkt = getattr(testutils, "simple_%s_packet" % pkt_type)()
            self.testPacket(pkt)

    def testPacket(self, pkt):
        for outport in [self.port1, self.port2]:

            # Build PacketOut message.
            packet_out_msg = self.helper.build_packet_out(
                payload=str(pkt),
                metadata={
                    # TODO: modify metadata names to match P4 program
                    # ---- START SOLUTION ----
                    "egress_port": outport,
                    "_pad": 0
                    # ---- END SOLUTION ----
                })

            # Send message and expect packet on the given data plane port.
            self.send_packet_out(packet_out_msg)

            testutils.verify_packet(self, pkt, outport)

        # Make sure packet was forwarded only on the specified ports
        testutils.verify_no_other_packets(self)


@group("packetio")
class PacketInTest(P4RuntimeTest):
    """Tests controller packet-in capability my matching on the packet EtherType
    and cloning to the CPU port.
    """

    def runTest(self):
        for pkt_type in ["tcp", "udp", "icmp", "arp", "tcpv6", "udpv6", "icmpv6"]:
            print_inline("%s ... " % pkt_type)
            pkt = getattr(testutils, "simple_%s_packet" % pkt_type)()
            self.testPacket(pkt)

    @autocleanup
    def testPacket(self, pkt):

        # Insert clone to CPU session
        self.insert_pre_clone_session(
            session_id=CPU_CLONE_SESSION_ID,
            ports=[self.cpu_port])

        # Match on the given pkt's EtherType
        eth_type = pkt[Ether].type
        self.insert(self.helper.build_table_entry(
            table_name="FabricIngress.acl",
            match_fields={
                # Ternary match.
                "hdr.ethernet.ether_type": (eth_type, 0xffff)
            },
            action_name="FabricIngress.clone_to_cpu",
            priority=DEFAULT_PRIORITY
        ))

        for inport in [self.port1, self.port2, self.port3]:

            # Expected P4Runtime PacketIn message.
            exp_packet_in_msg = self.helper.build_packet_in(
                payload=str(pkt),
                metadata={
                    # TODO: modify metadata names to match P4 program
                    # ---- START SOLUTION ----
                    "ingress_port": inport,
                    "_pad": 0
                    # ---- END SOLUTION ----
                })

            # Send packet to given switch ingress port and expect P4Runtime
            # PacketIn message.
            testutils.send_packet(self, inport, str(pkt))
            self.verify_packet_in(exp_packet_in_msg)