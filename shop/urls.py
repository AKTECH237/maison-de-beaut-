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
    path("inscription/", views.signup, name="signup"),
    path("connexion/", views.login_view, name="login"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("mon-compte/", views.account, name="account"),
]
