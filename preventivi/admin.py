from django.contrib import admin

from .models import CategoriaProdotto, Preventivo, Prodotto, SezionePreventivo, VoceProventivo


@admin.register(CategoriaProdotto)
class CategoriaProdottoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordine')


@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    list_display = ('descrizione', 'categoria', 'marca', 'prezzo_unitario')
    list_filter = ('categoria',)
    search_fields = ('descrizione', 'marca')


class VoceProventivoInline(admin.TabularInline):
    model = VoceProventivo
    extra = 0


@admin.register(SezionePreventivo)
class SezionePreventivoAdmin(admin.ModelAdmin):
    list_display = ('titolo', 'preventivo', 'ordine')
    inlines = [VoceProventivoInline]


class SezionePreventivoInline(admin.TabularInline):
    model = SezionePreventivo
    extra = 0
    show_change_link = True


@admin.register(Preventivo)
class PreventivoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'revisione', 'progetto', 'cliente_id', 'data', 'stato', 'totale_display')
    list_filter = ('stato',)
    search_fields = ('numero', 'progetto')
    inlines = [SezionePreventivoInline]

    @admin.display(description='Totale')
    def totale_display(self, obj):
        return obj.totale
