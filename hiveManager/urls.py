from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from main.models import Query, Comment
admin.autodiscover()
admin.site.register(Query)
admin.site.register(Comment)

urlpatterns = patterns('',
	url(r'^$', 'main.views.index', name='index'),

	url(r'^public/?', 'main.views.public', name='public_default'),
	url(r'^public/(?P<offset>\d{1,6})/?$', 'main.views.public', name='public_offset'),

	url(r'^saved/?', 'main.views.saved', name='saved_default'),
	url(r'^saved/(?P<offset>\d{1,6})/?$', 'main.views.saved', name='saved_offset'),

	url(r'^ajax/query/(?P<qid>\d{1,4})/?$', 'main.views.ajax_query', name='create_query'),
	url(r'^ajax/query/?$', 'main.views.ajax_query', name='create_query'),
	url(r'^ajax/queries/?$', 'main.views.ajax_queries', name='get_queries'),
	url(r'^ajax/comments/(?P<qid>\d{1,4})/?$', 'main.views.ajax_comments', name='get_comments'),

	url(r'^query/(?P<id>\d{1,4})/?$', 'main.views.query', name='view_query'),
	url(r'^query/(?P<id>\d{1,4})/download/?$', 'main.views.download_results', name='download_results'),

	url(r'^logout/?', 'main.views.logout_view', name="logout"),

	# Uncomment the admin/doc line below to enable admin documentation:
	#url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

	# Uncomment the next line to enable the admin:
	url(r'^admin/', include(admin.site.urls))
)
