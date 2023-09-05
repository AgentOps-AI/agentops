import json
from enum import Enum
from typing import Optional
import httpx

JSON_HEADER = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "*/*"
}


class HttpStatus(Enum):
    SUCCESS = 200
    INVALID_REQUEST = 400
    TIMEOUT = 408
    PAYLOAD_TOO_LARGE = 413
    TOO_MANY_REQUESTS = 429
    FAILED = 500
    UNKNOWN = -1


class Response:

    def __init__(self, status: HttpStatus = HttpStatus.UNKNOWN, body: Optional[dict] = None):
        self.status: HttpStatus = status
        self.code: int = status.value
        self.body = body
        if not self.body:
            self.body = {}

    async def parse(self, res: httpx.Response):
        res_body = res.json()
        self.code = res.status_code
        self.status = self.get_status(self.code)
        self.body = res_body
        return self

    @staticmethod
    def get_status(code: int) -> HttpStatus:
        if 200 <= code < 300:
            return HttpStatus.SUCCESS
        elif code == 429:
            return HttpStatus.TOO_MANY_REQUESTS
        elif code == 413:
            return HttpStatus.PAYLOAD_TOO_LARGE
        elif code == 408:
            return HttpStatus.TIMEOUT
        elif 400 <= code < 500:
            return HttpStatus.INVALID_REQUEST
        elif code >= 500:
            return HttpStatus.FAILED
        return HttpStatus.UNKNOWN


class HttpClient:

    @staticmethod
    async def post(url: str, payload: bytes, api_key: str = None, header=None) -> Response:
        result = Response()
        try:
            if api_key != None:
                JSON_HEADER["X-Agentops-Auth"] = api_key

            res = await httpx.post(url, data=payload,
                                   headers=JSON_HEADER, timeout=20)

            await result.parse(res)
        except httpx.TimeoutException:
            result.code = 408
            result.status = HttpStatus.TIMEOUT
        except httpx.HTTPStatusError as e:
            try:
                await result.parse(e.response)
            except:
                result = Response()
                result.code = e.response.status_code
                result.status = Response.get_status(e.response.status_code)
                result.body = {'error': str(e)}
        except httpx.RequestError as e:
            result.body = {'error': str(e)}
        return result
