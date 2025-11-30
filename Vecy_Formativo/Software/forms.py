# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import UsuarioPerfil, TipoDocumento

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre completo'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    
    fechanac_user = forms.DateField(
    required=False,
    widget=forms.DateInput(attrs={
        'class': 'form-control',
        'type': 'date'
    })
    )
    
    img_user = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control d-none',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"🔍 DEBUG FORM - Inicializando formulario para: {self.instance}")
        
        if self.instance and hasattr(self.instance, 'usuarioperfil'):
            perfil = self.instance.usuarioperfil
            print(f"🔍 DEBUG FORM - Perfil encontrado: {perfil}")
            print(f"🔍 DEBUG FORM - Fechanac en BD: {perfil.fechanac_user}")
            print(f"🔍 DEBUG FORM - Tipo de fecha: {type(perfil.fechanac_user)}")
            
            # SOLUCIÓN: Asignar directamente el objeto date
            if perfil.fechanac_user:
                self.fields['fechanac_user'].initial = perfil.fechanac_user
                print(f"✅ Initial establecido: {self.fields['fechanac_user'].initial}")
            else:
                print("⚠️ No hay fecha de nacimiento en el perfil")
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este email ya está registrado por otro usuario.")
        return email
    
    def save(self, commit=True):
        print("💾 FORM SAVE - Iniciando guardado...")
        
        user = super().save(commit=False)
        
        if commit:
            user.save()
            print("✅ Usuario guardado")
            
            try:
                perfil = UsuarioPerfil.objects.get(fkuser=user)
                print(f"📊 Perfil encontrado para actualizar: {perfil}")
                
                # Actualizar fecha de nacimiento
                fechanac = self.cleaned_data.get('fechanac_user')
                print(f"📅 Fecha de nacimiento en cleaned_data: {fechanac}")
                
                perfil.fechanac_user = fechanac
                print(f"📅 Fecha establecida en perfil: {perfil.fechanac_user}")
                
                # Guardar imagen si existe
                if 'img_user' in self.cleaned_data and self.cleaned_data['img_user']:
                    perfil.img_user = self.cleaned_data['img_user']
                    print(f"🖼️ Imagen guardada: {perfil.img_user}")
                
                perfil.save()
                print("✅ Perfil actualizado")
                
            except UsuarioPerfil.DoesNotExist as e:
                print(f"❌ Error: {e}")
                tipo_doc_default = TipoDocumento.objects.first()
                perfil = UsuarioPerfil(
                    fkuser=user,
                    fktipodoc_user=tipo_doc_default,
                    doc_user=user.username,
                    estado_user='activo',
                    fechanac_user=self.cleaned_data.get('fechanac_user')
                )
                perfil.save()
                print("✅ Nuevo perfil creado")
        
        return user