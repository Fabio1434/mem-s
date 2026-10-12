"""Shared column definitions for the flow and graph pipeline."""

RAW_COLUMNS = [
    "timestamp", "datapath_id", "in_port", "eth_src", "eth_dst",
    "ip_src", "ip_dst", "ip_proto", "src_port", "dst_port",
    "packet_count", "byte_count", "duration_sec",
]

FLOW_FEATURE_COLUMNS = [
    "packets_delta", "bytes_delta", "packet_rate", "byte_rate",
    "duration_sec", "ip_proto_num", "src_port_num", "dst_port_num", "in_port_num",
]

NODE_FEATURE_NAMES = [
    "out_flows", "in_flows", "unique_destinations", "unique_sources",
    "unique_destination_ports", "packets_out", "packets_in", "bytes_out", "bytes_in",
    "packet_rate_out_mean", "byte_rate_out_mean", "duration_out_mean",
]

LABEL_COLUMNS = ["timestamp_start", "timestamp_end", "src_ip", "dst_ip", "label", "scenario"]
