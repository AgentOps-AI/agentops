FROM redis:8

RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip install flask boto3

COPY redis.conf /usr/local/etc/redis/redis.conf
COPY backup_server.py /backup_server.py

VOLUME /data

CMD ["bash", "-c", "redis-server /usr/local/etc/redis/redis.conf & python3 /backup_server.py"]
