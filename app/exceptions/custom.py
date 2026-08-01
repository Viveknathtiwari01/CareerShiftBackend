class BaseAPIException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class AuthenticationException(BaseAPIException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class AuthorizationException(BaseAPIException):
    def __init__(self, message: str = "Not authorized to access this resource"):
        super().__init__(message, status_code=403)

class ValidationException(BaseAPIException):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)

class NotFoundException(BaseAPIException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class ConflictException(BaseAPIException):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)

class DatabaseException(BaseAPIException):
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message, status_code=500)
