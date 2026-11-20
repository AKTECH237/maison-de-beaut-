import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from shop.models import Category

QUERIES = {
    "laits-de-toilette": "body lotion bottle", "savons-gel-douche": "natural soap",
    "lotions-toniques": "face toner skincare", "serums-traitants": "face serum dropper",
    "glycerines-huiles": "natural oil bottle", "parfumerie": "perfume bottle",
    "meches-synthetiques": "braiding hair", "greffes-humaines": "hair bundles weave",
    "perruques": "wig", "produits-dentretien-capillaires": "hair oil",
}


class Command(BaseCommand):
    help = "Associe à chaque produit une image trouvée en ligne via l'API Pexels (internet requis)"

    def handle(self, *args, **opts):
        key = settings.PEXELS_API_KEY
        if not key:
            raise CommandError("Définissez PEXELS_API_KEY (clé gratuite : pexels.com/api), puis relancez.")
        for c in Category.objects.all():
            q = QUERIES.get(c.slug, "skincare cosmetics" if c.space == "soins" else "hair extensions")
            url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode({"query": q, "per_page": 15, "orientation": "landscape"})
            req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "maison-eclat"})
            try:
                data = json.load(urllib.request.urlopen(req, timeout=20))
            except Exception as e:
                self.stderr.write(f"{c.name} : échec ({e})")
                continue
            photos = [p["src"]["large"] for p in data.get("photos", [])]
            if not photos:
                continue
            for i, p in enumerate(c.product_set.all()):
                p.image_url = photos[i % len(photos)]
                p.save(update_fields=["image_url"])
            self.stdout.write(f"{c.name} : images associées")
