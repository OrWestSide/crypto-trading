build:
	docker-compose build

app:
	xhost +"local:docker@"
	docker-compose run --rm app
