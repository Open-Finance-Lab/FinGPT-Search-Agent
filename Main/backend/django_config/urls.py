"""
URL configuration for chat_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('input_webtext/', views.add_webtext, name='input_webtext'),
    path('get_chat_response/', views.chat_response, name='get_chat_response'),
    path('get_adv_response/', views.adv_response, name='get_adv_response'),
    path('get_source_urls/', views.get_sources, name = 'get_source_urls'),
    path('clear_messages/', views.clear, name = 'clear_messages'),
    path('api/get_preferred_urls/', views.get_preferred_urls, name='get_preferred_urls'),
    path('api/add_preferred_url/', views.add_preferred_url, name='add_preferred_url'),
    path('api/folder_path', views.folder_path, name='folder_path'),
    path('get_mcp_response/', views.mcp_chat_response, name='get_mcp_response'),
    path('log_question/', views.log_question, name='log_question'),

]
