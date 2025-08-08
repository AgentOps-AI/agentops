FROM redis:7-alpine

# define persistent volume for redis data
VOLUME ["/data"]

# set working directory to the data directory
WORKDIR /data

# launch redis server
CMD ["redis-server"]