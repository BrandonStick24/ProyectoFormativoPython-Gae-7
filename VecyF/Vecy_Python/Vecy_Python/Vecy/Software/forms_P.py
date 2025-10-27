# forms_P.py - Formularios exclusivos para gestión de productos
from django import forms
from Software.models import Productos, CategoriaProductos, Negocios

class ProductoForm_P(forms.ModelForm):
    class Meta:
        model = Productos
        fields = [
            'nom_prod', 'precio_prod', 'desc_prod', 'fkcategoria_prod',
            'stock_prod', 'stock_minimo', 'img_prod'
        ]
        widgets = {
            'nom_prod': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'precio_prod': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio',
                'step': '0.01'
            }),
            'desc_prod': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del producto',
                'rows': 3
            }),
            'fkcategoria_prod': forms.Select(attrs={
                'class': 'form-control'
            }),
            'stock_prod': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Stock disponible'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Stock mínimo alerta',
                'value': 5
            }),
            'img_prod': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'nom_prod': 'Nombre del Producto',
            'precio_prod': 'Precio',
            'desc_prod': 'Descripción',
            'fkcategoria_prod': 'Categoría',
            'stock_prod': 'Stock Disponible',
            'stock_minimo': 'Stock Mínimo',
            'img_prod': 'Imagen del Producto'
        }

class FiltroProductosForm_P(forms.Form):
    TIPO_BUSQUEDA = [
        ('nombre', 'Nombre'),
        ('precio', 'Precio'),
        ('estado', 'Estado'),
        ('stock', 'Stock'),
    ]
    
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar producto...',
            'id': 'inputBusqueda'
        })
    )
    
    tipo_filtro = forms.ChoiceField(
        choices=TIPO_BUSQUEDA,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'selectFiltro'
        })
    )
    
    orden = forms.ChoiceField(
        choices=[('asc', 'Ascendente'), ('desc', 'Descendente')],
        required=False,
        initial='asc',
        widget=forms.HiddenInput(attrs={'id': 'inputOrden'})
    )