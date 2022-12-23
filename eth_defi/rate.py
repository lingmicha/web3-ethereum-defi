import asyncio
import time
from web3 import Web3
import collections
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Sequence,
    Collection,
    Type,
)

from web3.types import (
    RPCEndpoint,
    RPCResponse,
    Middleware,
    AsyncMiddleware,
)

from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
    TooManyRedirects,
)

from web3.middleware.exception_retry_request import check_if_retry_on_failure



class REST_Semaphore(asyncio.Semaphore):
    """A custom semaphore to be used with REST API with velocity limit under asyncio
    """

    def __init__(self, value: int, interval: int):
        """控制REST API访问速率

        :param value: API limit
        :param interval: Reset interval
        """
        super().__init__(value)
        # Queue of inquiry timestamps
        self._inquiries = collections.deque(maxlen=value)
        self._loop = asyncio.get_event_loop()
        self._interval = interval

    def __repr__(self):
        return f'API velocity: {self._inquiries.maxlen} inquiries/{self._interval}s'

    async def acquire(self):
        await super().acquire()
        if self._inquiries:
            timelapse = time.monotonic() - self._inquiries.popleft()
            # Wait until interval has passed since the first inquiry in queue returned.
            if timelapse < self._interval:
                await asyncio.sleep(self._interval - timelapse)
        return True

    def release(self):
        self._inquiries.append(time.monotonic())
        super().release()


NODE_RATE_LIMITER = REST_Semaphore(20, 1) # Default Limiter


async def async_rate_limiter_middleware(
    make_request: Callable[[RPCEndpoint, Any], Any], w3: "Web3"
) -> AsyncMiddleware:

    async def middleware(method, params):
        # do pre-processing here

        # perform the RPC request, getting the response
        async with NODE_RATE_LIMITER:
            response = await make_request(method, params)

        # do post-processing here

        # finally return the response
        return response

    return  middleware


async def async_exception_retry_middleware(
    make_request: Callable[[RPCEndpoint, Any], RPCResponse],
    w3: "Web3",
    errors: Collection[Type[BaseException]],
    retries: int = 5,
) -> Callable[[RPCEndpoint, Any], RPCResponse]:
    """
    Creates middleware that retries failed HTTP requests. Is a default
    middleware for HTTPProvider.
    """

    async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        if check_if_retry_on_failure(method):

            for i in range(retries):
                try:
                    return await make_request(method, params)
                # https://github.com/python/mypy/issues/5349
                except errors:  # type: ignore
                    if i < retries - 1:
                        continue
                    else:
                        raise
            return None
        else:
            return await make_request(method, params)

    return middleware


async def async_http_retry_request_middleware(
    make_request: Callable[[RPCEndpoint, Any], Any], w3: "Web3"
) -> Callable[[RPCEndpoint, Any], Any]:
    return await async_exception_retry_middleware(
        make_request, w3, (ConnectionError, HTTPError, Timeout, TooManyRedirects)
    )