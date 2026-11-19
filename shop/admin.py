from django.contrib import admin
from .models import Category, Order, OrderItem, Product, Variant

admin.site.register(Category, list_display=("name", "space"), prepopulated_fields={"slug": ("name",)})


class VariantInline(admin.TabularInline):
    model, extra = Variant, 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "stock_total", "stock_ok", "featured", "active")
    list_filter = ("category__space", "category", "active")
    search_fields = ("name", "brand")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VariantInline]

    @admin.display(description="Stock total")
    def stock_total(self, obj):
        return sum(v.stock for v in obj.variants.all())

    @admin.display(boolean=True, description="Stock suffisant")
    def stock_ok(self, obj):
        return not any(v.low for v in obj.variants.all())


class ItemInline(admin.TabularInline):
    model, extra, can_delete = OrderItem, 0, False
    readonly_fields = ("variant", "name", "price", "qty")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone", "delivery_mode", "payment", "status", "driver", "total_fcfa", "created_at")
    list_editable = ("status", "driver")
    list_filter = ("status", "delivery_mode", "payment")
    search_fields = ("customer_name", "phone")
    inlines = [ItemInline]

    @admin.display(description="Total (FCFA)")
    def total_fcfa(self, obj):
        return obj.total
