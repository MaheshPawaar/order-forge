import threading

from django.db import connection

THREADS = 20


def run_in_threads(task, total_calls):
    barrier = threading.Barrier(THREADS)
    results = []
    errors = []

    def worker():
        try:
            barrier.wait()
            for _ in range(total_calls // THREADS):
                results.append(task())
        except Exception as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, errors
