class RateLimitExceeded(Exception):
    def __init__(self, message: str = "Rate limit exceeded", request_index: int | None = None):
        self.message = message
        self.request_index = request_index
        super().__init__(message)