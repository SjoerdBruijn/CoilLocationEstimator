#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys

from pylsl import StreamInlet, resolve_streams


def extract_marker_names(stream_info):
    names = extract_marker_names_from_markers(stream_info)
    if len(names) > 0:
        return names

    names = []
    n_channels = stream_info.channel_count()
    try:
        channels = stream_info.desc().child("channels")
        channel = channels.child("channel")
        while channel.name():
            label = (
                channel.child_value("marker")
                or channel.child_value("label")
                or channel.child_value("name")
            )
            if label:
                names.append(label)
            channel = channel.next_sibling()
    except Exception:
        names = []

    if len(names) == n_channels and n_channels % 4 == 0:
        return names[::4]
    if len(names) == n_channels and n_channels % 3 == 0:
        return names[::3]
    if len(names) > 0:
        return names

    if n_channels % 4 == 0:
        return default_marker_names(n_channels // 4)
    if n_channels % 3 == 0:
        return default_marker_names(n_channels // 3)
    return []


def extract_marker_names_from_markers(stream_info):
    names = []
    try:
        markers = stream_info.desc().child("markers")
        marker = markers.child("marker")
        while marker.name():
            label = marker.child_value("label") or marker.child_value("name")
            if label:
                names.append(label)
            marker = marker.next_sibling()
    except Exception:
        return []
    return names


def default_marker_names(n_markers):
    return [f"Marker_{i + 1}" for i in range(n_markers)]


def find_matching_stream(streams, stream_name):
    if stream_name is None:
        return streams[0] if len(streams) > 0 else None

    for stream in streams:
        if stream.name() == stream_name:
            return stream
    return None


def main():
    parser = argparse.ArgumentParser(description="Show marker names from an LSL stream.")
    parser.add_argument("--stream-name", help="Name of the LSL stream to inspect.")
    parser.add_argument(
        "--list-streams",
        action="store_true",
        help="List available streams before selecting one.",
    )
    args = parser.parse_args()

    streams = resolve_streams(wait_time=1.0)
    if len(streams) == 0:
        print("No LSL streams found.", file=sys.stderr)
        return 1

    if args.list_streams:
        print("Available streams:")
        for stream in streams:
            print(f"- {stream.name()} ({stream.type()}, {stream.channel_count()} channels)")

    stream = find_matching_stream(streams, args.stream_name)
    if stream is None:
        print(f"No LSL stream named '{args.stream_name}' was found.", file=sys.stderr)
        return 1

    inlet = StreamInlet(stream, max_buflen=1, recover=True)
    full_stream_info = inlet.info(timeout=5.0)
    marker_names = extract_marker_names(full_stream_info)
    print(f"Stream: {stream.name()}")
    print(f"Channels: {stream.channel_count()}")
    print("Marker names:")
    for marker_name in marker_names:
        print(marker_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
