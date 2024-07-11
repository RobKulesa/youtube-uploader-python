# Volleyball Video Uploader

## Build and run flyway container:

```sh
docker build --target flyway --tag volleyball-flyway .
```

```sh
docker run -t --rm volleyball-flyway
```

## Build and run main container:

```sh
docker build --platform linux/amd64 --target runtime --tag <dockerhub username>/volleyball-uploader .
```

```sh
docker run -it --rm -v <path to videos>:/mnt/user/media/volleyball <dockerhub username>/volleyball-uploader bash
python3 /usr/local/bin/volleyball-uploader --help
```
