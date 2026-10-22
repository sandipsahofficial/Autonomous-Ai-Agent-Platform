FROM python:3.11-alpine

# Security hardening: Create unprivileged non-root user
RUN addgroup -S sandboxgroup && adduser -S -G sandboxgroup -u 1000 sandboxuser

WORKDIR /home/sandboxuser
USER sandboxuser

# Default entrypoint runs python in unbuffered mode
ENTRYPOINT ["python", "-u", "-c"]
