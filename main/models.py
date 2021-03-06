from django.db import models
from django.contrib.auth.models import User
from django.core.mail import  EmailMessage
from django.forms.models import model_to_dict

import main.tasks as tasks
import json
import sys
import time
import csv
import os


class Query(models.Model):
	user = models.ForeignKey(User)

	name = models.CharField(max_length=200,blank=True,default='')
	query = models.TextField()

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
	is_saved = models.BooleanField(default=False)
	is_public = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)

	email_on_complete = models.BooleanField(default=False)

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)

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

	def to_json(self):
		di = model_to_dict(self)
		return json.dumps(di)

	@staticmethod
	def from_json(js):
		d = json.loads(js)
		q = Query.objects.get(pk=d['id'])
		del d['id']
		del d['user']

		for k in d:
			setattr(q, k, d[k])
		return

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


		try:
			transport = TSocket.TSocket(os.getenv('HIVE_SERVER'), 10000)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)

			client = ThriftHive.Client(protocol)
			transport.open()

			client.execute(self.query)

			self.refresh_from_db()

			self.status = self.WRITING
			self.save()

			self.results = '/tmp/hive_results/' + str(self.pk) + str(int(time.time())) + '.csv'

			rfile = open(self.results, 'w')
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

			self.status = self.SUCCESS
		except HiveServerException, e:
			self.error_msg = e

			if e.errorCode == 0:
				self.status = self.SUCCESS
			else:
				self.status = self.FAILED

			print '%s' % (e.message)
		except Thrift.TException, tx:
			self.error_msg = tx
			self.status = self.FAILED
			print '%s' % (tx.message)
		except TypeError, e:
			if self.query.count("INSERT") > 0 or self.query.count("CREATE") > 0 :
				self.status = self.SUCCESS
			else:
				self.error_msg = e
				self.status = self.FAILED
		except:
			self.error_msg = sys.exc_info()[0]
			self.status = self.FAILED

		self.save()
		if self.email_on_complete:
			subject = "Query finished: " + str(self.pk)
			html_content = "The query has finished. Go here for details: <a href='http://hive.louddev.com/query/" + str(self.pk) + "/'>Query</a>"
			from_email = "HiveManager <no-reply@louddev.com>"
			to = self.user.email

			msg = EmailMessage(subject, html_content, from_email, [to])
			msg.content_subtype = "html"  # Main content is now text/html
			msg.send()

class Comment(models.Model):
	user = models.ForeignKey(User)
	query = models.ForeignKey(Query)

	message = models.TextField()

	modified_on = models.DateTimeField(auto_now=True)
	created_on = models.DateTimeField(auto_now_add=True)



