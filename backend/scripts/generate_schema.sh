#!/bin/bash
# Generate OpenAPI schema
cd /app/backend
python manage.py spectacular --file schema.yml 2>/dev/null || echo "Schema generation skipped"
