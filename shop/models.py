from django.conf import settings
from django.db import models

FEES = {"douala": 1500, "yaounde": 2500, "autre": 4000}  # frais de livraison (FCFA)
EXPRESS_EXTRA = 1500


class Category(models.Model):
    SPACES = [("soins", "Cosmétiques & Soins"), ("capillaire", "Mèches, Greffes & Capillaire")]
    name = models.CharField("nom", max_length=80)
    slug = models.SlugField(unique=True)
    space = models.CharField("espace", max_length=12, choices=SPACES)

    class Meta:
        verbose_name, verbose_name_plural, ordering = "catégorie", "catégories", ["space", "name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="catégorie")
    name = models.CharField("nom", max_length=120)
    slug = models.SlugField(unique=True)
    brand = models.CharField("marque", max_length=80, blank=True)
    description = models.TextField(blank=True)
    badge = models.CharField("badge d'authenticité", max_length=60, blank=True,
                             help_text="Ex. : 100 % cheveux humains")
    skin_type = models.CharField("Type de peau", max_length=20, blank=True, choices=[
        ("seche", "Sèche"), ("mixte", "Mixte"), ("grasse", "Grasse"), ("hyperpigmentee", "Hyperpigmentée")])
    effect = models.CharField("Effet recherché", max_length=20, blank=True, choices=[
        ("hydratant", "Hydratant"), ("eclaircissant", "Éclaircissant / unifiant"),
        ("anti-imperfections", "Anti-imperfections")])
    hair_origin = models.CharField("Type de cheveux", max_length=20, blank=True, choices=[
        ("peruvien", "Péruvien"), ("bresilien", "Brésilien"), ("indien", "Indien"), ("synthetique", "Synthétique")])
    texture = models.CharField("Texture", max_length=20, blank=True, choices=[
        ("lisse", "Lisse (Straight)"), ("body-wave", "Ondulé (Body Wave)"), ("curly", "Bouclé (Curly)")])
    color = models.CharField("Couleur", max_length=30, blank=True, help_text="Ex. : 1B, 613, Ombré")
    image_url = models.URLField("image (URL)", blank=True, help_text="Laissez vide : une image est alors choisie en ligne")
    featured = models.BooleanField("mis en avant", default=False)
    active = models.BooleanField("visible sur le site", default=True)

    class Meta:
        verbose_name, ordering = "produit", ["name"]

    def __str__(self):
        return self.name

    @property
    def from_price(self):
        return min((v.price for v in self.variants.all()), default=0)

    @property
    def image_src(self):
        if self.image_url:
            return self.image_url
        kw = "skincare,cosmetics" if self.category.space == "soins" else "hair,wig"
        return f"https://loremflickr.com/640/480/{kw}?lock={self.pk}"

    @property
    def in_stock(self):
        return any(v.stock > 0 for v in self.variants.all())


class Variant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    label = models.CharField("déclinaison", max_length=60, help_text='Ex. : 250 ml ou 18"')
    price = models.PositiveIntegerField("prix (FCFA)")
    stock = models.PositiveIntegerField("stock", default=0)
    alert_threshold = models.PositiveIntegerField("seuil d'alerte", default=2)

    class Meta:
        verbose_name, ordering = "déclinaison", ["price"]

    def __str__(self):
        return f"{self.product.name} - {self.label}"

    @property
    def low(self):
        return self.stock <= self.alert_threshold


class Order(models.Model):
    STATUS = [("new", "Nouvelle commande"), ("prep", "En préparation"), ("ready", "Prête à retirer"),
              ("confirmed", "Confirmée pour livraison"), ("taken", "Prise en charge par le livreur"),
              ("delivered", "Livrée"), ("paid", "Payée")]
    DELIVERY = [("home", "Livraison à domicile ou au bureau"), ("pickup", "Retrait en boutique (Click & Collect)")]
    PAYMENT = [("cod", "À la livraison ou au retrait (espèces, paiement mobile)"),
               ("momo", "Mobile Money (Orange Money, MTN MoMo, Wave)"),
               ("card", "Carte bancaire (Visa, Mastercard)")]
    ZONES = [("douala", "Douala"), ("yaounde", "Yaoundé"), ("autre", "Autre ville")]

    customer_name = models.CharField("nom complet", max_length=120)
    phone = models.CharField("téléphone", max_length=30)
    email = models.EmailField("e-mail (facultatif)", blank=True)
    delivery_mode = models.CharField("mode de réception", max_length=10, choices=DELIVERY, default="home")
    zone = models.CharField("ville", max_length=10, choices=ZONES, default="douala")
    address = models.CharField("adresse ou quartier", max_length=200, blank=True)
    express = models.BooleanField("livraison express", default=False)
    payment = models.CharField("paiement", max_length=10, choices=PAYMENT, default="cod")
    status = models.CharField("statut", max_length=10, choices=STATUS, default="new")
    driver = models.CharField("livreur", max_length=80, blank=True,
                              help_text="Livreur interne ou service tiers (ex. Yango)")
    delivery_fee = models.PositiveIntegerField("frais de livraison", default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="orders", verbose_name="compte client")
    channel = models.CharField("canal", max_length=5, choices=[("web", "Site web"), ("shop", "Boutique")], default="web")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name, ordering = "commande", ["-created_at"]

    def __str__(self):
        return f"Commande n° {self.pk}"

    @property
    def total(self):
        return self.delivery_fee + sum(i.subtotal for i in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField()
    qty = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.price * self.qty


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField("téléphone", max_length=30)

    def __str__(self):
        return f"Profil de {self.user}"
