class OracleError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class ValidationError(OracleError):
    def __init__(self, message: str, code: int = 40001):
        super().__init__(code, message)

class AuthError(OracleError):
    def __init__(self, message: str, code: int = 41001):
        super().__init__(code, message)

class RateLimitError(OracleError):
    def __init__(self, message: str = "请求频率超限", code: int = 42001):
        super().__init__(code, message)

class BusinessError(OracleError):
    def __init__(self, message: str, code: int = 43001):
        super().__init__(code, message)

class UnsupportedSystemError(ValidationError):
    def __init__(self, system: str):
        super().__init__(f"不支持的术数系统: {system}", code=40002)
