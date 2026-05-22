class CipherDomainError(Exception):
    pass


class InvalidAlphabetError(CipherDomainError):
    pass


class InvalidDiskPermutationError(CipherDomainError):
    pass


class DuplicateDiskNumberError(CipherDomainError):
    pass


class MissingDiskNumberError(CipherDomainError):
    pass


class EmptyTextError(CipherDomainError):
    pass


class InvalidConfigurationError(CipherDomainError):
    pass
