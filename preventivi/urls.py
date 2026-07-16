from django.urls import path

from . import views

urlpatterns = [
    path('', views.PreventivoListView.as_view(), name='quote-list'),
    path('preventivi/nuovo/', views.PreventivoCreateView.as_view(), name='preventivo-create'),
    path('preventivi/<int:pk>/', views.PreventivoDetailView.as_view(), name='preventivo-detail'),
    path('preventivi/<int:pk>/modifica/', views.PreventivoUpdateView.as_view(), name='preventivo-update'),
    path('preventivi/<int:pk>/elimina/', views.PreventivoDeleteView.as_view(), name='preventivo-delete'),
    path('preventivi/<int:pk>/pdf/', views.preventivo_pdf, name='preventivo-pdf'),

    path('preventivi/<int:preventivo_pk>/sezioni/nuova/', views.SezionePreventivoCreateView.as_view(), name='sezione-create'),
    path('sezioni/<int:pk>/modifica/', views.SezionePreventivoUpdateView.as_view(), name='sezione-update'),
    path('sezioni/<int:pk>/elimina/', views.SezionePreventivoDeleteView.as_view(), name='sezione-delete'),

    path('sezioni/<int:sezione_pk>/voci/nuova/', views.VoceProventivoCreateView.as_view(), name='voce-create'),
    path('voci/<int:pk>/modifica/', views.VoceProventivoUpdateView.as_view(), name='voce-update'),
    path('voci/<int:pk>/elimina/', views.VoceProventivoDeleteView.as_view(), name='voce-delete'),

    path('clienti/', views.ClienteListView.as_view(), name='cliente-list'),
    path('clienti/nuovo/', views.ClienteCreateView.as_view(), name='cliente-create'),
    path('clienti/<int:pk>/modifica/', views.ClienteUpdateView.as_view(), name='cliente-update'),
    path('clienti/<int:pk>/elimina/', views.ClienteDeleteView.as_view(), name='cliente-delete'),

    path('catalogo/', views.ProdottoListView.as_view(), name='prodotto-list'),
    path('catalogo/nuovo/', views.ProdottoCreateView.as_view(), name='prodotto-create'),
    path('catalogo/<int:pk>/modifica/', views.ProdottoUpdateView.as_view(), name='prodotto-update'),
    path('catalogo/<int:pk>/elimina/', views.ProdottoDeleteView.as_view(), name='prodotto-delete'),
]
