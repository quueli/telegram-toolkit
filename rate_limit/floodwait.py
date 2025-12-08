# how many accounts one batch job burns through before it gives up
MAX_ACCOUNT_ROTATIONS = 3


class ProactiveRotationNeeded(Exception):
    def __init__(self, processed_count: int, last_index: int, partial_results: list):
        self.processed_count = processed_count
        self.last_index = last_index
        self.partial_results = partial_results
        super().__init__(
            f"proactive rotation after {processed_count} items "
            f"(last_index={last_index}, partial_results={len(partial_results)})"
        )


class FloodWaitWithProgress(Exception):
    def __init__(self, seconds: int, partial_results: list, last_index: int, processed_count: int):
        self.seconds = seconds
        self.partial_results = partial_results
        self.last_index = last_index
        self.processed_count = processed_count
        super().__init__(f"floodwait {seconds}s after {processed_count} items (last_index={last_index})")
