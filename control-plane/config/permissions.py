"""
Shared-token permissions for preview API deployments.

The project is still an early preview, but mutating and read API endpoints should not
be exposed without at least a deployment-specific token. Clients may send either:

* Authorization: Bearer <token>
* X-PLOADTESTING-API-TOKEN: <token>
"""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasSharedApiToken(BasePermission):
    """Require a shared API token for all DRF API requests when configured."""

    message = "A valid API token is required."

    def has_permission(self, request, view) -> bool:  # noqa: ANN001 - DRF interface
        expected_token = getattr(settings, "PLOADTESTING_API_TOKEN", "")
        if not expected_token:
            return True

        provided_token = request.headers.get("X-PLOADTESTING-API-TOKEN", "")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            provided_token = auth_header.split(" ", 1)[1].strip()

        return provided_token == expected_token
