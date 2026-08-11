import urllib.request
import urllib.error
urls = [
    'http://127.0.0.1:8000/health',
    'http://127.0.0.1:8000/products/1/reviews/summary',
    'http://127.0.0.1:8000/products/1/reviews?page=1&page_size=10',
]
for url in urls:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            body = r.read().decode('utf-8')
            print(url)
            print('STATUS', r.getcode())
            print(body[:1000])
            print('---')
    except urllib.error.HTTPError as e:
        print(url)
        print('HTTP', e.code)
        print(e.read().decode('utf-8', errors='ignore')[:1000])
        print('---')
    except Exception as e:
        print(url)
        print('ERROR', e)
        print('---')
