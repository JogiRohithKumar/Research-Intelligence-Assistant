import time


def retry_execute(
    func,
    *args,
    retries=3,
    delay=5,
    **kwargs
):

    last_error = None

    for attempt in range(retries):

        try:

            return func(*args, **kwargs)

        except Exception as e:

            last_error = e

            print(
                f"Retry {attempt + 1}/{retries}"
            )

            time.sleep(delay)

    raise last_error