"""Custom logging filters for request correlation."""

import logging
from api.utils.request_context import get_request_id


class RequestIdFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.

    This allows correlation of all logs generated during a single request.
    """

    def filter(self, record):
        request_id = get_request_id()
        record.request_id = request_id if request_id else '-'
        return True
