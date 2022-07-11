# brewerja/dice-roller

Simple app to have chat/dice-rolling rooms.

### Run from code:

```
docker run --rm -d -p 6379:6379 redis 
./mvnw spring-boot:run
```

### Build the image:

`./mvnw spring-boot:build-image -Dspring-boot.build-image.imageName=brewerja/dice-roller`

### Run a container:

`docker run -p 8080:8080 brewerja/dice-roller:latest`

