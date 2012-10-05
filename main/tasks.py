from celery import task

@task()
def run(query):
    query.run()
