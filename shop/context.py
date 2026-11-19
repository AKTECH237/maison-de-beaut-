from django.conf import settings

def shop_info(request):
    cart = request.session.get("cart", {})
    return {"shop": settings.SHOP, "cart_count": sum(cart.values())}
