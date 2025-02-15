# Volleyball Video Uploader

## Build and run flyway container:

```sh
docker build --target flyway --tag volleyball-flyway .
```

```sh
docker run -t --rm volleyball-flyway
```

## Build and push and run main container:

```sh
docker build --platform linux/amd64 --target runtime --tag robjkulesa/youtube-uploader-python .
```

```sh
docker image push robjkulesa/youtube-uploader-python
```

```sh
docker run -t --rm -v <path to videos>:/videos robjkulesa/youtube-uploader-python
```
