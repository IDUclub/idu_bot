For running elastic you docker is required

To build and run elastic use command:
docker-compose -f docker-compose.elastic.yaml up

You also need to have local vectorizer and llm api.
Set url methods in env variables.
The same for telegram bot credentials.

finally, start fastapi app locally or run from docker with command:
docker-compose -f docker-compose.app.yaml up

interactive api docs are availale on localhost:8000