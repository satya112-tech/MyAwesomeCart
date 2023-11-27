from django.shortcuts import render
from django.http import HttpResponse
from . models import Product,Contact,Orders,OrderUpdate
from math import ceil
import json
from django.views.decorators.csrf import csrf_exempt
from PayTm import Checksum

MERCHANT_KEY = 'Your-Merchant-Key-Here' + ' ' * (32 - len('Your-Merchant-Key-Here'))



def index(request):
    products= Product.objects.all()
    allprods=[]
    catprods=Product.objects.values('category','id')
    cats={item['category'] for item in catprods}
    for cat in cats:
        prod = Product.objects.filter(category=cat)
        n = len(prod)
        nslides = n // 4 + ceil((n / 4) - (n // 4))
        allprods.append([prod, range(1, nslides), nslides])
    params={'allprods':allprods}
    return render(request,'shop/index.html',params)


def about(request):
    return render(request,'shop/about.html')


def tracker(request):
    if request.method=="POST":
        orderId=request.POST.get('orderId','')
        email=request.POST.get('email','')
        try:
            order=Orders.objects.filter(order_id=orderId,email=email)
            if len(order)>0:
                update=OrderUpdate.objects.filter(order_id=orderId)
                updates=[]
                for item in update:
                    updates.append({'text':item.update_desc,'time':item.timestamp})
                    # json.dumps() convert dictionary into json
                    response = json.dumps({"status":"success", "updates": updates, "itemsJson": order[0].items_json}, default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{"status":"noitem"}')
        except Exception as e:
            return HttpResponse('{"status":"error"}')
    return render(request,'shop/tracker.html')


def contact(request):
    thank=False
    if request.method=="POST":
        name=request.POST.get('name','')
        email=request.POST.get('email', '')
        phone=request.POST.get('phone', '')
        desc=request.POST.get('desc', '')
        contact=Contact(name=name,email=email,phone=phone,desc=desc)
        contact.save()
        thank=True
    return render(request,'shop/contact.html',{'thank':thank})

def searchMatch(query, item):
    if query in item.desc.lower() or query in item.product_name.lower() or query in item.category.lower():
        return True
    else:
        return False
    
    
def search(request):
    query= request.GET.get('search')
    allprods=[]
    catprods=Product.objects.values('category','id')
    cats={item['category'] for item in catprods}
    for cat in cats:
        prodtemp = Product.objects.filter(category=cat)
        prod=[item for item in prodtemp if searchMatch(query, item)]
        n = len(prod)
        nslides = n // 4 + ceil((n / 4) - (n // 4))
        if len(prod)!= 0:
            allprods.append([prod, range(1, nslides), nslides])
    params = {'allprods': allprods, "msg":""}
    if len(allprods)==0 or len(query)<4:
        params={'msg':"Please make sure to enter relevant search query"}
    return render(request,'shop/search.html',params)


def productview(request,myid):
    product=Product.objects.filter(id=myid)
    return render(request,'shop/productview.html',{'product':product[0]})

def checkout(request):
    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amount', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address1', '') + " " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        order = Orders(items_json=items_json, name=name, amount=amount, email=email, address=address, city=city,state=state, zip_code=zip_code, phone=phone)
        order.save()
        #58,59 line for OrderUpdate
        update = OrderUpdate(order_id=order.order_id, update_desc="The order has been placed")
        update.save()
        thank=True
        id=order.order_id
        #return render(request,'shop/checkout.html',{'thank':thank,'id':id})
        #Request paytm to transfer the abount to account after payment by user
        param_dict={
            #merchant id
            'MID': 'Your-Merchant-Id-Here',
            'ORDER_ID': str(order.order_id),
            'TXN_AMOUNT': str(amount),
            'CUST_ID': email,
            'INDUSTRY_TYPE_ID': 'Retail',
            'WEBSITE': 'WEBSTAGING',
            'CHANNEL_ID': 'WEB',
            #Callback URL: It is the URL where you want Paytm to show you the payment status.
            'CALLBACK_URL':'http://127.0.0.1:8000/shop/handlerequest/',

        }
        param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
        return  render(request, 'shop/paytm.html', {'param_dict': param_dict})
    return render(request, 'shop/checkout.html')

@csrf_exempt
def handlerequest(request):
    # Ensure checksum is defined with a default value
    checksum = None

    # paytm will send you post request here
    form = request.POST
    response_dict = {}

    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]

    # Check if 'CHECKSUMHASH' is found in the form
    if checksum is not None:
        # Verify checksum after the loop
        verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)

        if verify:
            if response_dict['RESPCODE'] == '01':
                print('Order successful')
            else:
                print('Order was not successful because ' + response_dict['RESPMSG'])
    else:
        print('CHECKSUMHASH not found in the form')

    return render(request, 'shop/paymentstatus.html', {'response': response_dict})