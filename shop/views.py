# shop/views.py
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Product
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomUserCreationForm
from django.http import HttpResponse

def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})
    
# shop/views.py (ajoute ces fonctions en bas)

def add_to_cart(request, product_id):
    """Ajoute un produit au panier (via POST)"""
    product = get_object_or_404(Product, id=product_id)
    
    # Récupère ou crée le panier dans la session
    cart = request.session.get('cart', {})
    
    # Convertit product_id en chaîne (les clés de session sont des strings)
    product_id_str = str(product_id)
    
    # Si le produit est déjà dans le panier, incrémente la quantité
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {'quantity': 1}
    
    # Sauvegarde le panier dans la session
    request.session['cart'] = cart
    request.session.modified = True  # Important : indique à Django que la session a changé
    
    messages.success(request, f"{product.name} a été ajouté au panier.")
    return redirect('home')


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0

    for product_id_str, item_data in cart.items():
        product = get_object_or_404(Product, id=int(product_id_str))
        quantity = item_data['quantity']
        item_total = product.price * quantity
        total += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'item_total': item_total,
        })

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,  # ← ajouté
    })

def update_cart(request, product_id):
    """Met à jour ou supprime un article du panier (via POST)"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        action = request.POST.get('action')
        if action == 'remove':
            del cart[product_id_str]
            messages.info(request, "Article supprimé du panier.")
        elif action == 'update':
            try:
                quantity = int(request.POST.get('quantity', 1))
                if quantity < 1:
                    del cart[product_id_str]
                    messages.info(request, "Article supprimé du panier.")
                else:
                    cart[product_id_str]['quantity'] = quantity
                    messages.success(request, "Panier mis à jour.")
            except ValueError:
                pass  # Ignore les valeurs invalides

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('view_cart')
    
# shop/views.py (ajoute en bas)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')  # Redirige vers la page de login après inscription
    template_name = 'registration/register.html'    


def create_admin(request):
    if User.objects.filter(username='admin').exists():
        return HttpResponse("Admin existe déjà.")
    User.objects.create_superuser('admin', 'admin@example.com', 'motdepasse123')
    return HttpResponse("Superutilisateur créé !")

# shop/views.py (ajoute en bas)

def create_checkout_session(request):
    if not getattr(settings, 'STRIPE_SECRET_KEY', None):
        return HttpResponse("Stripe non configuré.", status=500)
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')

    # Récupère les articles du panier
    line_items = []
    for product_id_str, item_data in cart.items():
        product = get_object_or_404(Product, id=int(product_id_str))
        line_items.append({
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': product.name,
                },
                'unit_amount': int(product.price * 100),  # en centimes
            },
            'quantity': item_data['quantity'],
        })

    # Crée la commande (non payée)
    order = Order.objects.create(
        first_name='Temp',
        last_name='Temp',
        email='temp@example.com',
        address='Temp',
        postal_code='00000',
        city='Temp',
    )
    for product_id_str, item_data in cart.items():
        product = get_object_or_404(Product, id=int(product_id_str))
        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.price,
            quantity=item_data['quantity'],
        )

    # Crée la session Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri('/') + 'payment/success/',
        cancel_url=request.build_absolute_uri('/') + 'payment/cancel/',
        metadata={'order_id': order.id},
    )

    return JsonResponse({'id': session.id})
    
def payment_success(request):
    return render(request, 'payment_success.html')

def payment_cancel(request):
    return render(request, 'payment_cancel.html')    