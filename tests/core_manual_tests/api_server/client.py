import concurrent.futures
import requests


def fetch_url(url):
    response = requests.get(url)
    return response


url = "http://localhost:9696/completion"

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(fetch_url, url), executor.submit(fetch_url, url)]
    responses = [future.result() for future in concurrent.futures.as_completed(futures)]

response1, response2 = responses
print(response1.text)
print(response2.text)
