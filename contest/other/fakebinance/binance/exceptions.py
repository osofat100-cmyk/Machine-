class BinanceAPIException(Exception):
    def __init__(self, message="", code=0):
        super().__init__(message)
        self.message, self.code = message, code
