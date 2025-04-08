class ProcessingDataError(Exception):
    """Podstawowy wyjątek dla modułu processing_data."""

    pass


class StorageError(ProcessingDataError):
    """Wyjątek zgłaszany, gdy wystąpi problem z przechowywaniem danych."""

    pass


class RetrievalError(ProcessingDataError):
    """Wyjątek zgłaszany, gdy wystąpi problem z pobieraniem danych."""

    pass
