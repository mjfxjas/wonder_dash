FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/mjfxjas/wonder_dash"
LABEL org.opencontainers.image.description="AWS monitoring CLI tool"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install wonder-dash from PyPI
RUN pip install --no-cache-dir wonder-dash

# Create non-root user
RUN useradd -m -u 1000 wonder && chown -R wonder:wonder /app
USER wonder

ENTRYPOINT ["wonder-dash"]
CMD ["--help"]
