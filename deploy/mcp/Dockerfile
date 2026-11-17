# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG MATHFORMER_CONTAINER_ROOT
WORKDIR ${MATHFORMER_CONTAINER_ROOT}

COPY requirements-mcp-service.txt ./requirements-mcp-service.txt
RUN pip install --no-cache-dir -r requirements-mcp-service.txt

COPY . .

EXPOSE 8765

CMD ["python", "scripts/mathformer_mcp_service.py", "--config", "config/mathformer_mcp.local.toml"]
