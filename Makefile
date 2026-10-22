.PHONY: up down test eval logs clean

up:
	docker compose up --build

down:
	docker compose down

test:
	docker compose run --rm backend pytest tests/ -v

eval:
	docker compose run --rm backend python -m evals.run

logs:
	docker compose logs -f

clean:
	docker compose down -v
