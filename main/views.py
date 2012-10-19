from django.shortcuts import render_to_response, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.context_processors import csrf
from django.forms.models import model_to_dict
from django.http import HttpResponse

from main.models import QueryGroup, Query

import json


def index(request):
	if request.user.is_authenticated():
		groups = QueryGroup.getGroupTable(request.user)
		return render_to_response('main/index.html', {'queries': groups, 'cur_user': True})
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
	qs = QueryGroup.getGroupTable(user=request.user,args={'is_saved': True, 'is_deleted': False})
	return render_to_response('main/saved.html', {'queries': qs, 'cur_user': True})


def public(request, offset=0):
	qs = QueryGroup.getGroupTable(args={'is_public': True, 'is_deleted': False})
	return render_to_response('main/public.html', {'queries': qs})


def logout_view(request):
	logout(request)
	return redirect('/')



def ajax_query(request, qid=None):
	if request.user.is_authenticated():
		if qid == None:
			get = request.GET.dict()
			groupfields = ['name', 'is_saved', 'is_public']
			groupopts = {}
			for field in groupfields:
				if field in get:
					groupopts[field] = request.GET.dict()[field]
			querygroup = request.user.querygroup_set.create(**groupopts)

			queryfields = ['query', 'email_on_complete']
			queryopts = {}
			for field in queryfields:
				if field in get:
					queryopts[field] = get[field]

			query = querygroup.query_set.create(editor=request.user,**queryopts)

			#query.exc()
		else:
			query = Query.objects.get(pk=qid)
			d = json.loads(request.body)

			del d['id']
			del d['user']

			for k in d:
				setattr(d, k, d[k])

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



def ajax_comment(request):
	comm = json.loads(request.body)
	qid = comm['query_id']
	del comm['query_id']
	q = Query.objects.get(pk=qid)
	q.comment_set.create(user=request.user, **comm)
	return HttpResponse(request.body, mimetype="application/json")

def ajax_comments(request, qid):
	q = Query.objects.get(pk=qid)
	comments = q.comment_set.all().order_by('created_on')
	cs = []
	for comment in comments:
		cd = model_to_dict(comment)
		cd['user_name'] = comment.user.username
		cd['created_on'] = comment.created_on.strftime('%c')
		cs.append(cd)
	return HttpResponse(json.dumps(cs), mimetype="application/json")


def query(request, id):
	c = {}
	q = QueryGroup.objects.get(pk=id)

	if q.is_deleted:
		return redirect('/')

	c['query'] = q.to_dict()
	c['query_json'] = q.to_json()

	return render_to_response('main/query.html', c)

def download_results(request, id):
	import mimetypes
	import os.path

	mimetypes.init()

	q = Query.objects.get(pk=id)

	mime_type_guess = mimetypes.guess_type(os.path.basename(q.results))
	rf = open(q.results, 'r')

	r = HttpResponse(rf, mimetype=mime_type_guess[0])

	r['Content-Length'] = os.path.getsize(q.results)
	return r
