class InvalidAPIKeyError(RuntimeError):
    def __init__(self, code, message):
        self.message = message
        self.code = code
        super().__init__(message)


class ExpiredJWTError(RuntimeError):
    def __init__(self, code, message):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidModelError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        pass
