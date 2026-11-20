from functools import wraps
from urllib.parse import urlencode

from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import EXPRESS_EXTRA, FEES, Category, Order, OrderItem, Product, Profile, Variant

FILTERS = {"soins": ["skin_type", "effect"], "capillaire": ["hair_origin", "texture"]}
TITLES = dict(Category.SPACES)


def home(request):
    qs = Product.objects.filter(active=True).select_related("category").prefetch_related("variants")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(category__name__icontains=q))
        return render(request, "shop/catalogue.html", {"q": q, "title": f"Résultats pour « {q} »", "products": qs})
    return render(request, "shop/catalogue.html", {"hero": True, "products": qs.filter(featured=True)[:8]})


def catalogue(request, space):
    if space not in FILTERS:
        raise Http404
    qs = Product.objects.filter(active=True, category__space=space).select_related("category").prefetch_related("variants")
    cats = Category.objects.filter(space=space)
    filters = [{"name": "categorie", "label": "Catégorie", "choices": [(c.slug, c.name) for c in cats],
                "value": request.GET.get("categorie", "")}]
    for name in FILTERS[space]:
        f = Product._meta.get_field(name)
        filters.append({"name": name, "label": f.verbose_name, "choices": f.choices, "value": request.GET.get(name, "")})
    for f in filters:
        if f["value"]:
            qs = qs.filter(**{"category__slug" if f["name"] == "categorie" else f["name"]: f["value"]})
    return render(request, "shop/catalogue.html", {
        "space": space, "title": TITLES[space], "filters": filters, "products": qs,
        "filtered": any(f["value"] for f in filters)})


def product(request, slug):
    p = get_object_or_404(Product.objects.select_related("category").prefetch_related("variants"), slug=slug, active=True)
    variants = list(p.variants.all())
    default = next((v for v in variants if v.stock > 0), None)
    return render(request, "shop/product.html", {"p": p, "variants": variants, "default": default})


def _lines(request):
    raw = request.session.get("cart", {})
    lines, total = [], 0
    for v in Variant.objects.filter(id__in=list(raw)).select_related("product"):
        qty = min(raw[str(v.id)], v.stock)
        if qty > 0:
            lines.append({"v": v, "qty": qty, "sub": v.price * qty})
            total += v.price * qty
    return lines, total


def cart(request):
    lines, total = _lines(request)
    return render(request, "shop/cart.html", {"lines": lines, "total": total})


@require_POST
def cart_set(request):
    v = get_object_or_404(Variant, pk=request.POST.get("variant"))
    cart_data = request.session.get("cart", {})
    raw = request.POST.get("qty", "1")
    qty = int(raw) if raw.isdigit() else 1
    if request.POST.get("mode") == "add":
        qty += cart_data.get(str(v.id), 0)
    if qty > v.stock:
        qty = v.stock
        messages.warning(request, f"Seulement {v.stock} en stock pour « {v} ».")
    if qty <= 0:
        cart_data.pop(str(v.id), None)
        messages.info(request, f"« {v} » a été retiré du panier.")
    else:
        cart_data[str(v.id)] = qty
        messages.success(request, f"« {v} » : {qty} dans le panier.")
    request.session["cart"] = cart_data
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "cart")


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer_name", "phone", "email", "delivery_mode", "zone", "address", "express", "payment"]
        widgets = {"delivery_mode": forms.RadioSelect, "payment": forms.RadioSelect}

    def clean_phone(self):
        p = self.cleaned_data["phone"]
        if len([c for c in p if c.isdigit()]) < 8:
            raise forms.ValidationError("Entrez un numéro valide, par exemple 6 77 00 00 00.")
        return p

    def clean(self):
        d = super().clean()
        if d.get("delivery_mode") == "home" and not d.get("address"):
            self.add_error("address", "Indiquez votre adresse ou votre quartier pour la livraison.")
        return d


class OutOfStock(Exception):
    pass


def checkout(request):
    lines, total = _lines(request)
    if not lines:
        messages.info(request, "Votre panier est vide : ajoutez d'abord un produit.")
        return redirect("home")
    initial = {}
    if request.user.is_authenticated:
        pr = getattr(request.user, "profile", None)
        initial = {"customer_name": request.user.get_full_name(), "email": request.user.email, "phone": pr.phone if pr else ""}
    form = OrderForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        o = form.save(commit=False)
        if request.user.is_authenticated:
            o.user = request.user
        if o.delivery_mode == "pickup":
            o.zone, o.address, o.express, o.delivery_fee = "douala", "", False, 0
        else:
            o.delivery_fee = FEES[o.zone] + (EXPRESS_EXTRA if o.express else 0)
        try:
            with transaction.atomic():
                o.save()
                for l in lines:  # un seul stock : le site et la boutique partagent cette base
                    ok = Variant.objects.filter(pk=l["v"].pk, stock__gte=l["qty"]).update(stock=F("stock") - l["qty"])
                    if not ok:
                        raise OutOfStock(str(l["v"]))
                    OrderItem.objects.create(order=o, variant=l["v"], name=str(l["v"]), price=l["v"].price, qty=l["qty"])
        except OutOfStock as e:
            messages.error(request, f"Stock insuffisant pour « {e.args[0]} » : ajustez votre panier.")
            return redirect("cart")
        request.session["cart"] = {}
        request.session["last_order"] = o.pk
        return redirect("done", pk=o.pk)
    return render(request, "shop/checkout.html", {
        "form": form, "lines": lines, "total": total, "fees": FEES, "express_extra": EXPRESS_EXTRA})


def done(request, pk):
    if request.session.get("last_order") != pk:
        raise Http404
    o = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    return render(request, "shop/done.html", {"o": o})


class SignupForm(forms.Form):
    full_name = forms.CharField(label="Nom complet", max_length=120,
                                widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label="Adresse e-mail", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(label="Téléphone", max_length=30, help_text="Pour vous prévenir quand votre commande est prête.",
                            widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))
    password1 = forms.CharField(label="Mot de passe", help_text="8 caractères minimum.",
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmer le mot de passe",
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_email(self):
        e = self.cleaned_data["email"].lower()
        if User.objects.filter(username=e).exists():
            raise forms.ValidationError("Un compte existe déjà avec cet e-mail : connectez-vous.")
        return e

    def clean_phone(self):
        p = self.cleaned_data["phone"]
        if len([c for c in p if c.isdigit()]) < 8:
            raise forms.ValidationError("Entrez un numéro valide, par exemple 6 77 00 00 00.")
        return p

    def clean(self):
        d = super().clean()
        p1, p2 = d.get("password1"), d.get("password2")
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Les deux mots de passe ne sont pas identiques.")
        return d


class LoginForm(AuthenticationForm):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["username"].label = "Adresse e-mail ou identifiant"
        self.fields["username"].widget.attrs.update({"autocomplete": "email"})


login_view = LoginView.as_view(template_name="shop/login.html", authentication_form=LoginForm, redirect_authenticated_user=True)
logout_view = LogoutView.as_view()


def signup(request):
    if request.user.is_authenticated:
        return redirect("account")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        first, _, last = d["full_name"].strip().partition(" ")
        u = User.objects.create_user(username=d["email"], email=d["email"], password=d["password1"],
                                     first_name=first, last_name=last)
        Profile.objects.create(user=u, phone=d["phone"])
        login(request, u)
        messages.success(request, "Bienvenue ! Votre compte est créé.")
        return redirect("account")
    return render(request, "shop/signup.html", {"form": form})


@login_required
def account(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "shop/account.html", {"orders": orders, "profile": getattr(request.user, "profile", None)})


def staff_required(view):
    """Réservé au personnel : visiteur -> connexion ; client connecté -> accueil (évite la boucle de redirection)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "login")
        if not request.user.is_staff:
            messages.error(request, "Cette page est réservée au personnel de la boutique.")
            return redirect("home")
        return view(request, *args, **kwargs)
    return wrapper


def _commit(o, lines):
    """Enregistre une commande et décrémente le stock unique (site et boutique)."""
    with transaction.atomic():
        o.save()
        for v, qty in lines:
            if not Variant.objects.filter(pk=v.pk, stock__gte=qty).update(stock=F("stock") - qty):
                raise OutOfStock(str(v))
            OrderItem.objects.create(order=o, variant=v, name=str(v), price=v.price, qty=qty)


def _pos_lines(sale):
    lines, total = [], 0
    for v in Variant.objects.filter(id__in=list(sale)).select_related("product"):
        qty = min(sale[str(v.id)], v.stock)
        if qty > 0:
            lines.append({"v": v, "qty": qty, "sub": v.price * qty})
            total += v.price * qty
    return lines, total


@staff_required
def pos(request):
    sale = request.session.get("pos", {})
    if request.method == "POST":
        act = request.POST.get("action")
        if act == "add":
            v = get_object_or_404(Variant, pk=request.POST.get("variant"))
            raw = request.POST.get("qty", "1")
            n = int(raw) if raw.isdigit() and int(raw) > 0 else 1
            sale[str(v.id)] = min(sale.get(str(v.id), 0) + n, v.stock)
        elif act == "remove":
            sale.pop(request.POST.get("variant", ""), None)
        elif act == "pay":
            lines, _ = _pos_lines(sale)
            if not lines:
                messages.info(request, "La vente est vide : ajoutez d'abord un produit.")
            else:
                o = Order(customer_name=request.POST.get("name", "").strip() or "Client boutique", phone="-",
                          delivery_mode="pickup", payment="cod", status="paid", channel="shop")
                try:
                    _commit(o, [(l["v"], l["qty"]) for l in lines])
                    sale = {}
                    messages.success(request, f"Vente n° {o.pk} encaissée : {o.total} FCFA. Le stock du site est à jour.")
                except OutOfStock as e:
                    messages.error(request, f"Stock insuffisant pour « {e.args[0]} ».")
        request.session["pos"] = sale
        return redirect(f"{request.path}?{urlencode({'q': request.POST.get('q', '')})}")
    q = request.GET.get("q", "").strip()
    results = []
    if q:
        results = Variant.objects.filter(Q(product__name__icontains=q) | Q(label__icontains=q) | Q(product__brand__icontains=q)).select_related("product")[:15]
    lines, total = _pos_lines(sale)
    return render(request, "shop/pos.html", {"q": q, "results": results, "lines": lines, "total": total})


@staff_required
def dashboard(request):
    if request.method == "POST":
        o = get_object_or_404(Order, pk=request.POST.get("order"))
        st = request.POST.get("status")
        if st in dict(Order.STATUS):
            o.status, o.driver = st, request.POST.get("driver", "").strip()[:80]
            o.save(update_fields=["status", "driver"])
            messages.success(request, f"Commande n° {o.pk} mise à jour : {o.get_status_display()}.")
        return redirect("dashboard")
    counts = dict(Order.objects.values_list("status").annotate(n=Count("id")))
    return render(request, "shop/dashboard.html", {
        "stats": [(label, counts.get(key, 0)) for key, label in Order.STATUS],
        "low": Variant.objects.filter(stock__lte=F("alert_threshold")).select_related("product").order_by("stock"),
        "orders": Order.objects.exclude(status="paid").prefetch_related("items")[:40],
        "statuses": Order.STATUS})


@staff_required
def bordereau(request, pk):
    o = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    return render(request, "shop/bordereau.html", {"o": o})
