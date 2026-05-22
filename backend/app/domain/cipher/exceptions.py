class CipherDomainError(Exception):
    """Базовый класс для ошибок доменной логики шифратора."""

    pass


class InvalidAlphabetError(CipherDomainError):
    """Ошибка: алфавит не соответствует ожидаемому (A-Z)."""

    pass


class InvalidDiskPermutationError(CipherDomainError):
    """Ошибка: диск содержит некорректную перестановку символов."""

    pass


class DuplicateDiskNumberError(CipherDomainError):
    """Ошибка: в наборе или ключе обнаружены дублирующиеся ID дисков."""

    pass


class MissingDiskNumberError(CipherDomainError):
    """Ошибка: в ключе указан ID диска, отсутствующий в наборе."""

    pass


class EmptyTextError(CipherDomainError):
    """Ошибка: входной текст после нормализации оказался пустым."""

    pass


class InvalidConfigurationError(CipherDomainError):
    """Ошибка: некорректная конфигурация набора дисков или ключа."""

    pass
