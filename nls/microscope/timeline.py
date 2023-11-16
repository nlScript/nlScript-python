from datetime import datetime
from typing import Callable, TypeVar, Generic
from threading import Thread
from time import sleep

E = TypeVar('E')


class Timeline(Generic[E]):

    def __init__(self) -> None:
        self.timeline: dict[datetime, list[E]] = {}
        self.stop: bool = False
        self.executor: Thread | None = None

    def put(self, time: datetime, entry: E) -> None:
        if time not in self.timeline:
            self.timeline[time] = []
        self.timeline[time].append(entry)

    def runAndRemoveEntriesBefore(self, time: datetime, function: Callable[[E], None]) -> None:
        timesToRemove = []
        for entryTime in sorted(self.timeline.keys()):
            if entryTime < time:
                timesToRemove.append(entryTime)
                for entry in self.timeline[entryTime]:
                    function(entry)
            else:
                break

        for t in timesToRemove:
            del self.timeline[t]

    def process(self, function: Callable[[E], None]) -> None:
        self.stop = False
        self.executor = Thread(target=self._process_thread, args=(function,))
        self.executor.start()

    def _process_thread(self, function: Callable[[E], None]) -> None:
        while not self.stop and self.timeline:
            self.runAndRemoveEntriesBefore(datetime.now(), function)
            if not self.timeline:
                return
            sleep(1)

    def wait_for_processing(self) -> None:
        self.executor.join()

    def cancel(self) -> None:
        self.stop = True
        self.wait_for_processing()

    def clear(self) -> None:
        self.timeline.clear()

    def __str__(self) -> str:
        result = ""
        for t in sorted(self.timeline.keys()):
            entries = self.timeline[t]
            result += f"{t} -> {entries}\n"
        return result


def main():
    # Example Usage:
    timeline = Timeline()
    timeline.put(datetime(2023, 11, 15, 11, 27), "Entry 1")
    timeline.put(datetime(2023, 11, 14, 11, 27), "Entry 2")

    # timeline.put(datetime.now(), "Entry 1")
    # timeline.put(datetime.now(), "Entry 2")
    timeline.process(print)
    sleep(5)
    timeline.cancel()
