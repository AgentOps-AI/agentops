echo '~ Running AO SDK-API e2e tests ~'

docker build -t sdk-api-tests .
docker run -it --name test-container sdk-api-tests main.py