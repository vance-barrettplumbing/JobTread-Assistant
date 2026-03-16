"""
JobTread Pave API client.

Pave is a JSON-based query language used by JobTread. Queries are JSON objects,
not GraphQL strings. Authentication uses grantKey inside the query's $ input,
not an HTTP Authorization header.

Example query:
    {
        "$": { "grantKey": "..." },
        "organization": {
            "$": { "id": "abc123" },
            "id": {},
            "name": {},
            "jobs": {
                "nodes": { "id": {}, "name": {}, "number": {} }
            }
        }
    }
"""
import os
import requests
from typing import Any, Optional


JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL", "https://api.jobtread.com/pave")


class JobTreadClient:
    def __init__(self, grant_key: str, api_url: str = JOBTREAD_API_URL):
        self.grant_key = grant_key
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def query(self, pave_query: dict, variables: Optional[dict] = None) -> dict:
        """
        Execute a Pave query.

        pave_query should be the query object WITHOUT the top-level $ grantKey —
        that is injected automatically. Example:

            client.query({
                "organization": {
                    "$": { "id": "abc123" },
                    "id": {},
                    "name": {}
                }
            })
        """
        # Inject grantKey at the top level
        full_query: dict[str, Any] = {
            "$": {"grantKey": self.grant_key},
            **pave_query,
        }
        payload = {"query": full_query}

        response = self.session.post(self.api_url, json=payload, timeout=30)

        # Surface HTTP errors with the response body for easier debugging
        if not response.ok:
            raise PaveError(f"HTTP {response.status_code}: {response.text[:500]}")

        result = response.json()

        if isinstance(result, dict) and "errors" in result:
            raise PaveError(str(result["errors"]))

        return result

    def get_current_grant(self) -> dict:
        """Return current grant info including org memberships."""
        return self.query({
            "currentGrant": {
                "id": {},
                "user": {
                    "id": {},
                    "name": {},
                    "memberships": {
                        "nodes": {
                            "id": {},
                            "organization": {
                                "id": {},
                                "name": {},
                            },
                        }
                    },
                },
            }
        })


class PaveError(Exception):
    pass


# Keep old name for compatibility
GraphQLError = PaveError
