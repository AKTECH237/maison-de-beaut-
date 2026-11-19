from django.core.management.base import BaseCommand
from django.utils.text import slugify
from shop.models import Category, Product, Variant

S, H = "soins", "capillaire"
# (espace, catégorie, produit, marque, attributs, badge, vedette, [(déclinaison, prix, stock)])
DATA = [
    (S, "Laits de toilette", "Lait de toilette Karité & Miel", "Karité d'Or", dict(skin_type="seche", effect="hydratant"), "", True, [("250 ml", 3500, 20), ("500 ml", 6000, 12)]),
    (S, "Savons & Gel douche", "Savon éclat au Curcuma", "Karité d'Or", dict(skin_type="hyperpigmentee", effect="eclaircissant"), "", False, [("1 savon", 1500, 40)]),
    (S, "Lotions & Toniques", "Tonique unifiant Vitamine C", "Dermia", dict(skin_type="mixte", effect="eclaircissant"), "Produit cosmétique approuvé", True, [("200 ml", 5500, 15)]),
    (S, "Sérums traitants", "Sérum anti-taches Niacinamide", "Dermia", dict(skin_type="hyperpigmentee", effect="anti-imperfections"), "Produit cosmétique approuvé", True, [("30 ml", 12000, 2), ("50 ml", 18000, 8)]),
    (S, "Glycérines & Huiles", "Glycérine végétale pure", "Naturelle", dict(skin_type="seche", effect="hydratant"), "", False, [("100 ml", 2000, 25), ("250 ml", 4500, 10)]),
    (S, "Parfumerie", "Brume parfumée Fleur d'oranger", "Maison Éclat", dict(), "", False, [("100 ml", 7500, 14)]),
    (H, "Mèches synthétiques", "Mèches Soft Braid 1B", "Braid Pro", dict(hair_origin="synthetique", texture="lisse", color="1B"), "", False, [("1 paquet", 2500, 60)]),
    (H, "Greffes humaines", "Bundle Body Wave Péruvien", "Luxe Hair", dict(hair_origin="peruvien", texture="body-wave", color="1B"), "100 % cheveux humains", True, [('14"', 25000, 6), ('18"', 34000, 5), ('24"', 48000, 3)]),
    (H, "Greffes humaines", "Bundle Straight Brésilien", "Luxe Hair", dict(hair_origin="bresilien", texture="lisse", color="1B"), "100 % cheveux humains", True, [('16"', 28000, 4), ('22"', 42000, 1)]),
    (H, "Greffes humaines", "Frontal Lace 13x4 Curly Indien", "Luxe Hair", dict(hair_origin="indien", texture="curly", color="Ombré"), "100 % cheveux humains", False, [('12"', 35000, 3), ('16"', 45000, 2)]),
    (H, "Perruques", "Perruque Bob Lisse 613", "Luxe Hair", dict(hair_origin="bresilien", texture="lisse", color="613"), "100 % cheveux humains", True, [('12"', 55000, 2)]),
    (H, "Produits d'entretien capillaires", "Huile capillaire Ricin & Argan", "Naturelle", dict(), "", False, [("100 ml", 3000, 30), ("250 ml", 6500, 18)]),
]


class Command(BaseCommand):
    help = "Remplit la base avec un catalogue de démonstration"

    def handle(self, *args, **opts):
        if Product.objects.exists():
            return self.stdout.write("Catalogue déjà présent : rien à faire.")
        for space, cat, name, brand, attrs, badge, feat, variants in DATA:
            c, _ = Category.objects.get_or_create(slug=slugify(cat), defaults={"name": cat, "space": space})
            p = Product.objects.create(category=c, name=name, slug=slugify(name), brand=brand, badge=badge, featured=feat,
                                       description=f"{name} : produit sélectionné par Maison Éclat.", **attrs)
            for label, price, stock in variants:
                Variant.objects.create(product=p, label=label, price=price, stock=stock)
        self.stdout.write(self.style.SUCCESS("Catalogue de démonstration créé."))
