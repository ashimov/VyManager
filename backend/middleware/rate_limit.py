"""
Rate Limiting Middleware

Provides distributed rate limiting using Redis for API endpoints.
Falls back to in-memory storage if Redis is unavailable.
Protects against brute force attacks and DoS.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple, Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting middleware using Redis.

    Limits requests per IP address with different limits for different endpoint categories.
    Uses Redis for distributed rate limiting across multiple backend instances.
    Falls back to in-memory storage if Redis is unavailable.
    """

    # Rate limits: (max_requests, window_seconds)
    RATE_LIMITS: Dict[str, Tuple[int, int]] = {
        # Authentication endpoints - stricter limits
        "auth": (10, 60),  # 10 requests per minute
        # Session management
        "session": (30, 60),  # 30 requests per minute
        # General API endpoints
        "default": (300, 60),  # 300 requests per minute
        # CSV import - very strict
        "import": (3, 300),  # 3 imports per 5 minutes
    }

    # Endpoints that are exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    # IPs that are exempt from rate limiting (localhost for development)
    EXEMPT_IPS = {
        "127.0.0.1",
        "::1",
        "localhost",
    }

    # Redis key prefix for rate limiting
    REDIS_PREFIX = "ratelimit"

    def __init__(self, app, cleanup_interval: int = 300):
        super().__init__(app)
        # Fallback in-memory storage (used if Redis unavailable)
        self._requests: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._redis_available = False
        self._redis_checked = False

    def _get_category(self, path: str) -> str:
        """Determine rate limit category for a path."""
        if path.startswith("/api/auth") or path.startswith("/session/onboarding"):
            return "auth"
        if path.startswith("/session"):
            return "session"
        if "import" in path.lower():
            return "import"
        return "default"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check for forwarded IP (behind reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host
        return "unknown"

    def _get_redis_key(self, ip: str, category: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.REDIS_PREFIX}:{category}:{ip}"

    async def _get_redis_client(self, request: Request):
        """Get Redis client from app state."""
        if hasattr(request.app.state, "cache") and request.app.state.cache.is_connected:
            return request.app.state.cache._client
        return None

    async def _is_rate_limited_redis(
        self, redis_client, ip: str, category: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using Redis.

        Uses Redis INCR with EXPIRE for atomic rate limiting.
        """
        max_requests, window = self.RATE_LIMITS.get(category, self.RATE_LIMITS["default"])
        key = self._get_redis_key(ip, category)

        try:
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Increment the counter
            pipe.incr(key)
            # Set expiry only if key is new (returns 1 if key didn't exist)
            pipe.expire(key, window, nx=True)
            # Get TTL for retry-after header
            pipe.ttl(key)

            results = await pipe.execute()
            current_count = results[0]
            ttl = results[2]

            if current_count > max_requests:
                retry_after = max(1, ttl) if ttl > 0 else window
                return True, retry_after

            return False, None

        except Exception as e:
            logger.warning(f"Redis rate limit error: {e}, falling back to in-memory")
            return await self._is_rate_limited_memory(ip, category)

    async def _is_rate_limited_memory(
        self, ip: str, category: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using in-memory storage (fallback).

        Returns:
            Tuple of (is_limited, retry_after_seconds)
        """
        max_requests, window = self.RATE_LIMITS.get(category, self.RATE_LIMITS["default"])
        current_time = time.time()
        cutoff = current_time - window

        async with self._lock:
            # Get valid requests within the window
            valid_requests = [
                entry for entry in self._requests[ip][category]
                if entry[0] > cutoff
            ]

            # Update stored requests
            self._requests[ip][category] = valid_requests

            # Check if limit exceeded
            if len(valid_requests) >= max_requests:
                # Calculate retry-after
                oldest = min(entry[0] for entry in valid_requests)
                retry_after = int(oldest + window - current_time) + 1
                return True, max(1, retry_after)

            # Add current request
            self._requests[ip][category].append((current_time, 1))
            return False, None

    async def _cleanup_old_entries(self) -> None:
        """Remove expired entries from in-memory storage."""
        current_time = time.time()

        # Only cleanup periodically
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = current_time
        max_window = max(limit[1] for limit in self.RATE_LIMITS.values())
        cutoff = current_time - max_window

        async with self._lock:
            for ip in list(self._requests.keys()):
                for category in list(self._requests[ip].keys()):
                    # Remove old entries
                    self._requests[ip][category] = [
                        entry for entry in self._requests[ip][category]
                        if entry[0] > cutoff
                    ]
                    # Clean up empty categories
                    if not self._requests[ip][category]:
                        del self._requests[ip][category]
                # Clean up empty IPs
                if not self._requests[ip]:
                    del self._requests[ip]

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path

        # Skip rate limiting for exempt paths
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get client IP and category
        client_ip = self._get_client_ip(request)

        # Skip rate limiting for exempt IPs (localhost for development)
        if client_ip in self.EXEMPT_IPS:
            return await call_next(request)

        category = self._get_category(path)

        # Try to get Redis client
        redis_client = await self._get_redis_client(request)

        if redis_client:
            # Use Redis for distributed rate limiting
            if not self._redis_checked:
                logger.info("Rate limiting using Redis (distributed)")
                self._redis_checked = True
                self._redis_available = True
            is_limited, retry_after = await self._is_rate_limited_redis(
                redis_client, client_ip, category
            )
        else:
            # Fallback to in-memory
            if not self._redis_checked:
                logger.warning(
                    "Redis not available - using in-memory rate limiting. "
                    "This won't work correctly with multiple backend instances."
                )
                self._redis_checked = True
                self._redis_available = False

            # Cleanup old entries periodically
            await self._cleanup_old_entries()

            is_limited, retry_after = await self._is_rate_limited_memory(
                client_ip, category
            )

        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on category '{category}'"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Proceed with request
        return await call_next(request)
