#!/usr/bin/env python3
"""Ryu OpenFlow 1.3 collector and learning switch for the controlled lab.

Automatic blocking is disabled unless config/config.yaml enables it AND
GNN_SDN_MITIGATION=1 is set in the controller environment.
"""
import csv
import ipaddress
import json
import os
import time

import yaml
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    CONFIG_DISPATCHER,
    DEAD_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls,
)
from ryu.lib import hub
from ryu.lib.packet import ethernet, ipv4, packet, tcp, udp
from ryu.ofproto import ofproto_v1_3

OUTPUT = os.path.join("data", "raw", "flow_stats.csv")
DECISIONS = os.path.join("data", "processed", "decisions.jsonl")
LAB_NETWORK = ipaddress.ip_network("10.0.0.0/24")


def _mitigation_settings():
    """Require explicit config and environment opt-ins; bound temporary block lifetime."""
    try:
        with open("config/config.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
        mitigation = config.get("mitigation", {})
        timeout = int(mitigation.get("block_timeout_seconds", 60))
        timeout = max(1, min(timeout, 3600))
        enabled = (
            os.getenv("GNN_SDN_MITIGATION", "0") == "1"
            and bool(mitigation.get("enabled", False))
        )
        return enabled, timeout
    except (OSError, yaml.YAMLError, AttributeError, TypeError, ValueError):
        return False, 60


class FlowStatsCollector(app_manager.RyuApp):
    """Observe flow counters and support optional short-lived lab-only blocking."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.mac_to_port = {}
        # Ignore stale decisions from previous runs; consume only newly appended rows.
        self.decision_offset = os.path.getsize(DECISIONS) if os.path.exists(DECISIONS) else 0
        self.mitigation_enabled, self.block_timeout_seconds = _mitigation_settings()
        self._ensure_output()
        if self.mitigation_enabled:
            self.logger.warning(\n                "Lab mitigation is ENABLED; IPv4 blocks expire after %d seconds",\n                self.block_timeout_seconds,\n            )
        else:
            self.logger.info("Observation/alert mode; automatic mitigation is disabled")
        self.monitor_thread = hub.spawn(self._monitor)

    @staticmethod
    def _ensure_output():
        directory = os.path.dirname(OUTPUT)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) == 0:
            with open(OUTPUT, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "timestamp", "datapath_id", "in_port", "eth_src", "eth_dst",
                    "ip_src", "ip_dst", "ip_proto", "src_port", "dst_port",
                    "packet_count", "byte_count", "duration_sec",
                ])

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        """Install a table-miss rule that sends unknown packets to the controller."""
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self._add_flow(datapath, priority=0, match=parser.OFPMatch(), actions=actions)
        self.logger.info("Installed table-miss rule: dpid=%s", datapath.id)

    @staticmethod
    def _add_flow(datapath, priority, match, actions, hard_timeout=0):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        instructions = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        modification = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
            hard_timeout=hard_timeout,
        )
        datapath.send_msg(modification)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
            self.mac_to_port.setdefault(datapath.id, {})
            self.logger.info("Switch connected: dpid=%s", datapath.id)
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)
            self.mac_to_port.pop(datapath.id, None)
            self.logger.info("Switch disconnected: dpid=%s", datapath.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """Learn MAC locations and install forwarding matches with L3/L4 fields."""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == 0x88CC:
            return

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port
        out_port = self.mac_to_port[dpid].get(eth.dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match_fields = {
                "in_port": in_port,
                "eth_dst": eth.dst,
                "eth_src": eth.src,
            }
            ip_packet = pkt.get_protocol(ipv4.ipv4)
            tcp_segment = pkt.get_protocol(tcp.tcp)
            udp_segment = pkt.get_protocol(udp.udp)
            if ip_packet is not None:
                match_fields.update({
                    "eth_type": 0x0800,
                    "ipv4_src": ip_packet.src,
                    "ipv4_dst": ip_packet.dst,
                    "ip_proto": ip_packet.proto,
                })
                if tcp_segment is not None:
                    match_fields.update({
                        "tcp_src": tcp_segment.src_port,
                        "tcp_dst": tcp_segment.dst_port,
                    })
                elif udp_segment is not None:
                    match_fields.update({
                        "udp_src": udp_segment.src_port,
                        "udp_dst": udp_segment.dst_port,
                    })
            self._add_flow(
                datapath, priority=10, match=parser.OFPMatch(**match_fields), actions=actions
            )

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        packet_out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(packet_out)

    def _monitor(self):
        while True:
            for datapath in list(self.datapaths.values()):
                self._request_stats(datapath)
            if self.mitigation_enabled and self.datapaths:
                self._consume_decisions()
            hub.sleep(5)

    @staticmethod
    def _request_stats(datapath):
        parser = datapath.ofproto_parser
        datapath.send_msg(parser.OFPFlowStatsRequest(datapath))

    def _consume_decisions(self):
        """Apply new block_source decisions only to hosts in the lab subnet."""
        if not os.path.exists(DECISIONS):
            return
        try:
            with open(DECISIONS, "rb") as handle:
                handle.seek(self.decision_offset)
                pending = handle.read()
                self.decision_offset = handle.tell()
            for raw_line in pending.decode("utf-8", errors="replace").splitlines():
                if not raw_line.strip():
                    continue
                try:
                    decision = json.loads(raw_line)
                except json.JSONDecodeError:
                    self.logger.warning("Skipping invalid decision JSON line")
                    continue
                if decision.get("action") != "block_source":
                    continue
                try:
                    address = ipaddress.ip_address(decision.get("source_ip", ""))
                except ValueError:
                    self.logger.warning("Skipping decision with invalid source IP")
                    continue
                if address not in LAB_NETWORK:
                    self.logger.error("Refusing to block non-lab source %s", address)
                    continue
                self._block_lab_source(str(address), float(decision.get("score", 0)))
        except OSError:
            self.logger.exception("Could not read decision queue")

    def _block_lab_source(self, source_ip, score):
        """Install a temporary drop rule for one source IP on lab datapaths."""
        for datapath in list(self.datapaths.values()):
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=source_ip)
            self._add_flow(
                datapath,
                priority=100,
                match=match,
                actions=[],
                hard_timeout=self.block_timeout_seconds,
            )
        self.logger.warning(
            "Temporary lab block installed for %s (score=%.3f, timeout=%ss)",
            source_ip,
            score,
        )

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        timestamp = time.time()
        with open(OUTPUT, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for stat in ev.msg.body:
                match = stat.match
                writer.writerow([
                    timestamp,
                    ev.msg.datapath.id,
                    match.get("in_port", ""),
                    match.get("eth_src", ""),
                    match.get("eth_dst", ""),
                    match.get("ipv4_src", ""),
                    match.get("ipv4_dst", ""),
                    match.get("ip_proto", ""),
                    match.get("tcp_src", match.get("udp_src", "")),
                    match.get("tcp_dst", match.get("udp_dst", "")),
                    stat.packet_count,
                    stat.byte_count,
                    stat.duration_sec + stat.duration_nsec / 1e9,
                ])
        self.logger.info(
            "Collected flow stats: dpid=%s entries=%d",
            ev.msg.datapath.id,
            len(ev.msg.body),
        )
