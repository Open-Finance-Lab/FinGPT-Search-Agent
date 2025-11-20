"""
URL configuration for chat_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from api import views

urlpatterns = [
    # Admin disabled (requires database)
    # path('admin/', admin.site.urls),
    path('health/', views.health, name='health'),
    path('input_webtext/', views.add_webtext, name='input_webtext'),
    path('get_chat_response/', views.chat_response, name='get_chat_response'),
    path('get_chat_response_stream/', views.chat_response_stream, name='get_chat_response_stream'),
    path('get_adv_response/', views.adv_response, name='get_adv_response'),
    path('get_adv_response_stream/', views.adv_response_stream, name='get_adv_response_stream'),
    path('get_source_urls/', views.get_sources, name = 'get_source_urls'),
    path('clear_messages/', views.clear, name = 'clear_messages'),
    path('api/get_preferred_urls/', views.get_preferred_urls, name='get_preferred_urls'),
    path('api/add_preferred_url/', views.add_preferred_url, name='add_preferred_url'),
    path('api/sync_preferred_urls/', views.sync_preferred_urls, name='sync_preferred_urls'),
    path('get_agent_response/', views.agent_chat_response, name='get_agent_response'),
    path('log_question/', views.log_question, name='log_question'),
    path('api/get_memory_stats/', views.get_memory_stats, name='get_memory_stats'),
    path('api/get_available_models/', views.get_available_models, name='get_available_models'),
]
