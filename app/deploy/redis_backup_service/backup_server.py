import os
import subprocess
import gzip
from datetime import datetime
from flask import Flask, jsonify
import boto3


app = Flask(__name__)


@app.route("/backup", methods=["POST"])
def backup():
    try:
        subprocess.run(["redis-cli", "save"], check=True)

        rdb_path = "/data/dump.rdb"
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        gzip_path = f"/tmp/dump-{timestamp}.rdb.gz"
        s3_key = f"redis-backups/dump-{timestamp}.rdb.gz"

        with open(rdb_path, "rb") as f_in, gzip.open(gzip_path, "wb") as f_out:
            f_out.writelines(f_in)

        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["S3_ENDPOINT"],
            aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        )

        s3.upload_file(gzip_path, os.environ["S3_BUCKET"], s3_key)

        os.remove(gzip_path)

        return jsonify({"status": "ok", "uploaded": s3_key})

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
