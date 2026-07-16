from django.contrib import admin

from .models import Cliente, Preventivo, SezionePreventivo, VoceProventivo


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
    list_display = ('numero', 'revisione', 'cliente', 'data', 'stato', 'totale_display')
    list_filter = ('stato',)
    search_fields = ('numero', 'cliente__ragione_sociale')
    inlines = [SezionePreventivoInline]

    @admin.display(description='Totale')
    def totale_display(self, obj):
        return obj.totale


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('ragione_sociale', 'citta', 'piva')
    search_fields = ('ragione_sociale', 'citta')
