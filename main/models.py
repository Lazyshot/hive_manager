from django.db import models
from django.contrib.auth.models import User
from django.core.mail import  EmailMessage
from django.forms.models import model_to_dict
from calendar import timegm

import main.tasks as tasks
import json
import sys
import time
import csv
import os

def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


class QueryGroup(models.Model):
	name = models.CharField(max_length=200,blank=True,default='')

	creator = models.ForeignKey(User)

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)

	is_saved = models.BooleanField(default=False)
	is_public = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)


	def to_dict(self, related=True):
		di = model_to_dict(self)
		di['created_on'] = self.created_on
		di['modified_on'] = self.modified_on

		if related:
			di['queries'] = []
			for query in self.query_set.order_by('-created_on').all():
				di['queries'].append(query.to_dict(True))
			di['creator'] = {
				'id': self.creator.id,
				'name': self.creator.username
			}
		return di

	def to_json(self, related=True):
		return json.dumps(self.to_dict(related), default=date_handler)

	@staticmethod
	def getGroupTable(user=None,args={'is_deleted': False}):
		if user is None:
			groups = QueryGroup.objects.all().filter(**args)
		else:
			groups = user.querygroup_set.all().filter(**args).order_by('-created_on')


		for group in groups:
			group.last_query = group.query_set.order_by('-created_on')[0:1].get()
			try:
				group.last_query.last_result = group.last_query.queryresult_set.order_by('-created_on')[0:1].get()
			except:
				group.last_query.last_result = None

		return groups



class Query(models.Model):
	editor = models.ForeignKey(User)
	group = models.ForeignKey(QueryGroup)

	query = models.TextField()

	email_on_complete = models.BooleanField(default=False)

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)

	def to_dict(self, related=True):
		di = model_to_dict(self)
		di['created_on'] = self.created_on
		di['modified_on'] = self.modified_on
		if related:
			di['results'] = []
			for result in self.queryresult_set.order_by('-created_on').all():
				di['results'].append(result.to_dict())
			di['editor'] = {
				'id': self.editor.id,
				'name': self.editor.username
			}
			di['group'] = {
				'id': self.group.id,
				'name': self.group.name
			}
		return di

	def to_json(self, related=True):
		return json.dumps(self.to_dict(related), default=date_handler)

	def refresh_from_db(self):
		"""Refreshes this instance from db
		https://code.djangoproject.com/ticket/901
		"""
		from_db = self.__class__.objects.get(pk=self.pk)
		for field in self.__class__._meta.fields:
			setattr(self, field.name, getattr(from_db, field.name))

	def exc(self):
		tasks.run.delay(self)

	def run(self):
		##Thrift Imports

		from thrift import Thrift
		from thrift.transport import TSocket, TTransport
		from thrift.protocol import TBinaryProtocol
		from hive_service import ThriftHive
		from hive_service.ttypes import HiveServerException

		result = self.query_result_set.create()

		try:
			transport = TSocket.TSocket(os.getenv('HIVE_SERVER'), 10000)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)

			client = ThriftHive.Client(protocol)
			transport.open()

			client.execute(self.query)

			self.refresh_from_db()

			result.status = result.WRITING
			result.save()

			result.results = '/tmp/hive_results/' + str(result.pk) + str(int(time.time())) + '.csv'

			rfile = open(result.results, 'w')
			wr = csv.writer(rfile)
			columns = []

			schema = client.getSchema()

			for col in schema.fieldSchemas:
				columns.append(col.name)

			print columns
			wr.writerow(columns)

			limit = 10000

			while True:
				rows = client.fetchN(limit)
				if len(rows) < 1:
					break
				for row in rows:
					wr.writerow(row.split("\t"))

			self.refresh_from_db()

			rfile.close()

			result.status = result.SUCCESS
		except HiveServerException, e:
			result.error_msg = e

			if e.errorCode == 0:
				result.status = result.SUCCESS
			else:
				result.status = result.FAILED

			print '%s' % (e.message)
		except Thrift.TException, tx:
			result.error_msg = tx
			result.status = result.FAILED
			print '%s' % (tx.message)
		except TypeError, e:
			if self.query.count("INSERT") > 0 or self.query.count("CREATE") > 0 :
				result.status = result.SUCCESS
			else:
				result.error_msg = e
				result.status = result.FAILED
		except:
			result.error_msg = sys.exc_info()[0]
			result.status = result.FAILED

		result.save()
		self.save()

		if self.email_on_complete:
			subject = "Query finished: " + str(self.pk)
			html_content = "The query has finished. Go here for details: <a href='http://hive.louddev.com/query/" + str(self.pk) + "/'>Query</a>"
			from_email = "HiveManager <no-reply@louddev.com>"
			to = self.user.email

			msg = EmailMessage(subject, html_content, from_email, [to])
			msg.content_subtype = "html"  # Main content is now text/html
			msg.send()


class QueryResult(models.Model):
	query = models.ForeignKey(Query)

	error_msg = models.CharField(max_length=500,blank=True)
	results = models.CharField(max_length=400,blank=True)

	PENDING = 'pending'
	WRITING = 'writing'
	SUCCESS = 'completed_success'
	FAILED = 'completed_failed'

	StatusChoices = (
		(PENDING, 'Pending'),
		(WRITING, 'Writing To Disk'),
		(SUCCESS, 'Success'),
		(FAILED, 'Failed')
	)

	status = models.CharField(max_length=200,choices=StatusChoices, default=PENDING)

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)

	def to_dict(self, related=True):
		di = model_to_dict(self)
		di['created_on'] = self.created_on
		di['modified_on'] = self.modified_on
		return di


	def get_sample(self):
		if self.results == '':
			return []

		rf = csv.reader(open(self.results, 'r'))
		sample = []
		i = 0

		for line in rf:
			if i > 50:
				break
			i += 1
			sample.append(line)

		return sample



class Comment(models.Model):
	user = models.ForeignKey(User)
	query = models.ForeignKey(Query)

	message = models.TextField()

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)



