from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("boutique/<slug:space>/", views.catalogue, name="catalogue"),
    path("produit/<slug:slug>/", views.product, name="product"),
    path("panier/", views.cart, name="cart"),
    path("panier/modifier/", views.cart_set, name="cart_set"),
    path("commande/", views.checkout, name="checkout"),
    path("commande/<int:pk>/merci/", views.done, name="done"),
]
