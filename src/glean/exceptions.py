class GleanError(Exception):
    pass


class ScraperError(GleanError):
    pass


class ClientError(GleanError):
    pass
