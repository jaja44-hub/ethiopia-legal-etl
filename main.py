
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve /hub as static dashboard
app.mount('/hub', StaticFiles(directory='hub', html=True), name='hub')

@app.get('/')
def read_root():
    return {'status': 'App is live. Visit /hub for dashboard.'}

