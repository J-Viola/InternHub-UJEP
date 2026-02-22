help: ## Prints help for targets with comments
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build: ## Builds the app and detaches
	docker compose up -d --build

up: ## Brings Docker stack up and detaches
	docker compose up -d

down: ## Puts Docker stack down (removes volumes for full reset)
	docker compose down -v

restart: ## Restarts docker stack
	docker compose restart

frontend-open-sh: ## Opens shell inside running container
	docker container exec -it internhub-frontend bash

backend-open-sh: ## Opens shell inside running container
	docker container exec -it internhub-backend bash

lint: ## Runs linter check inside backend container
	docker container exec internhub-backend ruff check .

format: ## Formats code and fixes linting issues inside backend container
	docker container exec internhub-backend ruff format .
	docker container exec internhub-backend ruff check --fix .

test: ## Runs tests for the backend (pytest)
	docker container exec internhub-backend pytest

test-frontend: ## Runs tests for the frontend
	docker container exec internhub-frontend npm test -- --watchAll=false --passWithNoTests

migrate: ## Runs Django migrations inside the backend container
	docker container exec internhub-backend python manage.py migrate

seed: ## Seeds the database with demo data inside the backend container
	docker container exec internhub-backend python manage.py seed --settings=app.settings

lint-frontend: ## Runs ESLint on the frontend source
	docker container exec internhub-frontend npx eslint src --ext .js,.jsx

logs: ## Tails the last 100 lines of all container logs
	docker compose logs --tail=100 -f