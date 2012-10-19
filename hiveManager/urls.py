from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from main.models import Query, Comment
admin.autodiscover()
admin.site.register(Query)
admin.site.register(Comment)

urlpatterns = patterns('main.views',
	url(r'^$', 'index', name='index'),

	url(r'^public/?', 'public', name='public_default'),
	url(r'^public/(?P<offset>\d{1,6})/?$', 'public', name='public_offset'),

	url(r'^saved/?', 'saved', name='saved_default'),
	url(r'^saved/(?P<offset>\d{1,6})/?$', 'saved', name='saved_offset'),

	url(r'^ajax/query/(?P<qid>\d{1,4})/?$', 'ajax_query', name='create_query'),
	url(r'^ajax/query/?$', 'ajax_query', name='create_query'),
	url(r'^ajax/queries/?$', 'ajax_queries', name='get_queries'),

    url(r'^ajax/comment$', 'ajax_comment', name='save_comment'),

	url(r'^ajax/comments/(?P<qid>\d{1,4})/?$', 'ajax_comments', name='get_comments'),

	url(r'^query/(?P<id>\d{1,4})/?$', 'query', name='view_query'),
	url(r'^query/(?P<id>\d{1,4})/download/?$', 'download_results', name='download_results'),

	url(r'^logout/?', 'logout_view', name="logout"),
)

urlpatterns += patterns('', url(r'^admin/', include(admin.site.urls)))
