import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional, List
import httpx
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult


class HttpGetInput(BaseModel):
    url: str = Field(..., min_length=8, max_length=1000, description="Target HTTP or HTTPS URL to retrieve")
    max_bytes: int = Field(default=16384, ge=512, le=32768, description="Maximum response content size in bytes")


class HttpGetOutput(BaseModel):
    status_code: int
    content: str
    content_type: str
    url: str


BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}


def is_prohibited_ip(ip_str: str) -> bool:
    """
    Evaluates whether an IP address belongs to loopback, private RFC1918, link-local,
    multicast, or cloud metadata ranges.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_target_url(url: str, allowed_domains: Optional[List[str]] = None) -> str:
    """
    SSRF defense: validates URL scheme, prohibits loopback/private/metadata destinations,
    and enforces hostname allowlists if configured.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Prohibited protocol scheme: '{parsed.scheme}'. Only 'http' and 'https' are permitted.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise ValueError("URL must include a valid network hostname.")

    if hostname in BLOCKED_HOSTNAMES:
        raise PermissionError(f"Security Alert: Target host '{hostname}' is blocked by SSRF policy.")

    # Resolve IP address to detect DNS rebinding or numeric IP bypasses
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in addr_info:
            ip_candidate = item[4][0]
            if is_prohibited_ip(ip_candidate):
                raise PermissionError(
                    f"Security Alert: Host '{hostname}' resolves to prohibited/private IP '{ip_candidate}'."
                )
    except socket.gaierror as ge:
        raise ValueError(f"Failed to resolve hostname '{hostname}': {str(ge)}")

    if allowed_domains:
        normalized_allowed = [d.lower().strip() for d in allowed_domains]
        domain_matched = any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in normalized_allowed
        )
        if not domain_matched:
            raise PermissionError(
                f"Security Alert: Host '{hostname}' is not in the permitted domain allowlist ({allowed_domains})."
            )

    return url


class ApprovedHttpGetTool(BaseTool):
    """
    SSRF-hardened HTTP GET inspection tool.
    Disabled by default. Blocks private networks, cloud metadata, and loopbacks.
    """
    name = "http_get"
    version = "1.1.0"
    description = "Retrieves web content via HTTP GET with strict SSRF defense, network restrictions, and size bounds."
    args_schema = HttpGetInput
    output_schema = HttpGetOutput
    required_permissions = ["http:read"]
    timeout_seconds = 5
    max_output_size_bytes = 32768
    is_enabled = False  # Disabled by default as requested
    requires_approval = True
    idempotent = True

    def __init__(self, is_enabled: bool = False, allowed_domains: Optional[List[str]] = None):
        self.is_enabled = is_enabled
        self.allowed_domains = allowed_domains

    def run(self, url: str, max_bytes: int = 16384) -> ToolResult:
        if not self.is_enabled:
            return ToolResult(
                success=False,
                output=None,
                error="Tool 'http_get' is currently disabled by administrative security policy.",
                metadata={"disabled": True},
            )

        try:
            current_url = validate_target_url(url, self.allowed_domains)

            # Prevent automatic redirect following to private destinations
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
                resp = client.get(
                    current_url,
                    headers={"User-Agent": "MESH-AutonomousAgent/3.0 (Security-Sandboxed)"},
                )

                # If redirect, validate destination
                redirect_count = 0
                while resp.is_redirect and redirect_count < 3:
                    redirect_count += 1
                    loc = resp.headers.get("location")
                    if not loc:
                        break
                    # Validate redirected URL
                    target_redirect = validate_target_url(loc, self.allowed_domains)
                    resp = client.get(target_redirect)

                text_content = resp.text[:max_bytes]
                is_truncated = len(resp.text) > max_bytes

                return ToolResult(
                    success=resp.is_success,
                    output={
                        "status_code": resp.status_code,
                        "content": text_content,
                        "content_type": resp.headers.get("content-type", "unknown"),
                        "url": str(resp.url),
                    },
                    metadata={"truncated": is_truncated, "redirects": redirect_count},
                    error=None if resp.is_success else f"HTTP error status {resp.status_code}",
                )

        except (PermissionError, ValueError) as sec_err:
            return ToolResult(success=False, output=None, error=str(sec_err))
        except httpx.TimeoutException:
            return ToolResult(success=False, output=None, error=f"HTTP request timed out after {self.timeout_seconds}s")
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"HTTP request failed: {str(exc)}")
