import argparse, json, os, sys, urllib.request, urllib.error
p=argparse.ArgumentParser(description="Smoke de servicio TSI")
p.add_argument('--base',default=os.getenv('API_BASE','http://127.0.0.1:18000'))
a=p.parse_args()
paths=['/health/live','/health/ready','/api/items']
failures=0
for path in paths:
    try:
        with urllib.request.urlopen(a.base+path,timeout=5) as resp:
            payload=json.loads(resp.read().decode())
            print(f'{path} => {resp.status}: {str(payload)[:110]}')
            if resp.status != 200: failures+=1
    except urllib.error.HTTPError as exc:
        print(f'{path} => {exc.code} (esperado solo durante falla simulada)')
        failures+=1
    except Exception as exc:
        print(f'{path} => ERROR {exc}')
        failures+=1
sys.exit(1 if failures else 0)
