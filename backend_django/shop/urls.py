from django.urls import path
from .views import index, items, delete_item

urlpatterns = [
    # 🌐 frontend page
    path("", index),

    # 📦 API
    path("items/", items),
    path("items/<int:item_id>/", delete_item),
]
