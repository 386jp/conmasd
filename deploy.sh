poetry publish --build

docker buildx build --platform linux/amd64,linux/arm64 -t 386jp/conmasd:latest --push .
docker buildx build --platform linux/amd64,linux/arm64 -t 386jp/conmasd:0.1.4 --push .
