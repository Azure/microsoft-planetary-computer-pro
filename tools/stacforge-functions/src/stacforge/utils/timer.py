from time import perf_counter


class Timer:
    """A context manager to measure the time taken
    to execute a block of code."""

    def __enter__(self):
        self.start = perf_counter()
        self.end = 0.0
        return lambda: (
            perf_counter() - self.start if self.end == 0.0 else self.end - self.start
        )

    def __exit__(self, *args):
        self.end = perf_counter()
