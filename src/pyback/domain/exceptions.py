class DomainError(Exception):
    """Business rule violation."""


class NotFoundError(DomainError):
    pass


class AuthError(DomainError):
    pass


class ValidationError(DomainError):
    pass
