import argparse, json, os, urllib.request, urllib.error
p=argparse.ArgumentParser(description='Cambiar modo de dependencia SOLO en entorno local')
p.add_argument('mode',choices=['normal','slow','unavailable'])
p.add_argument('--base',default=os.getenv('API_BASE','http://127.0.0.1:18000'))
a=p.parse_args()
request=urllib.request.Request(a.base+'/admin/mode',data=json.dumps({'mode':a.mode}).encode(),headers={'Content-Type':'application/json','X-Lab-Key':'demo-tsi-a-no-produccion'},method='POST')
with urllib.request.urlopen(request,timeout=5) as response:
    print(response.status,response.read().decode())
