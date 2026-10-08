from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Item


# 🌐 FRONTEND PAGE
def index(request):
    return render(request, "index.html")


# 📦 API: GET + POST
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def items(request):
    if request.method == "GET":
        items = Item.objects.all().values()
        return Response(list(items))

    if request.method == "POST":
        item = Item.objects.create(
            name=request.data["name"],
            quantity=request.data["quantity"],
            user_id=request.user.id
        )
        return Response({
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity
        })


# ❌ DELETE
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_item(request, item_id):
    Item.objects.filter(id=item_id).delete()
    return Response({"status": "deleted"})
