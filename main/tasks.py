from celery import task
from main.models import Query

@task()
def run(query_id):
    q = Query.objects.get(pk=query_id)

    q.run()
