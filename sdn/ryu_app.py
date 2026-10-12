#!/usr/bin/env python3
"""Ryu application for OpenFlow 1.3 observation and flow statistics.

The application is intentionally limited to observation in this phase.
No automatic blocking or quarantine is performed.
"""
import csv
import os
import time

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    CONFIG_DISPATCHER,
    DEAD_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls,
)
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub


OUTPUT = os.path.join("data", "raw", "flow_stats.csv")


class FlowStatsCollector(app_manager.RyuApp):
    """Observe switches and periodically export OpenFlow flow counters."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self._ensure_output()
        self.monitor_thread = hub.spawn(self._monitor)

    @staticmethod
    def _ensure_output():
        directory = os.path.dirname(OUTPUT)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(OUTPUT) or os.path.getsize(OUTPUT) == 0:
            with open(OUTPUT, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "timestamp",
                        "datapath_id",
                        "in_port",
                        "eth_src",
                        "eth_dst",
                        "ip_src",
                        "ip_dst",
                        "ip_proto",
                        "src_port",
                        "dst_port",
                        "packet_count",
                        "byte_count",
                        "duration_sec",
                    ]
                )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        """Install a table-miss rule that sends unknown packets to the controller."""
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER,
            )
        ]
        match = parser.OFPMatch()
        self._add_flow(datapath, priority=0, match=match, actions=actions)

        self.logger.info("Installed table-miss rule: dpid=%s", datapath.id)

    @staticmethod
    def _add_flow(datapath, priority, match, actions):
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
        )
        datapath.send_msg(modification)

    @set_ev_cls(
        ofp_event.EventOFPStateChange,
        [MAIN_DISPATCHER, DEAD_DISPATCHER],
    )
    def _state_change_handler(self, ev):
        datapath = ev.datapath

        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
            self.logger.info("Switch connected: dpid=%s", datapath.id)
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(datapath.id, None)
            self.logger.info("Switch disconnected: dpid=%s", datapath.id)

    def _monitor(self):
        while True:
            for datapath in list(self.datapaths.values()):
                self._request_stats(datapath)
            hub.sleep(5)

    @staticmethod
    def _request_stats(datapath):
        parser = datapath.ofproto_parser
        request = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(request)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        timestamp = time.time()

        with open(OUTPUT, "a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)

            for stat in ev.msg.body:
                match = stat.match
                writer.writerow(
                    [
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
                    ]
                )

        self.logger.info(
            "Collected flow stats: dpid=%s entries=%d",
            ev.msg.datapath.id,
            len(ev.msg.body),
        )
