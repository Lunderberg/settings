"""
Usage:

from tvm_utils import TimeTransforms
with tvm.transform.PassContext(instruments=[TimeTransforms()]):
    lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)

from tvm_utils import TimeTransforms
with TimeTransforms.context():
    lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)

import pytest
@pytest.fixture(autouse=True)
def very_verbose():
    from tvm_utils import TimeTransforms
    context = TimeTransforms.context()
    with context:
        yield
"""

import datetime
import dataclasses
import enum
import time
from typing import Optional, List, Iterable, Dict, Any

import tvm
from tvm.ir.instrument import pass_instrument


class EventType(enum.Enum):
    Start = enum.auto()
    Stop = enum.auto()


@dataclasses.dataclass
class Event:
    type: EventType
    perf_counter_ns: int
    timestamp: datetime.datetime
    name: str


@dataclasses.dataclass
class Window:
    name: str
    begin_timestamp: datetime.datetime
    end_timestamp: datetime.datetime
    begin_perf_counter_ns: int
    end_perf_counter_ns: int

    parent: Optional["Window"] = None
    children: List["Window"] = dataclasses.field(default_factory=list)

    def iter_recursive(self):
        yield self
        for child in self.children:
            yield from child.iter_recursive()

    @property
    def duration_inclusive_ns(self) -> int:
        return self.end_perf_counter_ns - self.begin_perf_counter_ns

    @property
    def duration_inclusive(self) -> datetime.timedelta:
        return datetime.timedelta(microseconds=self.duration_inclusive_ns / 1e3)

    @property
    def duration_exclusive_ns(self) -> int:
        def transitions():
            yield self.begin_perf_counter_ns
            for child in self.children:
                yield child.begin_perf_counter_ns
                yield child.end_perf_counter_ns
            yield self.end_perf_counter_ns

        iter_transitions = transitions()

        return sum(
            stop - start
            for (start, stop) in
            # Zip trick can be replaced with
            # `itertools.batched(transitions(), 2)`, for python 3.12
            # onward.
            zip(iter_transitions, iter_transitions)
        )

    @property
    def duration_exclusive(self) -> datetime.timedelta:
        return datetime.timedelta(microseconds=self.duration_exclusive_ns / 1e3)


def format_timedelta(delta: datetime.timedelta):
    rem = delta.total_seconds()

    if rem > 86400:
        out_format = "{days:d}d{hours:02d}h{minutes:02d}m{seconds:02d}s"
    elif rem > 3600:
        out_format = "{hours:d}h{minutes:02d}m{seconds:02d}s"
    elif rem > 60:
        out_format = "{minutes:d}m{seconds:02d}s"
    else:
        out_format = "{seconds:d}.{ms:03d}s"

    days = int(rem // 86400)
    rem -= days * 86400

    hours = int(rem // 3600)
    rem -= hours * 3600

    minutes = int(rem // 60)
    rem -= minutes * 60

    seconds = int(rem)
    rem -= seconds

    ms = int(rem * 1000)
    rem -= ms / 1000

    return out_format.format(
        days=days, hours=hours, minutes=minutes, seconds=seconds, ms=ms
    )


@pass_instrument
class TimeTransforms:
    def __init__(self):
        """Construct the TVM Instrument"""
        self.events = []
        self.current_depth = 0

    @classmethod
    def context(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        return tvm.transform.PassContext(instruments=[obj])

    def enter_pass_ctx(self):
        if self.current_depth == 0:
            self._append_event(EventType.Start, "other")

    def exit_pass_ctx(self):
        if self.current_depth == 0:
            self._append_event(EventType.Stop, "other")
            self.print_summary()

    def run_before_pass(self, mod, info):
        self.current_depth += 1
        self._append_event(EventType.Start, info.name)

    def run_after_pass(self, mod, info):
        self._append_event(EventType.Stop, info.name)
        self.current_depth -= 1

    def _append_event(self, event_type: EventType, name: str):
        event = Event(
            type=event_type,
            perf_counter_ns=time.perf_counter_ns(),
            timestamp=datetime.datetime.now(),
            name=name,
        )
        self.events.append(event)

    def get_nested_pipeline(self):
        assert (
            self.current_depth == 0
        ), "get_nested_pipeline() may only be called after the pipeline completes"

        window = None
        for i, event in enumerate(self.events):
            assert window is not None or event.type == EventType.Start

            if event.type == EventType.Start:
                parent = window
                window = Window(
                    name=event.name,
                    begin_timestamp=event.timestamp,
                    begin_perf_counter_ns=event.perf_counter_ns,
                    end_timestamp=None,
                    end_perf_counter_ns=None,
                    parent=parent,
                    children=[],
                )
                if parent is not None:
                    parent.children.append(window)

            elif event.type == EventType.Stop:
                assert event.name == window.name
                window.end_timestamp = event.timestamp
                window.end_perf_counter_ns = event.perf_counter_ns

                if window.parent is None:
                    assert i + 1 == len(self.events)
                else:
                    window = window.parent

        return window

    def get_stats_by_transform(self):
        window = self.get_nested_pipeline()

        windows = [
            {
                "name": window.name,
                "duration_inclusive_ns": window.duration_inclusive_ns,
                "duration_exclusive_ns": window.duration_exclusive_ns,
                "duration_inclusive": window.duration_inclusive,
                "duration_exclusive": window.duration_exclusive,
            }
            for window in window.iter_recursive()
        ]

        grouped_windows = []
        grouped_window_lookup = {}
        for row in windows:
            if row["name"] == "other":
                continue

            group_index = grouped_window_lookup.get(row["name"])
            if group_index is None:
                group_index = len(grouped_windows)
                grouped_window_lookup[row["name"]] = group_index
                grouped_windows.append(
                    {
                        "name": row["name"],
                        "duration_inclusive_ns": 0,
                        "duration_exclusive_ns": 0,
                        "num_uses": 0,
                    }
                )

            group = grouped_windows[group_index]
            group["duration_inclusive_ns"] += row["duration_inclusive_ns"]
            group["duration_exclusive_ns"] += row["duration_exclusive_ns"]
            group["num_uses"] += 1

        for group in grouped_windows:
            group["duration_inclusive"] = datetime.timedelta(
                microseconds=group["duration_inclusive_ns"] / 1e3
            )
            group["duration_exclusive"] = datetime.timedelta(
                microseconds=group["duration_exclusive_ns"] / 1e3
            )

        grouped_windows.sort(
            key=lambda group: group["duration_exclusive_ns"], reverse=True
        )

        return grouped_windows

    def print_summary(self, sort_by="duration_exclusive", num_rows=10):
        grouped_windows = self.get_stats_by_transform()

        table = [
            {
                "Transform": group["name"],
                "Num. uses": str(group["num_uses"]),
                "Exc. Time": format_timedelta(group["duration_exclusive"]),
                "Inc. Time": format_timedelta(group["duration_inclusive"]),
            }
            for group in grouped_windows[:10]
        ]

        col_names = list({key: None for row in table for key in row})

        col_widths = {
            name: max(len(name), max(len(row[name]) for row in table))
            for name in col_names
        }

        table_str: List[str] = []

        strong_separator = "+".join(
            ["", *("=" * (col_widths[name] + 2) for name in col_names), ""]
        )
        weak_separator = "+".join(
            ["", *("-" * (col_widths[name] + 2) for name in col_names), ""]
        )

        table_str.append(weak_separator)
        table_str.append(
            "|".join(["", *(f" {name:{col_widths[name]}} " for name in col_names), ""])
        )
        table_str.append(weak_separator)
        for i, row in enumerate(table):
            table_str.append(
                "|".join(
                    [
                        "",
                        *(f" {row[name]:<{col_widths[name]}} " for name in col_names),
                        "",
                    ]
                )
            )

            if (i + 1) % 5 == 0:
                table_str.append(weak_separator)

        print("\n".join(table_str))
