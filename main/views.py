from django.shortcuts import render_to_response, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.context_processors import csrf
from django.forms.models import model_to_dict
from django.http import HttpResponse

from main.models import Query

import json


def index(request):
	if request.user.is_authenticated():
		queries = request.user.query_set.all().order_by('-created_on')
		return render_to_response('main/index.html', {'queries': queries})
	else:
		c = {}
		c.update(csrf(request))
		if request.method == 'POST':
			username = request.POST['username']
			password = request.POST['password']
			user = authenticate(username=username, password=password)
			if user is not None:
				login(request, user)
				return redirect('/')
			else:
				c['error'] = "Incorrect Username/Password"
				return render_to_response('main/login.html', c)
		else:
			return render_to_response('main/login.html', c)

def saved(request, offset=0):
	offset = int(offset)

	if 'page_limit' in request.session:
		limit = request.session['page_limit']
	else:
		limit = 25
	qs = request.user.query_set.filter(is_saved=True).order_by('-created_on')
	qs = qs[offset:limit]
	return render_to_response('main/saved.html', {'queries': qs})

def logout_view(request):
	logout(request)
	return redirect('/')

def public(request, offset=0):
	offset = int(offset)

	if 'page_limit' in request.session:
		limit = request.session['page_limit']
	else:
		limit = 25

	limit += offset

	qs = Query.objects.filter(is_public=True).order_by('-created_on')
	qs = qs[offset:limit]
	return render_to_response('main/public.html', {'queries': qs})


def ajax_query(request, qid=None):
	if request.user.is_authenticated():
		if qid == None:
			query = request.user.query_set.create(**request.GET.dict())
			query.exc()
		else:
			g = request.GET.dict()
			query = Query.objects.get(pk=request.GET['id'])
			for k in g:
				query[k] = g[k]
			query.save()
		response = query.to_json()

	else:
		response = json.dumps({'error': 'Not Logged In'})

	return HttpResponse(response, mimetype="application/json")

def ajax_queries(request):
	queries = request.user.query_set.all().order_by('-created_on')
	qs = []
	for query in queries:
		qs.append(model_to_dict(query))
	return HttpResponse(json.dumps(qs), mimetype="application/json")

def ajax_comments(request, qid):
	q = Query.objects.get(pk=qid)
	comments = q.comment_set.all().order_by('created_on')
	cs = []
	for comment in comments:
		cs.append(model_to_dict(comment))
	return HttpResponse(json.dumps(cs), mimetype="application/json")


def query(request, id):
	c = {}
	q = Query.objects.get(pk=id)

	if q.is_complete:
		s = q.get_sample()
	else:
		s = []

	c['query'] = q
	c['sample_data'] = s

	return render_to_response('main/query.html', c)

def download_results(request, id):
	import mimetypes
	import os.path

	mimetypes.init()

	q = Query.objects.get(pk=id)

	mime_type_guess = mimetypes.guess_type(os.path.basename(q.results))
	rf = open(q.results, 'r')

	return HttpResponse(rf, mimetype=mime_type_guess[0])
