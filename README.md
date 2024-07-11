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
docker build --platform linux/amd64 --target runtime --tag robjkulesa/volleyball-uploader .
```

```sh
docker run -it --rm -v /Users/rkulesa/Documents:/mnt/user/media/volleyball robjkulesa/volleyball-uploader bash
python3 /usr/local/bin/volleyball-uploader --help
```
