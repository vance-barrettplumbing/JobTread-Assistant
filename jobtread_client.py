"""
JobTread GraphQL API client.
"""
import os
import json
import requests
from typing import Any, Optional


JOBTREAD_API_URL = os.getenv("JOBTREAD_API_URL", "https://api.jobtread.com/papi")


class JobTreadClient:
    def __init__(self, api_key: str, api_url: str = JOBTREAD_API_URL):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })

    def query(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query or mutation."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = self.session.post(self.api_url, json=payload)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise GraphQLError(result["errors"])

        return result.get("data", {})

    def introspect_schema(self) -> dict:
        """Fetch the full GraphQL schema via introspection."""
        introspection_query = """
        query IntrospectionQuery {
          __schema {
            queryType { name }
            mutationType { name }
            types {
              kind
              name
              description
              fields(includeDeprecated: false) {
                name
                description
                args {
                  name
                  description
                  type { ...TypeRef }
                  defaultValue
                }
                type { ...TypeRef }
              }
              inputFields {
                name
                description
                type { ...TypeRef }
                defaultValue
              }
              enumValues(includeDeprecated: false) {
                name
                description
              }
            }
          }
        }
        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
        """
        return self.query(introspection_query)

    def get_top_level_fields(self) -> dict:
        """Get available query and mutation fields (lighter than full introspection)."""
        q = """
        {
          __schema {
            queryType {
              fields {
                name
                description
                args { name description type { kind name ofType { kind name } } }
              }
            }
            mutationType {
              fields {
                name
                description
                args { name description type { kind name ofType { kind name } } }
              }
            }
          }
        }
        """
        return self.query(q)


class GraphQLError(Exception):
    def __init__(self, errors: list):
        messages = "; ".join(e.get("message", str(e)) for e in errors)
        super().__init__(f"GraphQL errors: {messages}")
        self.errors = errors
