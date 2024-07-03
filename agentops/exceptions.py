class MultiSessionException(Exception):
    def __init__(self, message):
        super().__init__(message)


class NoSessionException(Exception):
    def __init__(self, message):
        super().__init__(message)
