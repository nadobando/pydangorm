class PydangoError(Exception):
    pass


class SessionNotInitializedError(PydangoError):
    pass


class DocumentNotFoundError(PydangoError):
    pass
