help: ## Prints help for targets with comments
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

build: ## Builds the app and detaches
	docker compose up --d -build --parallel

up: ## Brings Docker stack up and detaches
	docker compose up -d

down: ## Puts Docker stack down
	docker compose down -v

restart: ## Restarts docker stack
	docker compose restart

frontend-open-sh: ## Opens shell inside running container
	docker exec -it internhub-frontend bash

backend-open-sh: ## Opens shell inside running container
	docker exec -it internhub-backend bash