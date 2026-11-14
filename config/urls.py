"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path, include
from transactions.views import PurchaseDataView
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        "status": "online",
        "service": "Z9Pay VTU Backend API",
        "version": "v1",
        "endpoints": {
            "admin": "/admin/",
            "auth": "/api/v1/auth/register",
            "auth" : "/api/v1/auth/login/"
            "wallet": "/api/v1/wallet/",
            "catalog": "/api/v1/catalog/",
            "purchase": "/api/v1/purchase/data/",
            "transactions": "/api/v1/transactions/"
        }
    })

urlpatterns = [
    path("", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/wallet/", include("wallet.urls")),
    path("api/v1/catalog/", include("catalog.urls")),
    path("api/v1/purchase/data/", PurchaseDataView.as_view(), name="purchase-data"),
    path("api/v1/transactions/", include("transactions.urls")),
]
